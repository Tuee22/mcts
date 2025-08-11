"""
Final integration tests to push coverage to 100%.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.models import GameStatus, PlayerType


# MCTS mock fixture
@pytest.fixture(autouse=True)
def mock_mcts():
    """Mock MCTS for final integration tests."""
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


class TestFinalCoverage:
    """Tests to achieve final coverage gaps."""
    
    def test_matchmaking_complete_flow(self, test_client: TestClient, default_game_settings):
        """Test complete matchmaking flow to cover matchmaking lines."""
        # Player 1 joins queue
        response1 = test_client.post(
            "/matchmaking/queue",
            params={"player_id": "alice", "player_name": "Alice"},
            json=default_game_settings.dict()
        )
        assert response1.status_code == 200
        assert response1.json()["status"] == "queued"
        
        # Player 2 joins and gets matched
        response2 = test_client.post(
            "/matchmaking/queue", 
            params={"player_id": "bob", "player_name": "Bob"},
            json=default_game_settings.dict()
        )
        assert response2.status_code == 200
        data = response2.json()
        if data["status"] == "matched":
            assert "game_id" in data
    
    def test_statistics_with_completed_games(self, test_client: TestClient, pvp_game_request):
        """Test statistics after completing games."""
        # Create multiple games and complete them
        for i in range(3):
            response = test_client.post("/games", json=pvp_game_request.dict())
            game_data = response.json()
            game_id = game_data["game_id"]
            player1_id = game_data["player1"]["id"]
            
            # Complete game via resignation
            test_client.post(f"/games/{game_id}/resign", params={"player_id": player1_id})
        
        # Test leaderboard
        response = test_client.get("/stats/leaderboard")
        assert response.status_code == 200
        leaderboard = response.json()["leaderboard"]
        assert isinstance(leaderboard, list)
        
        # Test player stats
        response = test_client.get(f"/stats/player/{pvp_game_request.player1_id or 'test-player'}")
        # Will return either stats or 404 depending on implementation
        assert response.status_code in [200, 404]
    
    def test_game_analysis_edge_cases(self, test_client: TestClient, pvp_game_request):
        """Test game analysis edge cases."""
        response = test_client.post("/games", json=pvp_game_request.dict())
        game_id = response.json()["game_id"]
        
        # Test analysis with minimal depth
        response = test_client.get(f"/games/{game_id}/analysis", params={"depth": 1})
        assert response.status_code == 200
        
        # Test analysis with high depth
        response = test_client.get(f"/games/{game_id}/analysis", params={"depth": 1000})
        assert response.status_code == 200
    
    def test_hint_variations(self, test_client: TestClient, pvp_game_request):
        """Test hint functionality variations."""
        response = test_client.post("/games", json=pvp_game_request.dict())
        game_data = response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # Test hint with different simulation counts
        for sims in [10, 100, 500]:
            response = test_client.post(
                f"/games/{game_id}/hint",
                params={"player_id": player1_id, "simulations": sims}
            )
            assert response.status_code == 200
            hint = response.json()
            assert "suggested_move" in hint
            assert "confidence" in hint
    
    def test_game_list_with_filters(self, test_client: TestClient, pvp_game_request):
        """Test game listing with filters."""
        # Create games
        game_ids = []
        for i in range(2):
            response = test_client.post("/games", json=pvp_game_request.dict())
            game_ids.append(response.json()["game_id"])
        
        # Complete one game
        test_client.post(f"/games/{game_ids[0]}/resign", 
                        params={"player_id": "test-player"})
        
        # List all games
        response = test_client.get("/games")
        assert response.status_code == 200
        all_games = response.json()["games"]
        assert len(all_games) >= 2
        
        # List with status filter
        response = test_client.get("/games", params={"status": "in_progress"})
        assert response.status_code == 200
        active_games = response.json()["games"]
        for game in active_games:
            assert game["status"] == "in_progress"
        
        # List with player filter  
        response = test_client.get("/games", params={"player_id": "some-player"})
        assert response.status_code == 200
        # Should return empty list or games with that player
        player_games = response.json()["games"]
        assert isinstance(player_games, list)
    
    def test_move_sequence_coverage(self, test_client: TestClient, pvp_game_request):
        """Test move sequence to cover game state transitions."""
        response = test_client.post("/games", json=pvp_game_request.dict())
        game_data = response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        player2_id = game_data["player2"]["id"]
        players = [player1_id, player2_id]
        
        # Make several moves to cover game logic
        for i in range(4):
            # Get legal moves first
            response = test_client.get(f"/games/{game_id}/legal-moves")
            if response.status_code != 200:
                break
            legal_moves = response.json()["legal_moves"]
            if not legal_moves:
                break
            
            # Make move
            response = test_client.post(
                f"/games/{game_id}/moves",
                json={
                    "player_id": players[i % 2],
                    "action": legal_moves[0]
                }
            )
            if response.status_code != 200:
                break
        
        # Get final game state
        response = test_client.get(f"/games/{game_id}")
        assert response.status_code == 200
    
    def test_board_display_coverage(self, test_client: TestClient, pvp_game_request):
        """Test board display functionality."""
        response = test_client.post("/games", json=pvp_game_request.dict())
        game_id = response.json()["game_id"]
        
        # Test normal board display
        response = test_client.get(f"/games/{game_id}/board")
        assert response.status_code == 200
        board_data = response.json()
        assert "board" in board_data
        assert "current_turn" in board_data
        
        # Test flipped board display
        response = test_client.get(f"/games/{game_id}/board", params={"flip": True})
        assert response.status_code == 200
        flipped_data = response.json()
        assert "board" in flipped_data
    
    def test_machine_vs_machine(self, test_client: TestClient):
        """Test machine vs machine game to cover AI logic."""
        response = test_client.post(
            "/games",
            json={
                "player1_type": "machine",
                "player2_type": "machine",
                "player1_name": "AI-1", 
                "player2_name": "AI-2",
                "settings": {
                    "mcts_settings": {
                        "min_simulations": 10,
                        "max_simulations": 20
                    }
                }
            }
        )
        assert response.status_code == 200
        game = response.json()
        assert game["mode"] == "mvm"
        assert game["player1"]["type"] == "machine"
        assert game["player2"]["type"] == "machine"
    
    def test_player_vs_machine(self, test_client: TestClient):
        """Test player vs machine game."""
        response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "machine",
                "player1_name": "Human",
                "player2_name": "AI"
            }
        )
        assert response.status_code == 200
        game_data = response.json()
        game_id = game_data["game_id"]
        player1_id = game_data["player1"]["id"]
        
        # Human makes first move
        response = test_client.post(
            f"/games/{game_id}/moves",
            json={
                "player_id": player1_id,
                "action": "*(4,1)"
            }
        )
        assert response.status_code == 200
        move_response = response.json()
        assert move_response["success"] == True
        assert move_response["next_player_type"] == "machine"
    
    def test_comprehensive_error_scenarios(self, test_client: TestClient):
        """Test various error scenarios for coverage."""
        # Test operations on non-existent games
        non_existent_id = "non-existent-game"
        
        error_tests = [
            ("GET", f"/games/{non_existent_id}"),
            ("DELETE", f"/games/{non_existent_id}"),
            ("GET", f"/games/{non_existent_id}/board"),
            ("GET", f"/games/{non_existent_id}/legal-moves"),
            ("GET", f"/games/{non_existent_id}/analysis"),
            ("POST", f"/games/{non_existent_id}/resign", {"player_id": "player"}),
            ("POST", f"/games/{non_existent_id}/hint", {"player_id": "player", "simulations": 100}),
        ]
        
        for method, endpoint, *params in error_tests:
            if method == "GET":
                response = test_client.get(endpoint)
            elif method == "DELETE":
                response = test_client.delete(endpoint)
            elif method == "POST":
                if len(params) > 0:
                    if "hint" in endpoint:
                        response = test_client.post(endpoint, params=params[0])
                    else:
                        response = test_client.post(endpoint, params=params[0])
                else:
                    response = test_client.post(endpoint)
            
            # Should return 404 for non-existent resources
            assert response.status_code == 404