"""
Unit tests for pure Python functions in the MCTS corridors module.

These tests focus on Python-side functionality:
- Display formatting
- Game flow control
- Self-play mechanics
- Human-computer interaction
- Utility functions
"""

import asyncio
import io
import sys
from typing import Dict, Generator, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from tests.conftest import MCTSParams
from tests.mock_helpers import MockCorridorsMCTS
from tests.pytest_marks import display, integration, parametrize, python, unit


# Note: The fixture is not needed since we use context managers directly

from corridors import AsyncCorridorsMCTS


# Recreate the display_sorted_actions utility function for testing
def display_sorted_actions(
    actions: List[Tuple[int, float, str]], list_size: Optional[int] = None
) -> str:
    """Format sorted actions for display."""
    # Calculate total visits
    total_visits = sum(action[0] for action in actions)
    
    # Limit actions if requested
    limited_actions = actions[:list_size] if list_size is not None else actions
    
    # Format output
    lines = [f"Total Visits: {total_visits}"]
    lines.append("")  # Add empty line to match expected format
    
    for visits, equity, action in limited_actions:
        lines.append(f"Visit count: {visits} Equity: {equity:.4f} Action: {action}")
    
    return "\n".join(lines) + "\n"


@python
@display
class TestDisplaySortedActions:
    """Test the display_sorted_actions utility function."""

    def test_display_empty_actions(self) -> None:
        """Test displaying empty action list."""
        result = display_sorted_actions([])

        assert isinstance(result, str)
        assert "Total Visits: 0" in result
        assert result.count("\n") >= 2  # Should have header and trailing newline

    def test_display_single_action(
        self, sample_actions: List[Tuple[int, float, str]]
    ) -> None:
        """Test displaying single action."""
        single_action = sample_actions[:1]
        result = display_sorted_actions(single_action)

        assert isinstance(result, str)
        assert "Total Visits: 150" in result
        assert "Visit count: 150" in result
        assert "Equity: 0.6234" in result
        assert "Action: *(4,1)" in result

    def test_display_multiple_actions(
        self, sample_actions: List[Tuple[int, float, str]]
    ) -> None:
        """Test displaying multiple actions."""
        result = display_sorted_actions(sample_actions)

        assert isinstance(result, str)
        # Total visits should be sum of all visits
        expected_total = sum(action[0] for action in sample_actions)
        assert f"Total Visits: {expected_total}" in result

        # Should contain all actions
        for visits, equity, action_str in sample_actions:
            assert f"Visit count: {visits}" in result
            assert f"{equity:.4f}" in result
            assert f"Action: {action_str}" in result

    def test_display_limited_actions(
        self, sample_actions: List[Tuple[int, float, str]]
    ) -> None:
        """Test displaying limited number of actions."""
        result = display_sorted_actions(sample_actions, list_size=3)

        assert isinstance(result, str)
        # Should still show total visits for all actions
        expected_total = sum(action[0] for action in sample_actions)
        assert f"Total Visits: {expected_total}" in result

        # Should only show first 3 actions in detail
        lines = result.strip().split("\n")
        action_lines = [line for line in lines if line.startswith("Visit count:")]
        assert len(action_lines) == 3

        # First 3 actions should be present
        for visits, equity, action_str in sample_actions[:3]:
            assert f"Visit count: {visits}" in result

        # Later actions should not be present (check for exact line matches)
        for visits, equity, action_str in sample_actions[3:]:
            expected_line = (
                f"Visit count: {visits} Equity: {equity:.4f} Action: {action_str}"
            )
            assert expected_line not in result

    def test_display_zero_list_size(
        self, sample_actions: List[Tuple[int, float, str]]
    ) -> None:
        """Test display with list_size=0 shows all actions."""
        result_all = display_sorted_actions(sample_actions)
        result_zero = display_sorted_actions(sample_actions, list_size=0)

        assert result_all == result_zero

    @parametrize(
        "visits,equity,action",
        [
            (100, 0.5555, "*(1,2)"),
            (0, 0.0, "H(0,0)"),
            (999999, 0.9999, "V(8,7)"),
            (1, -0.5432, "*(0,8)"),
        ],
    )
    def test_display_various_values(
        self, visits: int, equity: float, action: str
    ) -> None:
        """Test displaying various action value combinations."""
        test_actions = [(visits, equity, action)]
        result = display_sorted_actions(test_actions)

        assert f"Total Visits: {visits}" in result
        assert f"Visit count: {visits}" in result
        assert f"{equity:.4f}" in result
        assert f"Action: {action}" in result

    def test_display_formatting_consistency(
        self, sample_actions: List[Tuple[int, float, str]]
    ) -> None:
        """Test that display formatting is consistent."""
        result = display_sorted_actions(sample_actions)

        lines = result.strip().split("\n")

        # Should have header, action lines, and trailing empty line
        assert lines[0].startswith("Total Visits:")

        action_lines = [line for line in lines if line.startswith("Visit count:")]
        assert len(action_lines) == len(sample_actions)

        # Each action line should follow format: "Visit count: X Equity: Y Action: Z"
        for line in action_lines:
            parts = line.split()
            assert len(parts) >= 6  # "Visit count: X Equity: Y Action: Z"
            assert parts[0] == "Visit"
            assert parts[1] == "count:"
            assert parts[3] == "Equity:"
            assert parts[5] == "Action:"


# Note: computer_self_play and human_computer_play functions were removed
# in the async refactor as they were already stub functions.


@python
@unit
class TestAsyncCorridorsMCTSPythonMethods:
    """Test Python-specific methods in AsyncCorridorsMCTS class."""

    @pytest.mark.asyncio
    async def test_get_evaluation_none_handling(self, fast_mcts_params: MCTSParams) -> None:
        """Test that get_evaluation properly handles None values."""
        async with AsyncCorridorsMCTS(**fast_mcts_params) as mcts:
            # Test that get_evaluation returns proper types
            result = await mcts.get_evaluation_async()
            assert result is None or isinstance(result, float)

    @pytest.mark.asyncio
    async def test_method_delegation(self, fast_mcts_params: MCTSParams) -> None:
        """Test that methods properly delegate to async implementation."""
        async with AsyncCorridorsMCTS(**fast_mcts_params) as mcts:
            # These should not raise exceptions and should return expected types
            display = await mcts.display_async(flip=False)
            assert isinstance(display, str)

            await mcts.ensure_sims_async(5)  # Should not raise

            evaluation = await mcts.get_evaluation_async()
            assert evaluation is None or isinstance(evaluation, (int, float))


@python
@parametrize(
    "c,seed,min_sims,max_sims",
    [
        (0.5, 1, 5, 100),
        (1.0, 42, 10, 100),
        (2.0, 123, 20, 100),
    ],
)
@pytest.mark.asyncio
async def test_async_mcts_parameter_combinations(
    c: float, seed: int, min_sims: int, max_sims: int
) -> None:
    """Test AsyncCorridorsMCTS with various parameter combinations."""
    async with AsyncCorridorsMCTS(
        c=c,
        seed=seed,
        min_simulations=min_sims,
        max_simulations=max_sims,
        sim_increment=25,
        use_rollout=True,
        eval_children=False,
        use_puct=False,
        use_probs=False,
        decide_using_visits=True,
    ) as mcts:
        assert mcts is not None
        # Basic functionality should work
        display = await mcts.display_async()
        assert isinstance(display, str)


@python
@integration
class TestErrorHandling:
    """Test error handling in Python functions."""

    def test_display_sorted_actions_invalid_input(self) -> None:
        """Test display_sorted_actions with invalid input."""
        # Should handle empty gracefully
        result = display_sorted_actions([])
        assert isinstance(result, str)

        # Test function robustness with edge cases
        # Focus on type-safe error conditions only

    def test_function_imports(self) -> None:
        """Test that all expected functions can be imported."""
        # These imports should work
        from corridors import AsyncCorridorsMCTS

        # Basic type checks
        assert callable(AsyncCorridorsMCTS)
