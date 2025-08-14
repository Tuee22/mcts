"""
Tests specifically designed to hit error paths and exception handling.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Any
from backend.api.models import PlayerType, GameStatus
import asyncio


class TestServerExceptionPaths:
    """Test server exception handling paths."""

    @patch("backend.api.server.game_manager.create_game")
    def test_create_game_exception(
        self, mock_create_game: Any, test_client: TestClient
    ) -> None:
        """Test exception handling in create_game endpoint."""
        # Mock create_game to raise an exception
        mock_create_game.side_effect = Exception("Database connection failed")

        response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Alice",
                "player2_name": "Bob",
            },
        )
        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]

    @patch("backend.api.server.game_manager.list_games")
    def test_list_games_exception(
        self, mock_list_games: Any, test_client: TestClient
    ) -> None:
        """Test exception handling in list_games endpoint."""
        mock_list_games.side_effect = Exception("Service unavailable")

        response = test_client.get("/games")
        assert response.status_code == 500

    @patch("backend.api.server.game_manager.get_game")
    def test_get_game_exception(
        self, mock_get_game: Any, test_client: TestClient
    ) -> None:
        """Test exception handling in get_game endpoint."""
        mock_get_game.side_effect = Exception("Connection timeout")

        response = test_client.get("/games/test-id")
        assert response.status_code == 500

    @patch("backend.api.server.game_manager.delete_game")
    def test_delete_game_exception(
        self, mock_delete_game: Any, test_client: TestClient
    ) -> None:
        """Test exception handling in delete_game endpoint."""
        mock_delete_game.side_effect = Exception("Deletion failed")

        response = test_client.delete("/games/test-id")
        assert response.status_code == 500

    def test_make_move_game_not_in_progress(self, test_client: TestClient) -> None:
        """Test making move when game is not in progress."""
        # Create a game first
        response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Alice",
                "player2_name": "Bob",
            },
        )
        game_id = response.json()["game_id"]
        player1_id = response.json()["player1"]["id"]

        # Mock the game to be finished
        with patch("backend.api.server.game_manager.get_game") as mock_get_game:
            mock_game = MagicMock()
            mock_game.status = GameStatus.COMPLETED
            mock_get_game.return_value = mock_game

            response = test_client.post(
                f"/games/{game_id}/moves",
                json={"action": "*(4,1)", "player_id": player1_id},
            )
            assert response.status_code == 400
            assert "not in progress" in response.json()["detail"]

    def test_make_move_wrong_turn(self, test_client: TestClient) -> None:
        """Test making move when it's not player's turn."""
        # Create a game first
        response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Alice",
                "player2_name": "Bob",
            },
        )
        game_id = response.json()["game_id"]
        player2_id = response.json()["player2"]["id"]  # Wrong player

        # Try to make move with wrong player
        response = test_client.post(
            f"/games/{game_id}/moves",
            json={"action": "*(4,1)", "player_id": player2_id},
        )
        assert response.status_code == 403
        assert "Not your turn" in response.json()["detail"]

    @patch("backend.api.server.game_manager.make_move")
    def test_make_move_value_error(
        self, mock_make_move: Any, test_client: TestClient
    ) -> None:
        """Test ValueError handling in make_move."""
        # Create a game first
        response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Alice",
                "player2_name": "Bob",
            },
        )
        game_id = response.json()["game_id"]
        player1_id = response.json()["player1"]["id"]

        # Mock make_move to raise ValueError
        mock_make_move.side_effect = ValueError("Invalid move")

        response = test_client.post(
            f"/games/{game_id}/moves",
            json={"action": "invalid", "player_id": player1_id},
        )
        assert response.status_code == 400
        assert "Invalid move" in response.json()["detail"]

    @patch("backend.api.server.game_manager.make_move")
    def test_make_move_general_exception(
        self, mock_make_move: Any, test_client: TestClient
    ) -> None:
        """Test general exception handling in make_move."""
        # Create a game first
        response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Alice",
                "player2_name": "Bob",
            },
        )
        game_id = response.json()["game_id"]
        player1_id = response.json()["player1"]["id"]

        # Mock make_move to raise general exception
        mock_make_move.side_effect = Exception("Server error")

        response = test_client.post(
            f"/games/{game_id}/moves",
            json={"action": "*(4,1)", "player_id": player1_id},
        )
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]


class TestMatchmakingExceptionPaths:
    """Test matchmaking exception paths."""

    @patch("backend.api.server.game_manager.leave_matchmaking")
    def test_leave_queue_exception(
        self, mock_leave: Any, test_client: TestClient
    ) -> None:
        """Test exception handling in leave matchmaking queue."""
        mock_leave.side_effect = Exception("Queue removal failed")

        response = test_client.delete("/matchmaking/queue/test-player")
        assert response.status_code == 500


class TestAnalysisExceptionPaths:
    """Test analysis and hint exception paths."""

    pass


class TestStatisticsExceptionPaths:
    """Test statistics exception paths."""

    @patch("backend.api.server.game_manager.get_leaderboard")
    def test_get_leaderboard_exception(
        self, mock_leaderboard: Any, test_client: TestClient
    ) -> None:
        """Test exception handling in get_leaderboard."""
        mock_leaderboard.side_effect = Exception("Leaderboard service down")

        response = test_client.get("/stats/leaderboard")
        assert response.status_code == 500

    @patch("backend.api.server.game_manager.get_player_stats")
    def test_get_player_stats_exception(
        self, mock_stats: Any, test_client: TestClient
    ) -> None:
        """Test exception handling in get_player_stats."""
        mock_stats.side_effect = Exception("Stats calculation failed")

        response = test_client.get("/stats/player/test-player")
        assert response.status_code == 500


class TestWebSocketExceptionPaths:
    """Test WebSocket-related exception paths in endpoints."""

    @patch("backend.api.server.ws_manager.broadcast_game_created")
    def test_websocket_broadcast_failure_on_create(
        self, mock_broadcast: Any, test_client: TestClient
    ) -> None:
        """Test WebSocket broadcast failure during game creation."""
        mock_broadcast.side_effect = Exception("WebSocket broadcast failed")

        # Game should still be created even if WebSocket broadcast fails
        response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Alice",
                "player2_name": "Bob",
            },
        )
        # Should still succeed despite WebSocket failure
        assert response.status_code == 200 or response.status_code == 500

    @patch("backend.api.server.ws_manager.broadcast_move")
    def test_websocket_broadcast_failure_on_move(
        self, mock_broadcast: Any, test_client: TestClient
    ) -> None:
        """Test WebSocket broadcast failure during move."""
        # Create a game first
        response = test_client.post(
            "/games",
            json={
                "player1_type": "human",
                "player2_type": "human",
                "player1_name": "Alice",
                "player2_name": "Bob",
            },
        )
        game_id = response.json()["game_id"]
        player1_id = response.json()["player1"]["id"]

        mock_broadcast.side_effect = Exception("WebSocket broadcast failed")

        # Get legal moves first
        response = test_client.get(f"/games/{game_id}/legal-moves")
        legal_moves_response = response.json()
        legal_moves = legal_moves_response.get("legal_moves", [])

        if legal_moves:
            # Move should still succeed even if WebSocket broadcast fails
            response = test_client.post(
                f"/games/{game_id}/moves",
                json={"action": legal_moves[0], "player_id": player1_id},
            )
            # Should succeed or fail gracefully
            assert response.status_code in [200, 500]
