"""
Comprehensive endpoint tests to achieve 100% coverage.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json

# Fixtures imported from conftest.py
from api.models import GameStatus, GameMode, PlayerType


# MCTS mock fixture for comprehensive endpoint tests
@pytest.fixture(autouse=True)
def mock_mcts():
    """Mock MCTS for comprehensive endpoint tests."""
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


class TestServerErrorHandling:
    """Test server error handling scenarios."""
    
    def test_create_game_invalid_player_type(self, test_client: TestClient):
        """Test creating game with invalid player type."""
        response = test_client.post(
            "/games",
            json={
                "player1_type": "invalid_type",
                "player2_type": "human",
                "player1_name": "Alice",
                "player2_name": "Bob"
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_create_game_missing_required_fields(self, test_client: TestClient):
        """Test creating game with missing required fields."""
        response = test_client.post(
            "/games",
            json={
                "player1_type": "human"
                # Missing player2_type
            }
        )
        assert response.status_code == 422
    
    def test_make_move_on_completed_game(self, test_client: TestClient, pvp_game_request):
        """Test making move on completed game."""
        # Create game
        create_response = test_client.post("/games", json=pvp_game_request.dict())
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        player2_id = game_data["player2"]["id"]
        
        # End game
        test_client.post(f"/games/{game_id}/resign", params={"player_id": player1_id})
        
        # Try to make move on completed game
        response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player2_id,
                "action": "*(4,1)"
            }
        )
        assert response.status_code == 400
        assert "not in progress" in response.json()["detail"].lower()
    
    def test_resign_non_existent_game(self, test_client: TestClient):
        """Test resigning from non-existent game."""
        response = test_client.post(
            "/games/non-existent/resign",
            params={"player_id": "some-player"}
        )
        assert response.status_code == 404
    
    def test_get_legal_moves_non_existent_game(self, test_client: TestClient):
        """Test getting legal moves for non-existent game."""
        response = test_client.get("/games/non-existent/legal-moves")
        assert response.status_code == 404
    
    def test_get_board_non_existent_game(self, test_client: TestClient):
        """Test getting board for non-existent game."""
        response = test_client.get("/games/non-existent/board")
        assert response.status_code == 404
    
    def test_analysis_non_existent_game(self, test_client: TestClient):
        """Test analysis on non-existent game."""
        response = test_client.get("/games/non-existent/analysis")
        assert response.status_code == 404
    
    def test_hint_non_existent_game(self, test_client: TestClient):
        """Test hint for non-existent game."""
        response = test_client.post(
            "/games/non-existent/hint",
            params={"player_id": "player", "simulations": 100}
        )
        assert response.status_code == 404
    
    def test_hint_unauthorized_player(self, test_client: TestClient, pvp_game_request):
        """Test hint for player not in game."""
        create_response = test_client.post("/games", json=pvp_game_request.dict())
        game_id = create_response.json()["game_id"]
        
        response = test_client.post(
            f"/games/{game_id}/hint",
            params={"player_id": "unauthorized-player", "simulations": 100}
        )
        assert response.status_code == 403


class TestServerAdvancedFeatures:
    """Test advanced server features."""
    
    def test_list_games_with_filters(self, test_client: TestClient, pvp_game_request):
        """Test listing games with various filters."""
        # Create multiple games
        game_ids = []
        for i in range(3):
            response = test_client.post("/games", json=pvp_game_request.dict())
            game_ids.append(response.json()["game_id"])
        
        # Complete one game
        test_client.post(f"/games/{game_ids[0]}/resign", 
                        params={"player_id": "some-player"})
        
        # Test status filter
        response = test_client.get("/games", params={"status": "in_progress"})
        assert response.status_code == 200
        games = response.json()["games"]
        for game in games:
            assert game["status"] == "in_progress"
        
        # Test player filter (should handle non-matching gracefully)
        response = test_client.get("/games", params={"player_id": "non-existent"})
        assert response.status_code == 200
        assert len(response.json()["games"]) == 0
    
    def test_game_settings_variations(self, test_client: TestClient):
        """Test creating games with different settings."""
        # Test with custom MCTS settings
        response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "machine",
                "settings": {
                    "mcts_settings": {
                        "c": 0.5,
                        "min_simulations": 50,
                        "max_simulations": 200,
                        "use_puct": True,
                        "seed": 12345
                    },
                    "allow_hints": False,
                    "allow_analysis": False
                }
            }
        )
        assert response.status_code == 200
        game = response.json()
        assert game["settings"]["mcts_settings"]["c"] == 0.5
        assert game["settings"]["allow_hints"] == False
    
    def test_statistics_endpoints_edge_cases(self, test_client: TestClient):
        """Test statistics endpoints edge cases."""
        # Test leaderboard when no games exist
        response = test_client.get("/stats/leaderboard")
        assert response.status_code == 200
        assert response.json()["leaderboard"] == []
        
        # Test player stats for non-existent player
        response = test_client.get("/stats/player/non-existent")
        assert response.status_code == 404
    
    def test_analysis_with_parameters(self, test_client: TestClient, pvp_game_request):
        """Test analysis with different parameters."""
        create_response = test_client.post("/games", json=pvp_game_request.dict())
        game_id = create_response.json()["game_id"]
        
        # Test analysis with different depth values
        for depth in [50, 100, 500]:
            response = test_client.get(
                f"/games/{game_id}/analysis",
                params={"depth": depth}
            )
            assert response.status_code == 200
            assert "best_moves" in response.json()
    
    def test_board_display_variations(self, test_client: TestClient, pvp_game_request):
        """Test board display with different parameters."""
        create_response = test_client.post("/games", json=pvp_game_request.dict())
        game_id = create_response.json()["game_id"]
        
        # Test normal board
        response = test_client.get(f"/games/{game_id}/board")
        assert response.status_code == 200
        normal_board = response.json()["board"]
        
        # Test flipped board
        response = test_client.get(f"/games/{game_id}/board", params={"flip": True})
        assert response.status_code == 200
        flipped_board = response.json()["board"]
        
        # Boards should be different when flipped
        assert normal_board != flipped_board
    
    def test_move_response_details(self, test_client: TestClient, pvp_game_request):
        """Test detailed move response information."""
        create_response = test_client.post("/games", json=pvp_game_request.dict())
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player1_id,
                "action": "*(4,1)"
            }
        )
        assert response.status_code == 200
        move_response = response.json()
        
        # Verify response structure
        assert "success" in move_response
        assert "move" in move_response
        assert "next_turn" in move_response
        assert "game_status" in move_response
        assert "next_player_type" in move_response
        
        # Verify move details
        assert move_response["move"]["action"] == "*(4,1)"
        assert move_response["move"]["player_id"] == player1_id
        assert move_response["move"]["move_number"] == 1


class TestServerValidationAndSecurity:
    """Test input validation and security aspects."""
    
    def test_malformed_json_requests(self, test_client: TestClient):
        """Test handling of malformed JSON requests."""
        response = test_client.post(
            "/games",
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_oversized_parameters(self, test_client: TestClient, pvp_game_request):
        """Test handling of oversized parameters."""
        # Test with very long names
        long_name = "x" * 1000
        request = pvp_game_request.dict()
        request["player1_name"] = long_name
        
        response = test_client.post("/games", json=request)
        # Should still work (server should handle gracefully)
        assert response.status_code in [200, 422]
    
    def test_special_characters_in_names(self, test_client: TestClient):
        """Test handling of special characters in player names."""
        response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Player<script>alert('xss')</script>",
                "player2_name": "Player'\"DROP TABLE games;"
            }
        )
        assert response.status_code == 200
        # Names should be sanitized or handled safely
        game = response.json()
        assert "script" not in game["player1"]["name"].lower()
    
    def test_concurrent_move_attempts(self, test_client: TestClient, pvp_game_request):
        """Test concurrent move attempts on same game."""
        create_response = test_client.post("/games", json=pvp_game_request.dict())
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        player2_id = game_data["player2"]["id"]
        
        # Player 1 makes valid move
        response1 = test_client.post(
            f"/games/{game_id}/moves",
            json={"player_id": player1_id, "action": "*(4,1)"}
        )
        assert response1.status_code == 200
        
        # Player 1 tries to move again (should fail - not their turn)
        response2 = test_client.post(
            f"/games/{game_id}/moves",
            json={"player_id": player1_id, "action": "*(3,0)"}
        )
        assert response2.status_code == 403
        
        # Player 2 makes valid move
        response3 = test_client.post(
            f"/games/{game_id}/moves",
            json={"player_id": player2_id, "action": "*(4,7)"}
        )
        assert response3.status_code == 200


class TestServerPerformanceAndLimits:
    """Test server performance and limit handling."""
    
    def test_analysis_depth_limits(self, test_client: TestClient, pvp_game_request):
        """Test analysis depth limits."""
        create_response = test_client.post("/games", json=pvp_game_request.dict())
        game_id = create_response.json()["game_id"]
        
        # Test extreme depth values
        for depth in [1, 10000]:
            response = test_client.get(
                f"/games/{game_id}/analysis",
                params={"depth": depth}
            )
            assert response.status_code == 200
    
    def test_hint_simulation_limits(self, test_client: TestClient, pvp_game_request):
        """Test hint simulation limits."""
        create_response = test_client.post("/games", json=pvp_game_request.dict())
        game_data = create_response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # Test extreme simulation values
        for sims in [1, 10000]:
            response = test_client.post(
                f"/games/{game_id}/hint",
                params={"player_id": player1_id, "simulations": sims}
            )
            assert response.status_code == 200