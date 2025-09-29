"""Pytest configuration for integration tests."""

import asyncio
import os
import subprocess
import time
from typing import AsyncGenerator, Dict, Generator, List, Optional, TypedDict, Union

import pytest
import pytest_asyncio
import requests
import websockets
from httpx import ASGITransport, AsyncClient
from websockets.client import WebSocketClientProtocol

from backend.api.server import app, game_manager, ws_manager
from backend.api.game_manager import GameManager
from backend.api.websocket_manager import WebSocketManager


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class TestConfig(TypedDict):
    api_host: str
    api_port: int
    database_url: str
    websocket_timeout: int
    connection_retry_max: int
    connection_retry_delay: float


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    """Test configuration with dedicated settings."""
    return TestConfig(
        api_host="127.0.0.1",
        api_port=8000,  # Single server serves both API and frontend
        database_url="sqlite+aiosqlite:///:memory:",
        websocket_timeout=5,
        connection_retry_max=3,
        connection_retry_delay=0.5,
    )


@pytest_asyncio.fixture
async def test_client(test_config: TestConfig) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for API testing."""
    # Set environment variable to indicate we're in a test
    os.environ["PYTEST_CURRENT_TEST"] = "true"

    # Initialize managers manually if not already initialized
    import backend.api.server as server_module

    if server_module.game_manager is None:
        server_module.game_manager = GameManager()
    if server_module.ws_manager is None:
        server_module.ws_manager = WebSocketManager()

    # Start the cleanup task for tests
    cleanup_task = asyncio.create_task(
        server_module.game_manager.cleanup_inactive_games()
    )

    try:
        # Create the transport and client
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url=f"http://{test_config['api_host']}:{test_config['api_port']}",
        ) as client:
            yield client
    finally:
        # Cancel the cleanup task
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


@pytest.fixture(scope="session")
def backend_server(
    test_config: TestConfig,
) -> Generator[Union[subprocess.Popen[bytes], None], None, None]:
    """Start backend server for integration tests or use existing one."""
    # First check if server is already running
    try:
        response = requests.get(
            f"http://{test_config['api_host']}:{test_config['api_port']}/health",
            timeout=1,
        )
        if response.status_code == 200:
            print(f"Using existing backend server on port {test_config['api_port']}")
            yield None  # No process to manage
            return
    except Exception:
        pass  # Server not running, we'll start one

    # If we're in a Docker container, don't try to start a subprocess
    # as it may not work properly
    if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
        print("Running in Docker container, assuming backend server is available")
        # Wait a bit for server to be ready
        max_retries = 10
        for _ in range(max_retries):
            try:
                response = requests.get(
                    f"http://{test_config['api_host']}:{test_config['api_port']}/health",
                    timeout=1,
                )
                if response.status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)
        yield None
        return

    # Start backend server only if not in Docker and server not already running
    env = os.environ.copy()
    env.update(
        {
            "MCTS_API_HOST": test_config["api_host"],
            "MCTS_API_PORT": str(test_config["api_port"]),
            "MCTS_DATABASE_URL": test_config["database_url"],
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

    # Wait for server to be ready
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
    else:
        process.terminate()
        raise RuntimeError("Backend server failed to start")

    yield process

    # Cleanup
    if process:  # Only cleanup if we started a process
        process.terminate()
        process.wait(timeout=5)


@pytest.fixture
def seeded_game_data() -> Dict[str, Union[str, List[Dict[str, Union[int, str]]]]]:
    """Provide seeded game data for consistent testing."""
    return {
        "game_id": "test-game-001",
        "player1_id": "test-player-001",
        "player2_id": "test-player-002",
        "test_moves": [
            {"action": 42, "player": "test-player-001"},
            {"action": 53, "player": "test-player-002"},
        ],
    }


@pytest_asyncio.fixture
async def websocket_client(
    test_config: TestConfig,
) -> AsyncGenerator[WebSocketClientProtocol, None]:
    """Create WebSocket client for testing."""

    uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
    async with websockets.connect(uri) as websocket:
        yield websocket
