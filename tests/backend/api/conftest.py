"""
API-specific test fixtures and configuration.
"""
import pytest
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import MagicMock

from backend.api.server import app
from backend.api.game_manager import GameManager
from backend.api.websocket_manager import WebSocketManager
from backend.api.models import (
    GameSettings, MCTSSettings, PlayerType,
    GameCreateRequest, Player
)


# Remove session-scoped event loop - let pytest-asyncio handle it automatically


@pytest.fixture
def test_client() -> Generator:
    """Create a test client for the FastAPI app."""
    # Ensure test environment is set
    import os
    os.environ['PYTEST_CURRENT_TEST'] = '1'
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def game_manager():
    """Create a GameManager instance for testing."""
    manager = GameManager()
    yield manager
    # Simplified cleanup - let the manager handle its own state


@pytest.fixture
async def ws_manager():
    """Create a WebSocketManager instance for testing."""
    manager = WebSocketManager()
    yield manager
    # Simplified cleanup - let the manager handle its own state


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


@pytest.fixture(autouse=True)
def mock_mcts(monkeypatch):
    """Mock all MCTS operations to prevent expensive computations during tests."""
    # Create a mock with fixed return values
    mock_sorted_actions = [
        (100, 0.8, "*(4,1)"), (80, 0.6, "*(3,0)"), (60, 0.4, "*(5,0)"),
        (50, 0.3, "H(4,0)"), (40, 0.2, "V(4,0)"), (30, 0.1, "H(3,1)")
    ]
    
    # Mock the MCTS constructor that returns a consistent mock
    def mock_mcts_constructor(*_args, **_kwargs):
        mock_mcts = MagicMock()
        # Set up the mock with consistent return values
        mock_mcts.get_sorted_actions = MagicMock(return_value=mock_sorted_actions)
        mock_mcts.choose_best_action = MagicMock(return_value="*(4,1)")
        mock_mcts.ensure_sims = MagicMock(return_value=None)
        mock_mcts.get_best_move = MagicMock(return_value="*(4,1)")
        mock_mcts.get_action_stats = MagicMock(return_value={
            "*(4,1)": {"visits": 100, "value": 0.8},
            "*(3,0)": {"visits": 80, "value": 0.6},
            "*(5,0)": {"visits": 60, "value": 0.4},
            "H(4,0)": {"visits": 50, "value": 0.3},
            "V(4,0)": {"visits": 40, "value": 0.2},
            "H(3,1)": {"visits": 30, "value": 0.1}
        })
        mock_mcts.display = MagicMock(return_value="Mock board display")
        mock_mcts.get_evaluation = MagicMock(return_value=None)
        mock_mcts.make_move = MagicMock(return_value=None)
        return mock_mcts
    
    # Apply mocking to all relevant modules
    monkeypatch.setattr('backend.api.game_manager.Corridors_MCTS', mock_mcts_constructor)
    monkeypatch.setattr('backend.python.corridors.corridors_mcts.Corridors_MCTS', mock_mcts_constructor)
    
    # Also mock any import attempts
    try:
        import backend.python.corridors.corridors_mcts
        monkeypatch.setattr(backend.python.corridors.corridors_mcts, 'Corridors_MCTS', mock_mcts_constructor)
    except ImportError:
        pass
    
    return mock_mcts_constructor