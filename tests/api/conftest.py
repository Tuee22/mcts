"""
API-specific test fixtures and configuration.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

from api.server import app
from api.game_manager import GameManager
from api.websocket_manager import WebSocketManager
from api.models import (
    GameSettings, MCTSSettings, PlayerType,
    GameCreateRequest, Player
)


# Remove session-scoped event loop - let pytest-asyncio handle it automatically


@pytest.fixture
def test_client() -> Generator:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client
    
    # Clean up global state after each test
    import api.server
    if api.server.game_manager:
        # Run cleanup in a sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule cleanup
                loop.create_task(api.server.game_manager.cleanup())
                loop.create_task(api.server.ws_manager.disconnect_all())
            else:
                # If no loop is running, run cleanup
                loop.run_until_complete(api.server.game_manager.cleanup())
                loop.run_until_complete(api.server.ws_manager.disconnect_all())
        except:
            pass  # Ignore cleanup errors in tests


@pytest.fixture
async def async_client() -> AsyncGenerator:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def game_manager():
    """Create a GameManager instance for testing."""
    manager = GameManager()
    try:
        yield manager
    finally:
        # Ensure proper cleanup
        await manager.cleanup()
        # Give a moment for cleanup to complete
        await asyncio.sleep(0.01)


@pytest.fixture
async def ws_manager():
    """Create a WebSocketManager instance for testing."""
    manager = WebSocketManager()
    try:
        yield manager
    finally:
        # Ensure proper cleanup
        await manager.disconnect_all()
        # Give a moment for cleanup to complete
        await asyncio.sleep(0.01)


@pytest.fixture
def default_game_settings() -> GameSettings:
    """Create default game settings for testing."""
    return GameSettings(
        mcts_settings=MCTSSettings(
            c=0.158,
            min_simulations=100,  # Lower for faster tests
            max_simulations=100,
            use_rollout=True,
            seed=42
        ),
        allow_hints=True,
        allow_analysis=True
    )


@pytest.fixture
def pvp_game_request(default_game_settings) -> GameCreateRequest:
    """Create a PvP game creation request."""
    return GameCreateRequest(
        player1_type=PlayerType.HUMAN,
        player2_type=PlayerType.HUMAN,
        player1_name="Alice",
        player2_name="Bob",
        settings=default_game_settings
    )


@pytest.fixture
def pvm_game_request(default_game_settings) -> GameCreateRequest:
    """Create a PvM game creation request."""
    return GameCreateRequest(
        player1_type=PlayerType.HUMAN,
        player2_type=PlayerType.MACHINE,
        player1_name="Human",
        player2_name="AI",
        settings=default_game_settings
    )


@pytest.fixture
def mvm_game_request(default_game_settings) -> GameCreateRequest:
    """Create a MvM game creation request."""
    return GameCreateRequest(
        player1_type=PlayerType.MACHINE,
        player2_type=PlayerType.MACHINE,
        player1_name="AI-1",
        player2_name="AI-2",
        settings=default_game_settings
    )


@pytest.fixture
def valid_moves():
    """Common valid move actions."""
    return [
        "*(4,1)",  # Move to position
        "*(3,0)",  # Move to position
        "*(5,0)",  # Move to position
        "H(4,0)",  # Horizontal wall
        "V(4,0)",  # Vertical wall
    ]


@pytest.fixture
def invalid_moves():
    """Common invalid move actions."""
    return [
        "*(9,9)",    # Out of bounds
        "*(4,8)",    # Too far
        "X(4,4)",    # Invalid action type
        "invalid",   # Invalid format
        "",          # Empty
    ]


# MCTS mocking will be done per-test as needed to avoid conflicts