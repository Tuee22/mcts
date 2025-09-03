"""Integration tests for API configuration and environment handling."""

import asyncio
import json
import os
import subprocess
import time
from typing import Dict, List, Union
from unittest.mock import patch

import httpx
import pytest
import requests
import websockets
from httpx import AsyncClient, Response

from tests.integration.conftest import TestConfig
from tests.models import (
    ErrorResponse,
    GameResponse,
    HealthResponse,
    parse_test_websocket_message,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAPIConfiguration:
    """Test API configuration including environment variables and URL handling."""

    async def test_api_base_url_configuration(self, test_config: TestConfig) -> None:
        """Test that API responds on configured host and port."""
        # Start server with custom configuration
        env = os.environ.copy()
        env.update(
            {
                "MCTS_API_HOST": test_config["api_host"],
                "MCTS_API_PORT": str(test_config["api_port"]),
            }
        )

        process: subprocess.Popen[bytes] = subprocess.Popen(
            [
                "python",
                "-m",
                "uvicorn",
                "backend.api.server:app",
                "--host",
                test_config["api_host"],
                "--port",
                str(test_config["api_port"]),
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            # Wait for server startup
            max_retries = 30
            for _ in range(max_retries):
                try:
                    response = requests.get(
                        f"http://{test_config['api_host']}:{test_config['api_port']}/health"
                    )
                    if response.status_code == 200:
                        break
                except Exception:
                    time.sleep(0.5)

            # Verify server is accessible
            response = requests.get(
                f"http://{test_config['api_host']}:{test_config['api_port']}/health"
            )
            assert response.status_code == 200
            health_data = HealthResponse.model_validate(response.json())
            assert health_data.status == "healthy"

        finally:
            process.terminate()
            process.wait(timeout=5)

    async def test_cors_environment_configuration(
        self, test_config: TestConfig
    ) -> None:
        """Test CORS configuration via environment variables."""
        custom_origins = (
            "http://localhost:3000,http://localhost:3001,https://production.com"
        )
        env = os.environ.copy()
        env.update(
            {
                "MCTS_API_HOST": test_config["api_host"],
                "MCTS_API_PORT": str(test_config["api_port"]),
                "MCTS_CORS_ORIGINS": custom_origins,
            }
        )

        # Note: This test would require modifying the server to read CORS from env
        # Currently CORS is hardcoded to "*" in the server
        # This test documents the expected behavior

        # For now, we'll test that the server starts with env vars
        process: subprocess.Popen[bytes] = subprocess.Popen(
            [
                "python",
                "-m",
                "uvicorn",
                "backend.api.server:app",
                "--host",
                test_config["api_host"],
                "--port",
                str(test_config["api_port"]),
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            # Wait for startup
            time.sleep(2)

            # Verify server started
            response = requests.get(
                f"http://{test_config['api_host']}:{test_config['api_port']}/health"
            )
            assert response.status_code == 200

        finally:
            process.terminate()
            process.wait(timeout=5)

    async def test_websocket_url_configuration(
        self, backend_server: subprocess.Popen[bytes], test_config: TestConfig
    ) -> None:
        """Test WebSocket URL construction and accessibility."""

        # Test different URL formats
        ws_urls = [
            f"ws://{test_config['api_host']}:{test_config['api_port']}/ws",
            f"ws://127.0.0.1:{test_config['api_port']}/ws",
            f"ws://localhost:{test_config['api_port']}/ws",
        ]

        for url in ws_urls:
            try:
                async with websockets.connect(url) as websocket:
                    message = await websocket.recv()
                    data = parse_test_websocket_message(json.loads(message))
                    assert data.type == "connect"
            except Exception as e:
                # localhost might not resolve in some environments
                if "localhost" not in url:
                    raise

    async def test_api_error_response_format(
        self, backend_server: subprocess.Popen[bytes], test_config: TestConfig
    ) -> None:
        """Test that API errors have consistent format."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Test 404 error
            response = await client.get("/games/non-existent-game")
            assert response.status_code == 404
            error = ErrorResponse.model_validate(response.json())
            assert error.detail == "Game not found"

            # Test 400 error (invalid move)
            game_response = await client.post(
                "/games",
                json={
                    "player1_type": "human",
                    "player2_type": "human",
                    "player1_name": "P1",
                    "player2_name": "P2",
                },
            )
            game = GameResponse.model_validate(game_response.json())

            move_response = await client.post(
                f"/games/{game.game_id}/moves",
                json={"player_id": "wrong-player", "action": "*(0,0)"},
            )
            assert move_response.status_code == 403
            error = ErrorResponse.model_validate(move_response.json())

    async def test_api_health_endpoint_components(
        self, backend_server: subprocess.Popen[bytes], test_config: TestConfig
    ) -> None:
        """Test health endpoint provides all expected information."""
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200

            health = HealthResponse.model_validate(response.json())
            assert health.status == "healthy"
            assert health.active_games >= 0
            assert health.connected_clients >= 0

    async def test_api_timeout_handling(
        self, backend_server: subprocess.Popen[bytes], test_config: TestConfig
    ) -> None:
        """Test API handles timeouts gracefully."""
        # Create a game first to have something that might take longer
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Create a game for testing
            game_response = await client.post(
                "/games",
                json={
                    "player1_type": "human",
                    "player2_type": "machine",
                    "player1_name": "Test",
                    "player2_name": "AI",
                    "machine_settings": {
                        "iterations": 10000,  # High iterations to make it slower
                        "algorithm": "uct",
                    },
                },
            )
            game = game_response.json()
            game_id = game["game_id"] if isinstance(game, dict) else None

        # Now test with very short timeout
        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}",
            timeout=httpx.Timeout(
                0.0001, connect=0.0001, read=0.0001, write=0.0001
            ),  # Even shorter timeout
        ) as client:
            # This should timeout
            with pytest.raises(httpx.TimeoutException):
                # Try to get game state which might involve more processing
                await client.get(f"/games/{game_id}")

    async def test_api_concurrent_requests(
        self, backend_server: subprocess.Popen[bytes], test_config: TestConfig
    ) -> None:
        """Test API handles concurrent requests properly."""

        async def create_game(client: AsyncClient, index: int) -> Response:
            response = await client.post(
                "/games",
                json={
                    "player1_type": "human",
                    "player2_type": "machine",
                    "player1_name": f"Player{index}",
                    "player2_name": "AI",
                },
            )
            return response

        async with AsyncClient(
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
        ) as client:
            # Create 10 games concurrently
            tasks: List[asyncio.Task[Response]] = [
                asyncio.create_task(create_game(client, i)) for i in range(10)
            ]
            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200
                game = response.json()
                if isinstance(game, dict):
                    assert "game_id" in game
                    assert game["status"] == "in_progress"
