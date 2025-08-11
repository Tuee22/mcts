"""
Integration tests for complete game flows.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Fixtures imported from conftest.py  # Import all fixtures
from api.models import GameStatus, PlayerType


# MCTS mock fixture for integration tests
@pytest.fixture(autouse=True)
def mock_mcts():
    """Mock MCTS for integration tests."""
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


class TestCompleteGameFlows:
    """Test complete game flows from start to finish."""
    
    def test_pvp_game_complete_flow(self, test_client: TestClient):
        """Test a complete PvP game flow."""
        # 1. Create game
        create_response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Alice",
                "player2_name": "Bob"
            }
        )
        assert create_response.status_code == 200
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        player2_id = game_data["player2"]["id"]
        
        # 2. Get initial board state
        board_response = test_client.get(f"/games/{game_id}/board")
        assert board_response.status_code == 200
        assert "board" in board_response.json()
        
        # 3. Get legal moves for player 1
        legal_moves_response = test_client.get(f"/games/{game_id}/legal-moves")
        assert legal_moves_response.status_code == 200
        legal_moves = legal_moves_response.json()["legal_moves"]
        assert len(legal_moves) > 0
        
        # 4. Player 1 makes a move
        move1_response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player1_id,
                "action": legal_moves[0]  # Use first legal move
            }
        )
        assert move1_response.status_code == 200
        assert move1_response.json()["next_turn"] == 2
        
        # 5. Get updated legal moves for player 2
        legal_moves_response = test_client.get(f"/games/{game_id}/legal-moves")
        legal_moves = legal_moves_response.json()["legal_moves"]
        
        # 6. Player 2 makes a move
        move2_response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player2_id,
                "action": legal_moves[0]
            }
        )
        assert move2_response.status_code == 200
        assert move2_response.json()["next_turn"] == 1
        
        # 7. Player 1 resigns
        resign_response = test_client.post(
            f"/games/{game_id}/resign",
            params={"player_id": player1_id}
        )
        assert resign_response.status_code == 200
        assert resign_response.json()["winner"] == 2
        
        # 8. Verify game is completed
        game_response = test_client.get(f"/games/{game_id}")
        assert game_response.status_code == 200
        final_game = game_response.json()
        assert final_game["status"] == "completed"
        assert final_game["winner"] == 2
    
    def test_pvm_game_flow(self, test_client: TestClient):
        """Test Player vs Machine game flow."""
        # MCTS is mocked via autouse fixture above
        
        # 1. Create PvM game
        create_response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "machine",
                "player1_name": "Human",
                "player2_name": "AI",
                "settings": {
                    "mcts_settings": {
                        "min_simulations": 100
                    }
                }
            }
        )
        assert create_response.status_code == 200
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # 2. Human makes first move
        move_response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player1_id,
                "action": "*(4,1)"
            }
        )
        assert move_response.status_code == 200
        assert move_response.json()["next_player_type"] == "machine"
        
        # 3. Wait briefly for AI to process (in real scenario)
        # The AI move would be processed in background
        
        # 4. Get game state to see AI's move
        game_response = test_client.get(f"/games/{game_id}")
        assert game_response.status_code == 200
        # In a real scenario, we'd see the AI's move in move_history
    
    def test_mvm_game_flow(self, test_client: TestClient):
        """Test Machine vs Machine game flow."""
        # Create MvM game
        create_response = test_client.post(
            "/games",
            json={
                "player1_type": "machine",
                "player2_type": "machine",
                "player1_name": "AI-1",
                "player2_name": "AI-2",
                "settings": {
                    "mcts_settings": {
                        "min_simulations": 50,
                        "max_simulations": 50
                    }
                }
            }
        )
        assert create_response.status_code == 200
        game_data = create_response.json()
        game_id = game_data["game_id"]
        
        # Game should start automatically with AI moves
        # Check game state
        game_response = test_client.get(f"/games/{game_id}")
        assert game_response.status_code == 200
        assert game_response.json()["status"] == "in_progress"


class TestMatchmakingFlow:
    """Test matchmaking flow."""
    
    def test_matchmaking_flow(self, test_client: TestClient):
        """Test complete matchmaking flow."""
        # 1. First player joins queue
        join1_response = test_client.post(
            "/matchmaking/queue",
            params={
                "player_id": "alice-id",
                "player_name": "Alice"
            }
        )
        assert join1_response.status_code == 200
        assert join1_response.json()["status"] == "queued"
        
        # 2. Second player joins and gets matched
        join2_response = test_client.post(
            "/matchmaking/queue",
            params={
                "player_id": "bob-id",
                "player_name": "Bob"
            }
        )
        assert join2_response.status_code == 200
        data = join2_response.json()
        assert data["status"] == "matched"
        game_id = data["game_id"]
        
        # 3. Both players can access the game
        game_response = test_client.get(f"/games/{game_id}")
        assert game_response.status_code == 200
        game = game_response.json()
        assert game["status"] == "in_progress"
        assert game["player1"]["name"] == "Alice"
        assert game["player2"]["name"] == "Bob"


class TestAnalysisFlow:
    """Test game analysis features."""
    
    def test_hint_and_analysis_flow(self, test_client: TestClient):
        """Test getting hints and analysis during a game."""
        # 1. Create game
        create_response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human",
                "settings": {
                    "allow_hints": True,
                    "allow_analysis": True,
                    "mcts_settings": {
                        "min_simulations": 100
                    }
                }
            }
        )
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # 2. Get position analysis
        analysis_response = test_client.get(
            f"/games/{game_id}/analysis",
            params={"depth": 100}
        )
        assert analysis_response.status_code == 200
        analysis = analysis_response.json()
        assert "best_moves" in analysis
        assert len(analysis["best_moves"]) > 0
        
        # 3. Get move hint
        hint_response = test_client.post(
            f"/games/{game_id}/hint",
            params={
                "player_id": player1_id,
                "simulations": 100
            }
        )
        assert hint_response.status_code == 200
        hint = hint_response.json()
        assert "suggested_move" in hint
        assert "confidence" in hint
        
        # 4. Use the hint to make a move
        move_response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player1_id,
                "action": hint["suggested_move"]
            }
        )
        assert move_response.status_code == 200


class TestWebSocketIntegration:
    """Test WebSocket integration with game flow."""
    
    def test_websocket_game_updates(self, test_client: TestClient):
        """Test receiving game updates via WebSocket."""
        # 1. Create game
        create_response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human"
            }
        )
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # 2. Connect via WebSocket
        with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket:
            # Receive initial state
            initial_state = websocket.receive_json()
            assert initial_state["type"] == "game_state"
            
            # 3. Make a move via REST API
            test_client.post(
                f"/games/{game_id}/moves",
                json={
                    "player_id": player1_id,
                    "action": "*(4,1)"
                }
            )
            
            # 4. Receive move update via WebSocket
            move_update = websocket.receive_json()
            assert move_update["type"] == "move"
            assert move_update["data"]["move"]["action"] == "*(4,1)"


class TestErrorHandling:
    """Test error handling in various scenarios."""
    
    def test_concurrent_moves(self, test_client: TestClient):
        """Test handling concurrent move attempts."""
        # Create game
        create_response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human"
            }
        )
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        player2_id = game_data["player2"]["id"]
        
        # Player 1 makes a move
        move1_response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player1_id,
                "action": "*(4,1)"
            }
        )
        assert move1_response.status_code == 200
        
        # Player 1 tries to move again (should fail)
        move2_response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player1_id,
                "action": "*(4,2)"
            }
        )
        assert move2_response.status_code == 403
        assert "not your turn" in move2_response.json()["detail"].lower()
    
    def test_move_after_game_end(self, test_client: TestClient):
        """Test attempting moves after game ends."""
        # Create and end a game
        create_response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human"
            }
        )
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # Resign to end game
        test_client.post(
            f"/games/{game_id}/resign",
            params={"player_id": player1_id}
        )
        
        # Try to make a move
        move_response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player1_id,
                "action": "*(4,1)"
            }
        )
        assert move_response.status_code == 400
        assert "not in progress" in move_response.json()["detail"].lower()


class TestPerformance:
    """Test performance and load handling."""
    
    @pytest.mark.slow
    def test_multiple_concurrent_games(self, test_client: TestClient):
        """Test handling multiple concurrent games."""
        game_ids = []
        
        # Create 10 games concurrently
        for i in range(10):
            response = test_client.post(
                "/games",
                json={
                    "player1_type": "human",
                    "player2_type": "human",
                    "player1_name": f"Player{i*2}",
                    "player2_name": f"Player{i*2+1}"
                }
            )
            assert response.status_code == 200
            game_ids.append(response.json()["game_id"])
        
        # Verify all games exist
        for game_id in game_ids:
            response = test_client.get(f"/games/{game_id}")
            assert response.status_code == 200
        
        # List all games
        list_response = test_client.get("/games")
        assert list_response.status_code == 200
        assert len(list_response.json()["games"]) >= 10
    
    @pytest.mark.slow
    def test_rapid_moves(self, test_client: TestClient):
        """Test making moves rapidly."""
        # Create game
        create_response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human"
            }
        )
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        player2_id = game_data["player2"]["id"]
        
        # Make several moves quickly
        players = [player1_id, player2_id]
        for i in range(10):
            # Get legal moves
            legal_response = test_client.get(f"/games/{game_id}/legal-moves")
            legal_moves = legal_response.json()["legal_moves"]
            
            if not legal_moves:
                break
            
            # Make a move
            move_response = test_client.post(
                f"/games/{game_id}/moves",
                json={
                    "player_id": players[i % 2],
                    "action": legal_moves[0]
                }
            )
            
            if move_response.status_code != 200:
                break  # Game might have ended
        
        # Verify game state is consistent
        final_response = test_client.get(f"/games/{game_id}")
        assert final_response.status_code == 200