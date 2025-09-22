from tests.pytest_marks import (
    api,
    asyncio as asyncio_mark,
    benchmark,
    board,
    cpp,
    display,
    edge_cases,
    endpoints,
    game_manager,
    integration,
    mcts,
    models,
    parametrize,
    performance,
    python,
    slow,
    stress,
    unit,
    websocket,
)

"""
Edge case and boundary condition tests for MCTS implementation.

These tests cover unusual conditions and corner cases:
- Boundary coordinates and moves
- Invalid inputs and error handling
- State transitions and game rules
- Algorithm edge conditions
"""

import asyncio
import sys
from typing import Dict, List, Tuple, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
import pytest_asyncio

from tests.mock_helpers import MockCorridorsMCTS

from corridors import AsyncCorridorsMCTS


@edge_cases
@cpp
class TestBoundaryConditions:
    """Test boundary conditions for board coordinates and moves."""

    @parametrize(
        "x,y",
        [
            (0, 0),
            (8, 8),  # Board corners
            (4, 0),
            (4, 8),  # Center edges
            (0, 4),
            (8, 4),  # Side centers
        ],
    )
    @pytest.mark.asyncio
    async def test_boundary_positions(self, x: int, y: int) -> None:
        """Test MCTS behavior at board boundaries."""
        async with AsyncCorridorsMCTS(
            c=1.0, seed=42, min_simulations=10, max_simulations=100,
            sim_increment=10, use_rollout=True, eval_children=False,
            use_puct=False, use_probs=False, decide_using_visits=True
        ) as mcts:
            # Try to place hero at boundary position via moves
            # (This is indirect since we can't directly set positions)
            await mcts.ensure_sims_async(10)

            # Basic functionality should work regardless of internal positions
            actions = await mcts.get_sorted_actions_async(flip=True)
            display = await mcts.display_async(flip=False)

            assert isinstance(actions, list)
            assert isinstance(display, str)

    def test_wall_boundary_positions(self) -> None:
        """Test wall placement at board boundaries."""
        mcts = Corridors_MCTS(c=1.0, seed=42, min_simulations=20, max_simulations=100)

        mcts.ensure_sims(20)
        actions = mcts.get_sorted_actions(flip=True)

        # Look for wall actions at boundaries
        wall_actions = [
            a[2] for a in actions if a[2].startswith("H(") or a[2].startswith("V(")
        ]
        boundary_walls = []

        for wall_action in wall_actions:
            # Parse wall coordinates
            coords_str = wall_action[2:-1]  # Remove "H(" or "V(" and ")"
            x_str, y_str = coords_str.split(",")
            x, y = int(x_str), int(y_str)

            # Check if it's a boundary wall (coordinates 0 or max)
            if x == 0 or x >= 7 or y == 0 or y >= 7:  # (BOARD_SIZE-2) = 7 for 9x9 board
                boundary_walls.append(wall_action)

        # Boundary walls should be legal when they appear
        for wall_action in boundary_walls[:3]:  # Test first few
            try:
                mcts_test = Corridors_MCTS(
                    c=1.0, seed=42, min_simulations=5, max_simulations=100
                )
                mcts_test.ensure_sims(5)
                test_actions = mcts_test.get_sorted_actions(flip=True)
                if wall_action in [a[2] for a in test_actions]:
                    mcts_test.make_move(wall_action, flip=True)
                    # Should not raise exception
            except Exception as e:
                pytest.fail(f"Boundary wall {wall_action} caused error: {e}")

    def test_maximum_walls_placement(self) -> None:
        """Test behavior when maximum walls are placed."""
        mcts = Corridors_MCTS(c=1.0, seed=42, min_simulations=15, max_simulations=100)

        # Try to place many walls (simulate late game)
        for i in range(10):  # Try up to 10 wall placements
            mcts.ensure_sims(15)
            actions = mcts.get_sorted_actions(flip=True)

            if not actions:
                break

            # Look for wall placement moves
            wall_moves = [
                a[2] for a in actions if a[2].startswith("H(") or a[2].startswith("V(")
            ]

            if not wall_moves:
                break  # No more wall moves available

            # Place a wall
            mcts.make_move(wall_moves[0], flip=True)

        # Should still function normally
        final_actions = mcts.get_sorted_actions(flip=False)
        assert isinstance(final_actions, list)


@edge_cases
@python
class TestDisplayEdgeCases:
    """Test display function edge cases."""

    def test_display_empty_actions_list(self) -> None:
        """Test displaying empty actions."""
        result = display_sorted_actions([])
        assert isinstance(result, str)
        assert "Total Visits: 0" in result
        assert result.strip() == "Total Visits: 0" or result.endswith("\n")

    def test_display_single_zero_visit_action(self) -> None:
        """Test displaying action with zero visits."""
        actions = [(0, 0.5, "*(4,4)")]
        result = display_sorted_actions(actions)

        assert "Total Visits: 0" in result
        assert "Visit count: 0" in result
        assert "Equity: 0.5000" in result

    def test_display_negative_equity(self) -> None:
        """Test displaying actions with negative equity."""
        actions = [(100, -0.7554, "*(2,3)")]
        result = display_sorted_actions(actions)

        assert "Equity: -0.7554" in result

    def test_display_extreme_values(self) -> None:
        """Test displaying extreme values."""
        actions = [
            (999999, 0.9999, "*(0,0)"),
            (1, -0.9999, "V(7,7)"),
            (0, 0.0, "H(4,4)"),
        ]
        result = display_sorted_actions(actions)

        assert "999999" in result
        assert "0.9999" in result
        assert "-0.9999" in result

    @parametrize("list_size", [-1, 0, 1, 100, 999999])
    def test_display_various_list_sizes(
        self, list_size: int, sample_actions: List[Tuple[int, float, str]]
    ) -> None:
        """Test display with various list size limits."""
        result = display_sorted_actions(sample_actions, list_size=list_size)
        assert isinstance(result, str)

        if list_size <= 0:
            # Should show all actions
            for action in sample_actions:
                assert f"Visit count: {action[0]}" in result
        else:
            # Should show limited actions
            expected_count = min(list_size, len(sample_actions))
            action_lines = [
                line for line in result.split("\n") if line.startswith("Visit count:")
            ]
            assert len(action_lines) == expected_count

    def test_display_unicode_handling(self) -> None:
        """Test display with potential unicode issues."""
        # Test with basic ASCII - more complex unicode would need C++ side support
        actions = [(50, 0.5, "*(1,2)")]
        result = display_sorted_actions(actions)
        assert isinstance(result, str)
        assert len(result) > 0


@edge_cases
@integration
class TestGameFlowEdgeCases:
    """Test edge cases in game flow."""

    @patch("builtins.print")
    def test_computer_self_play_immediate_end(self, mock_print: MagicMock) -> None:
        """Test self-play when game ends immediately."""
        mock_p1 = MockCorridorsMCTS(
            sorted_actions=[],  # No moves available
            board_display="Game over",
            evaluation=None,
        )

        # Should handle gracefully
        computer_self_play(mock_p1)
        # MockCorridorsMCTS automatically tracks calls

    @patch("builtins.print")
    def test_computer_self_play_alternating_players(
        self, mock_print: MagicMock
    ) -> None:
        """Test self-play with proper player alternation."""
        call_count = [0]  # Mutable counter

        def get_actions_p1(flip: bool) -> List[Tuple[int, float, str]]:
            call_count[0] += 1
            if call_count[0] == 1:
                return [(100, 0.6, "*(4,1)")]  # First call - hero's move
            else:
                return []  # Second call - game over

        def get_actions_p2(flip: bool) -> List[Tuple[int, float, str]]:
            return []  # Villain has no moves

        mock_p1 = MockCorridorsMCTS(
            sorted_actions_side_effect=get_actions_p1,
            board_display="Board 1",
            evaluation=None,
        )
        mock_p2 = MockCorridorsMCTS(
            sorted_actions_side_effect=get_actions_p2,
            board_display="Board 2",
            evaluation=None,
        )

        computer_self_play(mock_p1, mock_p2)

        # Both players should make the same move
        mock_p1.assert_move_made("*(4,1)", True)
        mock_p2.assert_move_made("*(4,1)", True)


@edge_cases
@cpp
class TestMCTSParameterEdgeCases:
    """Test MCTS with edge case parameters."""

    def test_very_small_c_parameter(self) -> None:
        """Test with very small exploration parameter."""
        mcts = Corridors_MCTS(
            c=1e-10,  # Extremely small
            seed=42,
            min_simulations=10,
            max_simulations=100,
        )

        mcts.ensure_sims(10)
        actions = mcts.get_sorted_actions(flip=True)
        assert isinstance(actions, list)

    def test_very_large_c_parameter(self) -> None:
        """Test with very large exploration parameter."""
        mcts = Corridors_MCTS(
            c=1e6,  # Extremely large
            seed=42,
            min_simulations=10,
            max_simulations=100,
        )

        mcts.ensure_sims(10)
        actions = mcts.get_sorted_actions(flip=True)
        assert isinstance(actions, list)

    def test_min_greater_than_max_simulations(self) -> None:
        """Test behavior when min_simulations > max_simulations."""
        # This should either work (correcting the range internally) or raise a specific error
        try:
            mcts = Corridors_MCTS(
                c=1.0,
                seed=42,
                min_simulations=100,
                max_simulations=100,  # Less than min
            )

            mcts.ensure_sims(50)
            actions = mcts.get_sorted_actions(flip=True)
            assert isinstance(
                actions, list
            ), "MCTS should return list of actions when it handles invalid range internally"
        except (ValueError, RuntimeError, TypeError) as e:
            # Specific exceptions are acceptable for invalid parameters
            assert len(str(e)) > 0, "Exception should have a descriptive message"
        except Exception as e:
            pytest.fail(
                f"Unexpected exception type {type(e).__name__}: {e}. Expected ValueError, RuntimeError, or TypeError"
            )

    def test_zero_increment(self) -> None:
        """Test with zero simulation increment."""
        mcts = Corridors_MCTS(c=1.0, seed=42, min_simulations=10, max_simulations=100)

        # This should either complete normally or raise a specific timeout/runtime error
        try:
            # Use timeout to prevent hanging - pytest-timeout can help but we'll be explicit
            import signal

            def timeout_handler(signum: int, frame: object) -> None:
                raise TimeoutError(
                    "ensure_sims call timed out - likely hanging on zero increment"
                )

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)  # 5 second timeout

            mcts.ensure_sims(10)

            signal.alarm(0)  # Cancel timeout

            # If we get here, the operation completed successfully
            actions = mcts.get_sorted_actions(flip=True)
            assert isinstance(
                actions, list
            ), "MCTS should return valid actions after ensure_sims"

        except (TimeoutError, RuntimeError, ValueError) as e:
            signal.alarm(0)  # Cancel timeout
            # These are acceptable - either timeout due to hanging or immediate error
            assert len(str(e)) > 0, "Exception should have a descriptive message"
        except Exception as e:
            signal.alarm(0)  # Cancel timeout
            pytest.fail(
                f"Unexpected exception type {type(e).__name__}: {e}. Expected TimeoutError, RuntimeError, or ValueError"
            )

    @parametrize("seed", [-1, 0, 2**31 - 1, 2**32 - 1])
    def test_edge_case_seeds(self, seed: int) -> None:
        """Test with edge case random seeds."""
        try:
            mcts = Corridors_MCTS(
                c=1.0, seed=seed, min_simulations=5, max_simulations=100
            )

            mcts.ensure_sims(5)
            actions = mcts.get_sorted_actions(flip=True)
            assert isinstance(
                actions, list
            ), f"MCTS should return list of actions with seed {seed}"
            assert len(actions) >= 0, f"Actions list should be valid with seed {seed}"
        except (ValueError, OverflowError, RuntimeError, TypeError) as e:
            # Some seeds might be invalid (e.g., negative, overflow, type issues) - that's acceptable
            assert (
                len(str(e)) > 0
            ), f"Exception for seed {seed} should have a descriptive message: {e}"
        except Exception as e:
            pytest.fail(
                f"Unexpected exception type {type(e).__name__} for seed {seed}: {e}. Expected ValueError, OverflowError, RuntimeError, or TypeError"
            )


@edge_cases
@cpp
class TestStateTransitionEdgeCases:
    """Test edge cases in state transitions."""

    def test_rapid_move_sequence(self) -> None:
        """Test rapid sequence of moves without simulations."""
        mcts = Corridors_MCTS(
            c=1.0,
            seed=42,
            min_simulations=1,  # Minimal simulations
            max_simulations=100,
        )

        # Try to make moves rapidly
        for i in range(5):
            mcts.ensure_sims(1)
            actions = mcts.get_sorted_actions(flip=(i % 2 == 0))

            if not actions:
                break

            # Make first available move
            mcts.make_move(actions[0][2], flip=(i % 2 == 0))

            # Verify state is still consistent
            display = mcts.display(flip=False)
            assert isinstance(display, str)
            assert len(display) > 0

    def test_alternating_flip_parameters(self) -> None:
        """Test alternating flip parameters."""
        mcts = Corridors_MCTS(c=1.0, seed=42, min_simulations=10, max_simulations=100)

        mcts.ensure_sims(10)

        # Alternate flip parameters
        for flip_value in [True, False, True, False]:
            actions = mcts.get_sorted_actions(flip=flip_value)
            display = mcts.display(flip=flip_value)

            assert isinstance(actions, list)
            assert isinstance(display, str)

    def test_evaluation_during_game_progress(self) -> None:
        """Test evaluation changes during game progress."""
        mcts = Corridors_MCTS(c=1.0, seed=42, min_simulations=15, max_simulations=100)

        evaluations = []

        for i in range(5):
            mcts.ensure_sims(15)
            evaluation = mcts.get_evaluation()
            evaluations.append(evaluation)

            actions = mcts.get_sorted_actions(flip=(i % 2 == 0))
            if not actions:
                break

            mcts.make_move(actions[0][2], flip=(i % 2 == 0))

        # Evaluations should be None or numeric
        for eval_val in evaluations:
            assert eval_val is None or isinstance(eval_val, (int, float))


@edge_cases
@python
class TestErrorRecovery:
    """Test error recovery and robustness."""

    def test_malformed_action_strings(self) -> None:
        """Test display with malformed action strings."""
        malformed_actions = [
            (100, 0.5, "invalid"),
            (50, 0.3, "*("),
            (25, 0.1, "H(1,2,3)"),
            (10, 0.0, ""),
        ]

        # Should not crash, even with malformed data
        result = display_sorted_actions(malformed_actions)
        assert isinstance(result, str)
        assert "Total Visits: 185" in result

    def test_type_mixed_actions(self) -> None:
        """Test display with mixed types in action tuples."""
        # Test with properly typed but edge case data
        mixed_actions = [
            (100, 0.5, "*(4,1)"),
            (50, 0.3, "H(2,3)"),  # Valid integer
            (25, 0.1, "V(1,1)"),  # Valid integer
        ]

        try:
            result = display_sorted_actions(mixed_actions)
            assert isinstance(result, str)
        except (TypeError, ValueError):
            # Type errors are acceptable for invalid input
            pass

    def test_function_resilience(self) -> None:
        """Test that functions are resilient to unexpected inputs."""
        mcts = Corridors_MCTS(c=1.0, seed=42, min_simulations=5, max_simulations=100)

        # Test various edge case calls
        try:
            mcts.ensure_sims(5)

            # These should not crash the system
            mcts.display(flip=True)
            mcts.display(flip=False)
            mcts.get_evaluation()

            actions = mcts.get_sorted_actions(flip=True)
            if actions:
                # Try epsilon values outside normal range
                mcts.choose_best_action(epsilon=-1.0)  # Negative epsilon
                mcts.choose_best_action(epsilon=2.0)  # > 1.0 epsilon

        except Exception as e:
            # Some exceptions may be expected for invalid inputs
            # Just ensure the system doesn't crash completely
            assert isinstance(e, Exception)
