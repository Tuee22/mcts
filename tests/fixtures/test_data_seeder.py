"""Test data seeding utilities for consistent test environments."""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Union

import httpx
from httpx import AsyncClient

from tests.models.response_models import GameListResponse, GameResponse, HealthResponse


class TestDataSeeder:
    """Utility class for seeding test data in backend for integration tests."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.client: Optional[AsyncClient] = None

    async def __aenter__(self) -> "TestDataSeeder":
        self.client = AsyncClient(base_url=self.base_url)
        return self

    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None:
        if self.client is not None:
            await self.client.aclose()

    async def seed_test_games(self, count: int = 5) -> List[Dict[str, object]]:
        """Seed test games with various configurations."""
        games: List[Dict[str, object]] = []

        for i in range(count):
            game_config = {
                "player1_type": "human",
                "player2_type": "machine" if i % 2 == 0 else "human",
                "player1_name": f"TestPlayer{i}_1",
                "player2_name": f"TestPlayer{i}_2" if i % 2 != 0 else "AI",
                "settings": {
                    "board_size": 9 if i < 3 else 7,
                    "time_limit_seconds": 30,
                    "use_analysis": i % 3 == 0,
                },
            }

            if self.client is None:
                raise RuntimeError("Client not initialized")
            response = await self.client.post("/games", json=game_config)
            response.raise_for_status()
            json_response = response.json()
            assert isinstance(json_response, dict)
            games.append(json_response)

        return games

    async def cleanup_test_games(self, game_ids: List[str]) -> None:
        """Clean up test games after test completion."""
        if self.client is None:
            raise RuntimeError("Client not initialized")

        for game_id in game_ids:
            try:
                response = await self.client.delete(f"/games/{game_id}")
                if response.status_code != 404:  # OK if already deleted
                    response.raise_for_status()
            except Exception as e:
                print(f"Warning: Could not cleanup game {game_id}: {e}")

    async def seed_game_with_moves(
        self, moves: List[str], game_config: Optional[Dict[str, object]] = None
    ) -> Dict[str, object]:
        """Seed a game and execute a sequence of moves."""
        if self.client is None:
            raise RuntimeError("Client not initialized")

        # Create game
        config = game_config or {
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": "TestPlayer1",
            "player2_name": "TestPlayer2",
        }

        response = await self.client.post("/games", json=config)
        response.raise_for_status()
        game = response.json()
        assert isinstance(game, dict)

        # Execute moves
        for move in moves:
            move_data = {"action": move}
            response = await self.client.post(
                f"/games/{game['id']}/moves", json=move_data
            )
            response.raise_for_status()

        return game

    async def verify_server_health(self) -> HealthResponse:
        """Verify the test server is healthy and responsive."""
        if self.client is None:
            raise RuntimeError("Client not initialized")

        response = await self.client.get("/health")
        response.raise_for_status()
        json_response = response.json()
        assert isinstance(json_response, dict)
        return HealthResponse(**json_response)

    async def get_test_game_list(self) -> GameListResponse:
        """Get list of all games for test verification."""
        if self.client is None:
            raise RuntimeError("Client not initialized")

        response = await self.client.get("/games")
        response.raise_for_status()
        json_response = response.json()
        assert isinstance(json_response, dict)
        return GameListResponse(**json_response)
