"""
API-specific test fixtures and configuration.
"""

import os
from typing import AsyncGenerator, Callable, Dict, Generator, List, Tuple
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from backend.api.game_manager import GameManager
from backend.api.models import (
    GameCreateRequest,
    GameSettings,
    MCTSSettings,
    Player,
    PlayerType,
)
from backend.api.server import app
from backend.api.websocket_manager import WebSocketManager
from tests.mock_helpers import MockCorridorsMCTS

# Remove session-scoped event loop - let pytest-asyncio handle it automatically


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    # Ensure test environment is set
    os.environ["PYTEST_CURRENT_TEST"] = "1"

    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(base_url="http://test") as client:
        yield client


@pytest.fixture
async def game_manager() -> AsyncGenerator[GameManager, None]:
    """Create a GameManager instance for testing."""
    manager = GameManager()
    yield manager
    # Simplified cleanup - let the manager handle its own state


@pytest.fixture
async def ws_manager() -> AsyncGenerator[WebSocketManager, None]:
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
            seed=42,
        ),
        allow_hints=True,
        allow_analysis=True,
    )


@pytest.fixture
def pvp_game_request(default_game_settings: GameSettings) -> GameCreateRequest:
    """Create a PvP game creation request."""
    return GameCreateRequest(
        player1_type=PlayerType.HUMAN,
        player2_type=PlayerType.HUMAN,
        player1_name="Alice",
        player2_name="Bob",
        settings=default_game_settings,
    )


@pytest.fixture
def pvm_game_request(default_game_settings: GameSettings) -> GameCreateRequest:
    """Create a PvM game creation request."""
    return GameCreateRequest(
        player1_type=PlayerType.HUMAN,
        player2_type=PlayerType.MACHINE,
        player1_name="Human",
        player2_name="AI",
        settings=default_game_settings,
    )


@pytest.fixture
def mvm_game_request(default_game_settings: GameSettings) -> GameCreateRequest:
    """Create a MvM game creation request."""
    return GameCreateRequest(
        player1_type=PlayerType.MACHINE,
        player2_type=PlayerType.MACHINE,
        player1_name="AI-1",
        player2_name="AI-2",
        settings=default_game_settings,
    )


@pytest.fixture
def valid_moves() -> list[str]:
    """Common valid move actions."""
    return [
        "*(4,1)",  # Move to position
        "*(3,0)",  # Move to position
        "*(5,0)",  # Move to position
        "H(4,0)",  # Horizontal wall
        "V(4,0)",  # Vertical wall
    ]


@pytest.fixture
def invalid_moves() -> list[str]:
    """Common invalid move actions."""
    return [
        "*(9,9)",  # Out of bounds
        "*(4,8)",  # Too far
        "X(4,4)",  # Invalid action type
        "invalid",  # Invalid format
        "",  # Empty
    ]


@pytest.fixture(autouse=True)
def mock_mcts(monkeypatch: MonkeyPatch) -> Callable[[], MockCorridorsMCTS]:
    """Mock all MCTS operations to prevent expensive computations during tests."""
    # Create a mock with fixed return values
    mock_sorted_actions: List[Tuple[int, float, str]] = [
        (100, 0.8, "*(4,1)"),
        (80, 0.6, "*(3,0)"),
        (60, 0.4, "*(5,0)"),
        (50, 0.3, "H(4,0)"),
        (40, 0.2, "V(4,0)"),
        (30, 0.1, "H(3,1)"),
    ]

    # Mock the MCTS constructor that returns a consistent mock
    def mock_mcts_constructor(*args: object, **kwargs: object) -> MockCorridorsMCTS:
        # Set up action stats
        action_stats: Dict[str, Dict[str, float]] = {
            "*(4,1)": {"visits": 100, "value": 0.8},
            "*(3,0)": {"visits": 80, "value": 0.6},
            "*(5,0)": {"visits": 60, "value": 0.4},
            "H(4,0)": {"visits": 50, "value": 0.3},
            "V(4,0)": {"visits": 40, "value": 0.2},
            "H(3,1)": {"visits": 30, "value": 0.1},
        }

        return MockCorridorsMCTS(
            sorted_actions=mock_sorted_actions,
            best_action="*(4,1)",
            best_move="*(4,1)",
            board_display="Mock board display",
            evaluation=None,
            action_stats=action_stats,
        )

    # Apply mocking to all relevant modules - mock AsyncCorridorsMCTS in corridors.async_mcts
    monkeypatch.setattr(
        "corridors.async_mcts.AsyncCorridorsMCTS", mock_mcts_constructor
    )
    monkeypatch.setattr("corridors.AsyncCorridorsMCTS", mock_mcts_constructor)

    return mock_mcts_constructor
