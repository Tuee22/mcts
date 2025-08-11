"""
Tests for FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json

# Fixtures imported from conftest.py  # Import all fixtures
from api.models import GameStatus, GameMode, PlayerType


# MCTS mock fixture for endpoint tests
@pytest.fixture(autouse=True)
def mock_mcts():
    """Mock MCTS for endpoint tests."""
    mock_mcts = MagicMock()
    mock_mcts.get_sorted_actions.return_value = [
        (100, 0.8, "*(4,1)"),
        (50, 0.6, "*(3,0)"),
        (30, 0.4, "H(4,0)")
    ]
    mock_mcts.choose_best_action.return_value = "*(4,1)"
    mock_mcts.get_evaluation.return_value = None
    mock_mcts.display.return_value = "Test Board Display"
    mock_mcts.ensure_sims.return_value = None
    mock_mcts.make_move.return_value = None
    mock_mcts.get_legal_moves.return_value = ["*(4,1)", "*(3,0)", "H(4,0)"]
    
    with patch('api.game_manager.Corridors_MCTS', return_value=mock_mcts):
        yield mock_mcts


class TestGameManagementEndpoints:
    """Test game management endpoints."""
    
    def test_create_game_pvp(self, test_client: TestClient, pvp_game_request):
        """Test creating a PvP game."""
        response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == GameMode.PVP.value
        assert data["status"] == GameStatus.IN_PROGRESS.value
        assert data["player1"]["name"] == "Alice"
        assert data["player2"]["name"] == "Bob"
        assert "game_id" in data
    
    def test_create_game_pvm(self, test_client: TestClient, pvm_game_request):
        """Test creating a PvM game."""
        response = test_client.post(
            "/games",
            json=pvm_game_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == GameMode.PVM.value
        assert data["player2"]["type"] == PlayerType.MACHINE.value
    
    def test_create_game_mvm(self, test_client: TestClient, mvm_game_request):
        """Test creating a MvM game."""
        response = test_client.post(
            "/games",
            json=mvm_game_request.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == GameMode.MVM.value
        assert data["player1"]["type"] == PlayerType.MACHINE.value
        assert data["player2"]["type"] == PlayerType.MACHINE.value
    
    def test_get_game(self, test_client: TestClient, pvp_game_request):
        """Test getting a game by ID."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_id = create_response.json()["game_id"]
        
        # Get the game
        response = test_client.get(f"/games/{game_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == game_id
        assert data["status"] == GameStatus.IN_PROGRESS.value
    
    def test_get_nonexistent_game(self, test_client: TestClient):
        """Test getting a non-existent game."""
        response = test_client.get("/games/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_list_games(self, test_client: TestClient, pvp_game_request):
        """Test listing games."""
        # Create multiple games
        game_ids = []
        for i in range(3):
            response = test_client.post(
                "/games",
                json=pvp_game_request.dict()
            )
            game_ids.append(response.json()["game_id"])
        
        # List all games
        response = test_client.get("/games")
        assert response.status_code == 200
        data = response.json()
        assert "games" in data
        assert len(data["games"]) >= 3
        
        # List with filters
        response = test_client.get(
            "/games",
            params={"status": GameStatus.IN_PROGRESS.value}
        )
        assert response.status_code == 200
        data = response.json()
        for game in data["games"]:
            assert game["status"] == GameStatus.IN_PROGRESS.value
    
    def test_delete_game(self, test_client: TestClient, pvp_game_request):
        """Test deleting a game."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_id = create_response.json()["game_id"]
        
        # Delete the game
        response = test_client.delete(f"/games/{game_id}")
        assert response.status_code == 200
        
        # Verify it's deleted
        response = test_client.get(f"/games/{game_id}")
        assert response.status_code == 404


class TestGamePlayEndpoints:
    """Test game play endpoints."""
    
    @pytest.mark.asyncio
    async def test_make_move(self, test_client: TestClient, pvp_game_request):
        """Test making a valid move."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # Make a move
        response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player1_id,
                "action": "*(4,1)"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["move"]["action"] == "*(4,1)"
        assert data["next_turn"] == 2
    
    @pytest.mark.asyncio
    async def test_make_invalid_move(self, test_client: TestClient, pvp_game_request):
        """Test making an invalid move."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # Try invalid move
        response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player1_id,
                "action": "*(9,9)"  # Out of bounds
            }
        )
        assert response.status_code == 400
        assert "illegal" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_make_move_wrong_turn(self, test_client: TestClient, pvp_game_request):
        """Test making a move when it's not the player's turn."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player2_id = game_data["player2"]["id"]
        
        # Player 2 tries to move first
        response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player2_id,
                "action": "*(4,1)"
            }
        )
        assert response.status_code == 403
        assert "not your turn" in response.json()["detail"].lower()
    
    def test_get_legal_moves(self, test_client: TestClient, pvp_game_request):
        """Test getting legal moves."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_id = create_response.json()["game_id"]
        
        # Get legal moves
        response = test_client.get(f"/games/{game_id}/legal-moves")
        assert response.status_code == 200
        data = response.json()
        assert "legal_moves" in data
        assert isinstance(data["legal_moves"], list)
        assert len(data["legal_moves"]) > 0
    
    def test_get_board_state(self, test_client: TestClient, pvp_game_request):
        """Test getting board state."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_id = create_response.json()["game_id"]
        
        # Get board state
        response = test_client.get(f"/games/{game_id}/board")
        assert response.status_code == 200
        data = response.json()
        assert "board" in data
        assert "current_turn" in data
        assert data["move_count"] == 0
        
        # Get flipped board
        response = test_client.get(
            f"/games/{game_id}/board",
            params={"flip": True}
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_resign_game(self, test_client: TestClient, pvp_game_request):
        """Test resigning from a game."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # Resign
        response = test_client.post(
            f"/games/{game_id}/resign",
            params={"player_id": player1_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["winner"] == 2  # Player 2 wins
        
        # Check game status
        response = test_client.get(f"/games/{game_id}")
        assert response.status_code == 200
        game = response.json()
        assert game["status"] == GameStatus.COMPLETED.value
        assert game["winner"] == 2


class TestAIAnalysisEndpoints:
    """Test AI analysis endpoints."""
    
    def test_get_position_analysis(self, test_client: TestClient, pvp_game_request):
        """Test getting position analysis."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_id = create_response.json()["game_id"]
        
        # Get analysis
        response = test_client.get(
            f"/games/{game_id}/analysis",
            params={"depth": 100}
        )
        assert response.status_code == 200
        data = response.json()
        assert "best_moves" in data
        assert "total_simulations" in data
        assert isinstance(data["best_moves"], list)
    
    def test_get_move_hint(self, test_client: TestClient, pvp_game_request):
        """Test getting a move hint."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # Get hint
        response = test_client.post(
            f"/games/{game_id}/hint",
            params={
                "player_id": player1_id,
                "simulations": 100
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggested_move" in data
        assert "confidence" in data
        assert "evaluation" in data
    
    def test_hint_unauthorized_player(self, test_client: TestClient, pvp_game_request):
        """Test getting hint for a player not in the game."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        game_id = create_response.json()["game_id"]
        
        # Try to get hint with invalid player ID
        response = test_client.post(
            f"/games/{game_id}/hint",
            params={
                "player_id": "invalid-player",
                "simulations": 100
            }
        )
        assert response.status_code == 403
        assert "not a player" in response.json()["detail"].lower()


class TestMatchmakingEndpoints:
    """Test matchmaking endpoints."""
    
    def test_join_matchmaking_queue(self, test_client: TestClient, default_game_settings):
        """Test joining matchmaking queue."""
        response = test_client.post(
            "/matchmaking/queue",
            params={
                "player_id": "player-1",
                "player_name": "Alice"
            },
            json=default_game_settings.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert "position" in data
    
    def test_matchmaking_instant_match(self, test_client: TestClient, default_game_settings):
        """Test instant match when another player is waiting."""
        # First player joins
        response1 = test_client.post(
            "/matchmaking/queue",
            params={
                "player_id": "player-1",
                "player_name": "Alice"
            },
            json=default_game_settings.dict()
        )
        assert response1.json()["status"] == "queued"
        
        # Second player joins and gets matched
        response2 = test_client.post(
            "/matchmaking/queue",
            params={
                "player_id": "player-2",
                "player_name": "Bob"
            },
            json=default_game_settings.dict()
        )
        assert response2.status_code == 200
        data = response2.json()
        assert data["status"] == "matched"
        assert "game_id" in data
        assert data["opponent"] == "Alice"
    
    def test_leave_matchmaking_queue(self, test_client: TestClient, default_game_settings):
        """Test leaving matchmaking queue."""
        # Join queue
        test_client.post(
            "/matchmaking/queue",
            params={
                "player_id": "player-1",
                "player_name": "Alice"
            },
            json=default_game_settings.dict()
        )
        
        # Leave queue
        response = test_client.delete("/matchmaking/queue/player-1")
        assert response.status_code == 200
        
        # Try to leave again (not in queue)
        response = test_client.delete("/matchmaking/queue/player-1")
        assert response.status_code == 404


class TestStatisticsEndpoints:
    """Test statistics endpoints."""
    
    def test_get_leaderboard(self, test_client: TestClient):
        """Test getting leaderboard."""
        response = test_client.get("/stats/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
    
    def test_get_player_stats(self, test_client: TestClient, pvp_game_request):
        """Test getting player statistics."""
        # Create a game
        create_response = test_client.post(
            "/games",
            json=pvp_game_request.dict()
        )
        player_id = create_response.json()["player1"]["id"]
        
        # Get stats
        response = test_client.get(f"/stats/player/{player_id}")
        assert response.status_code == 200
        data = response.json()
        assert "games_played" in data
        assert "wins" in data
        assert "win_rate" in data
    
    def test_get_nonexistent_player_stats(self, test_client: TestClient):
        """Test getting stats for non-existent player."""
        response = test_client.get("/stats/player/nonexistent")
        assert response.status_code == 404


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check(self, test_client: TestClient):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_games" in data
        assert "connected_clients" in data