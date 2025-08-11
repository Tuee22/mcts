"""
Tests for GameManager component.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Fixtures imported from conftest.py  # Import all fixtures
from api.game_manager import GameManager
from api.models import (
    GameStatus, GameMode, PlayerType, GameSession,
    Player, Move, GameSettings, MCTSSettings
)


# MCTS mock fixture for game manager tests
@pytest.fixture(autouse=True)
def mock_mcts():
    """Mock MCTS for game manager tests."""
    mock_mcts = MagicMock()
    mock_mcts.get_sorted_actions.return_value = [
        (100, 0.8, "*(4,1)"),
        (50, 0.6, "*(3,0)")
    ]
    mock_mcts.choose_best_action.return_value = "*(4,1)"
    mock_mcts.get_evaluation.return_value = None
    mock_mcts.display.return_value = "Test Board Display"
    mock_mcts.ensure_sims.return_value = None
    mock_mcts.make_move.return_value = None
    mock_mcts.get_legal_moves.return_value = ["*(4,1)", "*(3,0)", "H(4,0)"]
    
    with patch('api.game_manager.Corridors_MCTS', return_value=mock_mcts):
        yield mock_mcts


@pytest.mark.asyncio
class TestGameManagerCreation:
    """Test game creation functionality."""
    
    async def test_create_pvp_game(self, game_manager: GameManager):
        """Test creating a PvP game."""
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN,
            player1_name="Alice",
            player2_name="Bob"
        )
        
        assert game.mode == GameMode.PVP
        assert game.status == GameStatus.IN_PROGRESS
        assert game.player1.name == "Alice"
        assert game.player2.name == "Bob"
        assert game.player1.type == PlayerType.HUMAN
        assert game.player2.type == PlayerType.HUMAN
        assert game.current_turn == 1
        assert game.mcts_instance is not None
    
    async def test_create_pvm_game(self, game_manager: GameManager):
        """Test creating a PvM game."""
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.MACHINE,
            player1_name="Human",
            player2_name="AI"
        )
        
        assert game.mode == GameMode.PVM
        assert game.player2.type == PlayerType.MACHINE
        # AI move is NOT queued yet since human goes first
        assert game_manager.ai_move_queue.empty()
    
    async def test_create_mvm_game(self, game_manager: GameManager):
        """Test creating a MvM game."""
        game = await game_manager.create_game(
            player1_type=PlayerType.MACHINE,
            player2_type=PlayerType.MACHINE,
            player1_name="AI-1",
            player2_name="AI-2"
        )
        
        assert game.mode == GameMode.MVM
        assert game.player1.type == PlayerType.MACHINE
        assert game.player2.type == PlayerType.MACHINE
        # First AI should be queued
        assert not game_manager.ai_move_queue.empty()
    
    async def test_create_game_with_custom_settings(self, game_manager: GameManager):
        """Test creating a game with custom MCTS settings."""
        settings = GameSettings(
            mcts_settings=MCTSSettings(
                c=0.5,
                min_simulations=1000,
                use_puct=True,
                seed=123
            )
        )
        
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN,
            settings=settings
        )
        
        assert game.settings.mcts_settings.c == 0.5
        assert game.settings.mcts_settings.min_simulations == 1000
        assert game.settings.mcts_settings.use_puct is True


@pytest.mark.asyncio
class TestGameManagerRetrieval:
    """Test game retrieval and listing."""
    
    async def test_get_game(self, game_manager: GameManager):
        """Test retrieving a game by ID."""
        # Create a game
        created_game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Retrieve it
        retrieved_game = await game_manager.get_game(created_game.game_id)
        assert retrieved_game is not None
        assert retrieved_game.game_id == created_game.game_id
    
    async def test_get_nonexistent_game(self, game_manager: GameManager):
        """Test retrieving a non-existent game."""
        game = await game_manager.get_game("nonexistent-id")
        assert game is None
    
    async def test_list_games(self, game_manager: GameManager):
        """Test listing all games."""
        # Create multiple games
        game_ids = []
        for i in range(3):
            game = await game_manager.create_game(
                player1_type=PlayerType.HUMAN,
                player2_type=PlayerType.HUMAN,
                player1_name=f"Player{i}"
            )
            game_ids.append(game.game_id)
        
        # List all games
        games = await game_manager.list_games()
        assert len(games) >= 3
        
        # Check games are sorted by creation time
        for i in range(len(games) - 1):
            assert games[i].created_at >= games[i + 1].created_at
    
    async def test_list_games_with_filters(self, game_manager: GameManager):
        """Test listing games with filters."""
        # Create games with different statuses
        game1 = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        game2 = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Cancel one game
        await game_manager.delete_game(game2.game_id)
        
        # Filter by status
        active_games = await game_manager.list_games(status=GameStatus.IN_PROGRESS)
        assert all(g.status == GameStatus.IN_PROGRESS for g in active_games)
        
        # Filter by player
        player_games = await game_manager.list_games(player_id=game1.player1.id)
        assert all(g.is_player(game1.player1.id) for g in player_games)
    
    async def test_delete_game(self, game_manager: GameManager):
        """Test deleting a game."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Delete it
        success = await game_manager.delete_game(game.game_id)
        assert success is True
        
        # Verify it's gone
        retrieved = await game_manager.get_game(game.game_id)
        assert retrieved is None
        
        # Try to delete again
        success = await game_manager.delete_game(game.game_id)
        assert success is False


@pytest.mark.asyncio
class TestGameManagerMoves:
    """Test move making functionality."""
    
    async def test_make_valid_move(self, game_manager: GameManager):
        """Test making a valid move."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Make a move
        response = await game_manager.make_move(
            game_id=game.game_id,
            player_id=game.player1.id,
            action="*(4,1)"
        )
        
        assert response.success is True
        assert response.move.action == "*(4,1)"
        assert response.next_turn == 2
        assert response.game_status == GameStatus.IN_PROGRESS
        
        # Check move was recorded
        updated_game = await game_manager.get_game(game.game_id)
        assert len(updated_game.move_history) == 1
        assert updated_game.current_turn == 2
    
    async def test_make_invalid_move(self, game_manager: GameManager):
        """Test making an invalid move."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Try invalid move
        with pytest.raises(ValueError, match="Illegal move"):
            await game_manager.make_move(
                game_id=game.game_id,
                player_id=game.player1.id,
                action="*(9,9)"  # Out of bounds
            )
    
    async def test_make_move_wrong_turn(self, game_manager: GameManager):
        """Test making a move when it's not the player's turn."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Player 2 tries to move first
        with pytest.raises(ValueError, match="Not your turn"):
            await game_manager.make_move(
                game_id=game.game_id,
                player_id=game.player2.id,
                action="*(4,1)"
            )
    
    async def test_make_move_invalid_player(self, game_manager: GameManager):
        """Test making a move with invalid player ID."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Invalid player ID
        with pytest.raises(ValueError, match="Player not in this game"):
            await game_manager.make_move(
                game_id=game.game_id,
                player_id="invalid-player",
                action="*(4,1)"
            )
    
    async def test_get_legal_moves(self, game_manager: GameManager):
        """Test getting legal moves."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Get legal moves
        legal_moves = await game_manager.get_legal_moves(game.game_id)
        assert isinstance(legal_moves, list)
        assert len(legal_moves) > 0
        # Should contain both move and wall placement options
        assert any(move.startswith("*") for move in legal_moves)
        assert any(move.startswith("H") or move.startswith("V") for move in legal_moves)


@pytest.mark.asyncio
class TestGameManagerAnalysis:
    """Test position analysis functionality."""
    
    async def test_analyze_position(self, game_manager: GameManager):
        """Test position analysis."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Analyze position
        analysis = await game_manager.analyze_position(game.game_id, depth=100)
        
        assert "evaluation" in analysis
        assert "sorted_actions" in analysis
        assert "simulations" in analysis
        assert len(analysis["sorted_actions"]) > 0
        
        # Check action format
        first_action = analysis["sorted_actions"][0]
        assert "action" in first_action
        assert "visits" in first_action
        assert "equity" in first_action
    
    async def test_get_hint(self, game_manager: GameManager):
        """Test getting move hints."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Get hint
        hint = await game_manager.get_hint(game.game_id, simulations=100)
        
        assert "action" in hint
        assert "confidence" in hint
        assert "evaluation" in hint
        assert 0 <= hint["confidence"] <= 1
    
    async def test_get_board_display(self, game_manager: GameManager):
        """Test getting board display."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Get display
        display = await game_manager.get_board_display(game.game_id)
        assert isinstance(display, str)
        assert len(display) > 0
        
        # Get flipped display
        flipped = await game_manager.get_board_display(game.game_id, flip=True)
        assert isinstance(flipped, str)
        # Flipped should be different from normal
        assert flipped != display


@pytest.mark.asyncio
class TestGameManagerEndGame:
    """Test game ending scenarios."""
    
    async def test_resign_game(self, game_manager: GameManager):
        """Test player resignation."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Player 1 resigns
        winner = await game_manager.resign_game(game.game_id, game.player1.id)
        assert winner == 2
        
        # Check game state
        updated_game = await game_manager.get_game(game.game_id)
        assert updated_game.status == GameStatus.COMPLETED
        assert updated_game.winner == 2
        assert updated_game.termination_reason == "resignation"
    
    async def test_resign_invalid_player(self, game_manager: GameManager):
        """Test resignation with invalid player."""
        # Create a game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Invalid player tries to resign
        with pytest.raises(ValueError, match="Player not in game"):
            await game_manager.resign_game(game.game_id, "invalid-player")


@pytest.mark.asyncio
class TestGameManagerMatchmaking:
    """Test matchmaking functionality."""
    
    async def test_join_matchmaking_queue(self, game_manager: GameManager):
        """Test joining matchmaking queue."""
        # First player joins
        result = await game_manager.join_matchmaking(
            player_id="player1",
            player_name="Alice"
        )
        assert result is None  # No match yet
        assert len(game_manager.matchmaking_queue) == 1
    
    async def test_instant_match(self, game_manager: GameManager):
        """Test instant match when opponent is waiting."""
        # First player joins
        await game_manager.join_matchmaking(
            player_id="player1",
            player_name="Alice"
        )
        
        # Second player joins and gets matched
        game = await game_manager.join_matchmaking(
            player_id="player2",
            player_name="Bob"
        )
        
        assert game is not None
        assert game.mode == GameMode.PVP
        assert game.player1.name == "Alice"
        assert game.player2.name == "Bob"
        assert len(game_manager.matchmaking_queue) == 0
    
    async def test_leave_matchmaking(self, game_manager: GameManager):
        """Test leaving matchmaking queue."""
        # Join queue
        await game_manager.join_matchmaking(
            player_id="player1",
            player_name="Alice"
        )
        
        # Leave queue
        success = await game_manager.leave_matchmaking("player1")
        assert success is True
        assert len(game_manager.matchmaking_queue) == 0
    
    async def test_get_queue_position(self, game_manager: GameManager):
        """Test getting position in queue."""
        # Add multiple players
        for i in range(3):
            await game_manager.join_matchmaking(
                player_id=f"player{i}",
                player_name=f"Player{i}"
            )
        
        # Check positions
        pos1 = await game_manager.get_queue_position("player0")
        pos2 = await game_manager.get_queue_position("player1")
        pos3 = await game_manager.get_queue_position("player2")
        
        assert pos1 == 1
        assert pos2 == 2
        assert pos3 == 3
        
        # Non-existent player
        pos = await game_manager.get_queue_position("nonexistent")
        assert pos == -1


@pytest.mark.asyncio
class TestGameManagerAI:
    """Test AI move processing."""
    
    async def test_process_ai_moves(self, game_manager: GameManager):
        """Test AI move processing."""
        # MCTS is mocked via autouse fixture above
        
        # Create PvM game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.MACHINE
        )
        
        # Make human move
        await game_manager.make_move(
            game_id=game.game_id,
            player_id=game.player1.id,
            action="*(4,1)"
        )
        
        # Process AI move (normally runs in background)
        await game_manager.ai_move_queue.put(game.game_id)
        
        # Create a task for process_ai_moves and run one iteration
        task = asyncio.create_task(game_manager.process_ai_moves())
        await asyncio.sleep(0.1)  # Let it process
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Check AI made a move
        updated_game = await game_manager.get_game(game.game_id)
        assert len(updated_game.move_history) == 2
        assert updated_game.current_turn == 1  # Back to human


@pytest.mark.asyncio
class TestGameManagerStatistics:
    """Test statistics functionality."""
    
    async def test_get_player_stats(self, game_manager: GameManager):
        """Test getting player statistics."""
        # Create and complete some games
        player_id = "test-player"
        
        # Win a game
        game1 = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN,
            player1_id=player_id
        )
        await game_manager.resign_game(game1.game_id, game1.player2.id)
        
        # Lose a game
        game2 = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN,
            player2_id=player_id
        )
        await game_manager.resign_game(game2.game_id, game2.player2.id)
        
        # Get stats
        stats = await game_manager.get_player_stats(player_id)
        assert stats is not None
        assert stats["games_played"] == 2
        assert stats["wins"] == 1
        assert stats["losses"] == 1
        assert stats["win_rate"] == 0.5
    
    async def test_get_player_stats_nonexistent(self, game_manager: GameManager):
        """Test getting stats for non-existent player."""
        stats = await game_manager.get_player_stats("nonexistent")
        assert stats is None
    
    async def test_get_leaderboard(self, game_manager: GameManager):
        """Test getting leaderboard."""
        # Create some completed games with different players
        players = ["player1", "player2", "player3"]
        for i, player in enumerate(players):
            for j in range(i + 1):  # player1 gets 0 wins, player2 gets 1, player3 gets 2
                game = await game_manager.create_game(
                    player1_type=PlayerType.HUMAN,
                    player2_type=PlayerType.HUMAN,
                    player1_id=player,
                    player2_id="opponent"
                )
                await game_manager.resign_game(game.game_id, "opponent")
        
        leaderboard = await game_manager.get_leaderboard()
        assert len(leaderboard) >= 3
        # Should be sorted by wins descending
        assert leaderboard[0]["wins"] >= leaderboard[1]["wins"] >= leaderboard[2]["wins"]
    
    async def test_get_active_game_count(self, game_manager: GameManager):
        """Test getting active game count."""
        # Create games
        for i in range(3):
            await game_manager.create_game(
                player1_type=PlayerType.HUMAN,
                player2_type=PlayerType.HUMAN
            )
        
        count = await game_manager.get_active_game_count()
        assert count == 3
        
        # Complete one game
        games = await game_manager.list_games()
        await game_manager.resign_game(games[0].game_id, games[0].player1.id)
        
        count = await game_manager.get_active_game_count()
        assert count == 2


@pytest.mark.asyncio 
class TestGameManagerAdvanced:
    """Test advanced GameManager functionality."""
    
    async def test_game_natural_termination(self, game_manager: GameManager):
        """Test game ending naturally (not by resignation)."""
        # Create game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Simulate game ending naturally by setting terminal state
        game_session = await game_manager.get_game(game.game_id)
        game_session.status = GameStatus.COMPLETED
        game_session.winner = 1
        game_session.termination_reason = "goal_reached"
        
        # Verify game ended
        updated_game = await game_manager.get_game(game.game_id)
        assert updated_game.status == GameStatus.COMPLETED
        assert updated_game.winner == 1
    
    async def test_move_validation_edge_cases(self, game_manager: GameManager):
        """Test move validation edge cases."""
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Test invalid player ID
        with pytest.raises(ValueError, match="Player not in this game"):
            await game_manager.make_move(
                game_id=game.game_id,
                player_id="invalid-player-id",
                action="*(4,1)"
            )
        
        # Test move on non-existent game
        with pytest.raises(ValueError, match="Game not found"):
            await game_manager.make_move(
                game_id="non-existent-game",
                player_id=game.player1.id,
                action="*(4,1)"
            )
    
    async def test_game_session_properties(self, game_manager: GameManager):
        """Test GameSession helper methods."""
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Test is_player method
        assert game.is_player(game.player1.id) == True
        assert game.is_player(game.player2.id) == True
        assert game.is_player("random-id") == False
        
        # Test get_player_number
        assert game.get_player_number(game.player1.id) == 1
        assert game.get_player_number(game.player2.id) == 2
        assert game.get_player_number("random-id") == 0
        
        # Test current_player property
        current_player = game.current_player
        assert current_player == game.player1  # Player 1 starts
    
    async def test_analysis_error_handling(self, game_manager: GameManager):
        """Test analysis methods error handling."""
        # Test analysis on non-existent game
        with pytest.raises(ValueError, match="Game not found"):
            await game_manager.analyze_position("non-existent", depth=100)
        
        with pytest.raises(ValueError, match="Game not found"):
            await game_manager.get_hint("non-existent", simulations=100)
        
        with pytest.raises(ValueError, match="Game not found"):
            await game_manager.get_board_display("non-existent")
    
    async def test_matchmaking_edge_cases(self, game_manager: GameManager):
        """Test matchmaking edge cases."""
        # Test leaving queue when not in queue
        success = await game_manager.leave_matchmaking("not-in-queue")
        assert success == False
        
        # Test queue position for non-existent player
        position = await game_manager.get_queue_position("not-in-queue")
        assert position == -1
        
        # Test multiple joins by same player
        await game_manager.join_matchmaking("player1", "Player1")
        result = await game_manager.join_matchmaking("player1", "Player1")
        assert result is None  # Already in queue
    
    async def test_game_termination_scenarios(self, game_manager: GameManager):
        """Test different game termination scenarios."""
        # Test resignation from completed game
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN
        )
        
        # Complete the game first
        await game_manager.resign_game(game.game_id, game.player1.id)
        
        # Try to resign again (should fail)
        with pytest.raises(ValueError, match="Game not in progress"):
            await game_manager.resign_game(game.game_id, game.player2.id)