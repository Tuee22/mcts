"""
Pytest configuration and fixtures for MCTS testing.
"""

# Approach that completely avoids assignment issues by setting up module constants
import sys
from math import sqrt
from typing import Dict, List, Optional, Tuple, TypedDict

import numpy as np
import pytest

# Always use the corridors module - stubs should handle the typing
from corridors.corridors_mcts import Corridors_MCTS, display_sorted_actions


class MCTSParams(TypedDict):
    """Type definition for MCTS parameters."""

    c: float
    seed: int
    min_simulations: int
    max_simulations: int
    use_rollout: bool
    eval_children: bool
    use_puct: bool
    use_probs: bool
    decide_using_visits: bool


class BoardState(TypedDict):
    """Type definition for board state."""

    flip: bool
    hero_x: int
    hero_y: int
    villain_x: int
    villain_y: int
    hero_walls_remaining: int
    villain_walls_remaining: int
    wall_middles: List[bool]
    horizontal_walls: List[bool]
    vertical_walls: List[bool]


@pytest.fixture
def basic_mcts_params() -> MCTSParams:
    """Basic MCTS parameters for testing."""
    return {
        "c": sqrt(2),
        "seed": 42,
        "min_simulations": 100,
        "max_simulations": 1000,
        "use_rollout": True,
        "eval_children": False,
        "use_puct": False,
        "use_probs": False,
        "decide_using_visits": True,
    }


@pytest.fixture
def fast_mcts_params() -> MCTSParams:
    """Fast MCTS parameters for quick testing."""
    return {
        "c": sqrt(0.5),
        "seed": 123,
        "min_simulations": 10,
        "max_simulations": 50,
        "use_rollout": True,
        "eval_children": False,
        "use_puct": False,
        "use_probs": False,
        "decide_using_visits": True,
    }


@pytest.fixture
def puct_mcts_params() -> MCTSParams:
    """PUCT-style MCTS parameters."""
    return {
        "c": sqrt(0.025),
        "seed": 456,
        "min_simulations": 100,
        "max_simulations": 500,
        "use_rollout": False,
        "eval_children": True,
        "use_puct": True,
        "use_probs": True,
        "decide_using_visits": False,
    }


@pytest.fixture
def sample_board_state() -> BoardState:
    """Sample board state for testing C++ board functions."""
    return {
        "flip": False,
        "hero_x": 4,
        "hero_y": 0,
        "villain_x": 4,
        "villain_y": 8,
        "hero_walls_remaining": 10,
        "villain_walls_remaining": 10,
        "wall_middles": [False] * 64,  # (9-1)*(9-1) = 64
        "horizontal_walls": [False] * 72,  # (9-1)*9 = 72
        "vertical_walls": [False] * 72,  # (9-1)*9 = 72
    }


@pytest.fixture
def blocked_board_state() -> BoardState:
    """Board state with some walls placed."""
    state: BoardState = {
        "flip": False,
        "hero_x": 4,
        "hero_y": 1,
        "villain_x": 4,
        "villain_y": 7,
        "hero_walls_remaining": 8,
        "villain_walls_remaining": 9,
        "wall_middles": [False] * 64,
        "horizontal_walls": [False] * 72,
        "vertical_walls": [False] * 72,
    }
    # Place some walls
    state["wall_middles"][27] = True  # Middle intersection
    state["horizontal_walls"][30] = True
    state["horizontal_walls"][31] = True
    return state


@pytest.fixture
def near_terminal_state() -> BoardState:
    """Board state near game end."""
    return {
        "flip": False,
        "hero_x": 4,
        "hero_y": 7,  # Close to winning
        "villain_x": 4,
        "villain_y": 1,  # Close to winning
        "hero_walls_remaining": 2,
        "villain_walls_remaining": 1,
        "wall_middles": [False] * 64,
        "horizontal_walls": [False] * 72,
        "vertical_walls": [False] * 72,
    }


@pytest.fixture
def sample_actions() -> List[Tuple[int, float, str]]:
    """Sample sorted actions for testing display functions."""
    return [
        (150, 0.6234, "*(4,1)"),
        (120, 0.5876, "*(5,0)"),
        (100, 0.5234, "*(3,0)"),
        (80, 0.4567, "H(3,0)"),
        (60, 0.3421, "V(4,0)"),
        (40, 0.2876, "*(4,0)"),
        (20, 0.1543, "H(5,0)"),
        (10, 0.0987, "V(3,1)"),
    ]


class MCTSTestHelper:
    """Helper class for MCTS testing utilities."""

    @staticmethod
    def create_mcts_instance(params: MCTSParams) -> "Corridors_MCTS":
        """Create MCTS instance with given parameters."""
        if not CORRIDORS_AVAILABLE:
            raise ImportError("Corridors C++ module not available")
        return Corridors_MCTS(**params)

    @staticmethod
    def validate_action_format(action: str) -> bool:
        """Validate action string format."""
        if action.startswith("*(") and action.endswith(")"):
            # Positional move: *(x,y)
            coords = action[2:-1].split(",")
            return len(coords) == 2 and all(c.isdigit() for c in coords)
        elif (action.startswith("H(") or action.startswith("V(")) and action.endswith(
            ")"
        ):
            # Wall placement: H(x,y) or V(x,y)
            coords = action[2:-1].split(",")
            return len(coords) == 2 and all(c.isdigit() for c in coords)
        return False

    @staticmethod
    def validate_sorted_actions(actions: List[Tuple[int, float, str]]) -> bool:
        """Validate sorted actions structure and ordering."""
        if not actions:
            return True

        # Check structure
        for action in actions:
            if len(action) != 3:
                return False
            visits, equity, action_str = action
            if not isinstance(visits, int) or visits < 0:
                return False
            if not isinstance(equity, (int, float)):
                return False
            if not isinstance(action_str, str):
                return False
            if not MCTSTestHelper.validate_action_format(action_str):
                return False

        # Check ordering (should be sorted by equity, descending)
        # MCTS sorts by best actions first, but when equities are equal, order may vary
        equities = [a[1] for a in actions]
        # Check that equities are in non-increasing order (allowing for equal values)
        for i in range(len(equities) - 1):
            if equities[i] < equities[i + 1]:
                return False
        return True


@pytest.fixture
def mcts_helper() -> type[MCTSTestHelper]:
    """Provide MCTS testing helper."""
    return MCTSTestHelper
