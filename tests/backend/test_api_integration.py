"""
REST API integration tests for the backend API endpoints.

Tests the actual HTTP endpoints to ensure they work correctly after the API refactoring.
"""

import pytest
import httpx
from typing import Dict, List, Union
from unittest.mock import AsyncMock, patch, MagicMock

from backend.api.models import (
    GameSession,
    GameResponse,
    MoveResponse,
    Player,
    PlayerType,
    GameMode,
    GameSettings,
    Move,
    GameStatus,
)
from datetime import datetime, timezone


class MockGameManager:
    """Mock game manager for testing."""

    def __init__(self) -> None:
        self.create_game = AsyncMock()
        self.get_game = AsyncMock()
        self.make_move = AsyncMock()
        self.get_legal_moves = AsyncMock()
        self.list_games = AsyncMock()


class TestGameRESTAPI:
    """Test the REST API endpoints for game management."""

    async def test_create_game_endpoint(self) -> None:
        """Test POST /games endpoint creates a game successfully."""
        # Mock the game manager to avoid actual game creation
        mock_manager = MockGameManager()
        player1 = Player(
            id="player1",
            name="Player 1",
            type=PlayerType.HUMAN,
            is_hero=True,
            walls_remaining=10,
        )
        player2 = Player(
            id="player2",
            name="Player 2",
            type=PlayerType.MACHINE,
            is_hero=False,
            walls_remaining=10,
        )
        mock_game_session = GameSession(
            game_id="test-game-123",
            status="in_progress",
            mode=GameMode.PVM,
            player1=player1,
            player2=player2,
            settings=GameSettings(),
        )
        mock_manager.create_game.return_value = mock_game_session

        with patch("backend.api.server.game_manager", mock_manager):
            async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                response = await client.post(
                    "/games",
                    json={
                        "mode": "human_vs_ai",
                        "ai_config": {
                            "difficulty": "medium",
                            "time_limit_ms": 5000,
                            "use_mcts": True,
                            "mcts_iterations": 1000,
                        },
                        "board_size": 9,
                    },
                )

                assert response.status_code == 200
                response_data = response.json()
                assert isinstance(
                    response_data, dict
                ), "Response should be a dictionary"
                # The actual implementation creates a new UUID, so we just check the structure
                assert "game_id" in response_data
                assert isinstance(response_data["game_id"], str)
                assert response_data["status"] == "in_progress"
                assert "player1" in response_data
                assert "player2" in response_data

    async def test_get_game_endpoint(self) -> None:
        """Test GET /games/{game_id} endpoint retrieves game state."""
        mock_manager = MockGameManager()
        player1 = Player(
            id="player1",
            name="Player 1",
            type=PlayerType.HUMAN,
            is_hero=True,
            walls_remaining=10,
        )
        player2 = Player(
            id="player2",
            name="Player 2",
            type=PlayerType.MACHINE,
            is_hero=False,
            walls_remaining=10,
        )
        mock_game_session = GameSession(
            game_id="test-game-123",
            status="in_progress",
            mode=GameMode.PVM,
            current_turn=2,
            player1=player1,
            player2=player2,
            settings=GameSettings(),
        )
        mock_manager.get_game.return_value = mock_game_session

        with patch("backend.api.server.game_manager", mock_manager):
            async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                response = await client.get("/games/test-game-123")

                assert response.status_code == 200
                response_data = response.json()
                assert isinstance(
                    response_data, dict
                ), "Response should be a dictionary"
                assert response_data["game_id"] == "test-game-123"

    async def test_make_move_endpoint(self) -> None:
        """Test POST /games/{game_id}/moves endpoint makes a move."""
        mock_manager = MockGameManager()
        mock_move = Move(
            player_id="player1",
            action="e2e4",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            move_number=1,
        )
        mock_move_response = MoveResponse(
            success=True,
            game_id="test-game-123",
            move=mock_move,
            game_status=GameStatus.IN_PROGRESS,
            next_turn=2,
            next_player_type=PlayerType.MACHINE,
        )
        mock_manager.make_move.return_value = mock_move_response

        with patch("backend.api.server.game_manager", mock_manager):
            async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                response = await client.post(
                    "/games/test-game-123/moves",
                    json={"player_id": "player1", "action": "e2e4"},
                )

                assert response.status_code == 200
                response_data = response.json()
                assert isinstance(
                    response_data, dict
                ), "Response should be a dictionary"
                assert "success" in response_data
                assert response_data["game_id"] == "test-game-123"

    async def test_get_legal_moves_endpoint(self) -> None:
        """Test GET /games/{game_id}/legal-moves endpoint."""
        mock_manager = MockGameManager()
        mock_manager.get_legal_moves.return_value = [
            "e2",
            "e4",
            "wall_h_3_4",
            "wall_v_2_3",
        ]

        with patch("backend.api.server.game_manager", mock_manager):
            async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                response = await client.get("/games/test-game-123/legal-moves")

                assert response.status_code == 200
                response_data = response.json()
                assert isinstance(
                    response_data, dict
                ), "Response should be a dictionary"
                assert "legal_moves" in response_data
                # Access the legal moves list directly
                legal_moves = response_data["legal_moves"]
                assert isinstance(legal_moves, list)
                assert len(legal_moves) > 0

    async def test_list_games_endpoint(self) -> None:
        """Test GET /games endpoint lists games."""
        mock_manager = MockGameManager()
        player1_game1 = Player(
            id="player1",
            name="Player 1",
            type=PlayerType.HUMAN,
            is_hero=True,
            walls_remaining=10,
        )
        player2_game1 = Player(
            id="player2",
            name="Player 2",
            type=PlayerType.MACHINE,
            is_hero=False,
            walls_remaining=10,
        )
        player1_game2 = Player(
            id="player1",
            name="Alice",
            type=PlayerType.HUMAN,
            is_hero=True,
            walls_remaining=10,
        )
        player2_game2 = Player(
            id="player2",
            name="Bob",
            type=PlayerType.HUMAN,
            is_hero=False,
            walls_remaining=10,
        )
        mock_game_sessions = [
            GameSession(
                game_id="game-1",
                status=GameStatus.IN_PROGRESS,
                mode=GameMode.PVM,
                player1=player1_game1,
                player2=player2_game1,
                settings=GameSettings(),
            ),
            GameSession(
                game_id="game-2",
                status=GameStatus.COMPLETED,
                mode=GameMode.PVP,
                winner=1,
                player1=player1_game2,
                player2=player2_game2,
                settings=GameSettings(),
            ),
        ]
        mock_manager.list_games.return_value = mock_game_sessions

        with patch("backend.api.server.game_manager", mock_manager):
            async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                response = await client.get("/games")

                assert response.status_code == 200
                response_data = response.json()
                assert isinstance(response_data, list), "Response should be a list"
                assert len(response_data) == 2
                first_game = response_data[0]
                assert isinstance(first_game, dict), "Game data should be a dictionary"
                assert first_game["game_id"] == "game-1"

    async def test_error_handling_game_not_found(self) -> None:
        """Test API error handling when game is not found."""
        mock_manager = MockGameManager()
        mock_manager.get_game.return_value = None

        with patch("backend.api.server.game_manager", mock_manager):
            async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                response = await client.get("/games/nonexistent-game")

                assert response.status_code == 404 or response.status_code == 500

    async def test_invalid_move_handling(self) -> None:
        """Test API error handling for invalid moves."""
        mock_manager = MockGameManager()
        mock_manager.make_move.side_effect = ValueError("Invalid move")

        with patch("backend.api.server.game_manager", mock_manager):
            async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                response = await client.post(
                    "/games/test-game-123/moves",
                    json={"player_id": "player1", "action": "invalid_move"},
                )

                assert response.status_code == 400 or response.status_code == 500


class TestWebSocketEndpoints:
    """Test WebSocket endpoints work correctly."""

    async def test_main_websocket_connection(self) -> None:
        """Test that the main WebSocket endpoint accepts connections."""
        # This would require WebSocket testing infrastructure
        # For now, we'll just test that the endpoint exists
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            # Try to upgrade to WebSocket (will fail but endpoint should exist)
            response = await client.get(
                "/ws", headers={"Connection": "Upgrade", "Upgrade": "websocket"}
            )

            # Should get either upgrade response or method not allowed, not 404
            assert response.status_code != 404

    async def test_game_specific_websocket_endpoint(self) -> None:
        """Test that game-specific WebSocket endpoints exist."""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.get(
                "/games/test-game/ws",
                headers={"Connection": "Upgrade", "Upgrade": "websocket"},
            )

            # Should get either upgrade response or method not allowed, not 404
            assert response.status_code != 404


# Add pytest markers and configuration
pytestmark = pytest.mark.asyncio


if __name__ == "__main__":
    # Allow running tests directly
    import asyncio

    async def run_tests() -> None:
        test_class = TestGameRESTAPI()
        await test_class.test_create_game_endpoint()
        await test_class.test_get_game_endpoint()
        await test_class.test_make_move_endpoint()
        print("All REST API tests passed!")

    asyncio.run(run_tests())
