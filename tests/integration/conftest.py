"""Pytest configuration for integration tests."""

import asyncio
import os
import subprocess
import time
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.api.server import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Test configuration with dedicated settings."""
    return {
        "api_host": "127.0.0.1",
        "api_port": 8001,  # Different from default 8000
        "frontend_host": "127.0.0.1",
        "frontend_port": 3001,  # Different from default 3000
        "database_url": "sqlite+aiosqlite:///:memory:",
        "cors_origins": ["http://localhost:3001", "http://127.0.0.1:3001"],
        "websocket_timeout": 5,
        "connection_retry_max": 3,
        "connection_retry_delay": 0.5,
    }


@pytest_asyncio.fixture
async def test_client(test_config) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for API testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
    ) as client:
        yield client


@pytest.fixture(scope="session")
def backend_server(test_config):
    """Start backend server for integration tests."""
    env = os.environ.copy()
    env.update({
        "MCTS_API_HOST": test_config["api_host"],
        "MCTS_API_PORT": str(test_config["api_port"]),
        "MCTS_CORS_ORIGINS": ",".join(test_config["cors_origins"]),
        "MCTS_DATABASE_URL": test_config["database_url"],
    })
    
    # Start backend server
    process = subprocess.Popen(
        ["python", "-m", "uvicorn", "backend.api.server:app", 
         "--host", test_config["api_host"],
         "--port", str(test_config["api_port"])],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to be ready
    max_retries = 30
    for _ in range(max_retries):
        try:
            import requests
            response = requests.get(
                f"http://{test_config['api_host']}:{test_config['api_port']}/health"
            )
            if response.status_code == 200:
                break
        except:
            time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError("Backend server failed to start")
    
    yield process
    
    # Cleanup
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="session")
def frontend_server(test_config):
    """Start frontend development server for E2E tests."""
    env = os.environ.copy()
    env.update({
        "REACT_APP_API_URL": f"http://{test_config['api_host']}:{test_config['api_port']}",
        "REACT_APP_WS_URL": f"ws://{test_config['api_host']}:{test_config['api_port']}/ws",
        "PORT": str(test_config["frontend_port"]),
    })
    
    # Build frontend first
    subprocess.run(
        ["npm", "run", "build"],
        cwd="frontend",
        env=env,
        check=True
    )
    
    # Start frontend server
    process = subprocess.Popen(
        ["npm", "run", "serve", "--", "-l", str(test_config["frontend_port"])],
        cwd="frontend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to be ready
    max_retries = 30
    for _ in range(max_retries):
        try:
            import requests
            response = requests.get(
                f"http://{test_config['frontend_host']}:{test_config['frontend_port']}"
            )
            if response.status_code == 200:
                break
        except:
            time.sleep(0.5)
    else:
        process.terminate()
        raise RuntimeError("Frontend server failed to start")
    
    yield process
    
    # Cleanup
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture
def seeded_game_data():
    """Provide seeded game data for consistent testing."""
    return {
        "game_id": "test-game-001",
        "player1_id": "test-player-001",
        "player2_id": "test-player-002",
        "test_moves": [
            {"action": 42, "player": "test-player-001"},
            {"action": 53, "player": "test-player-002"},
        ]
    }


@pytest_asyncio.fixture
async def websocket_client(test_config):
    """Create WebSocket client for testing."""
    import websockets
    
    uri = f"ws://{test_config['api_host']}:{test_config['api_port']}/ws"
    async with websockets.connect(uri) as websocket:
        yield websocket