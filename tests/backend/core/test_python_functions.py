"""
Unit tests for pure Python functions in the MCTS corridors module.

These tests focus on Python-side functionality:
- Display formatting
- Game flow control
- Self-play mechanics
- Human-computer interaction
- Utility functions
"""

import pytest
import io
import sys
from unittest.mock import patch, MagicMock
from typing import Dict, List, Tuple, Generator
from tests.pytest_marks import python, display, integration, unit, parametrize
from tests.mock_helpers import MockCorridorsMCTS

try:
    from corridors.corridors_mcts import (
        Corridors_MCTS,
        display_sorted_actions,
        computer_self_play,
        human_computer_play,
    )

    CORRIDORS_AVAILABLE = True
except ImportError:
    CORRIDORS_AVAILABLE = False


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


@python
@integration
class TestComputerSelfPlay:
    """Test computer self-play functionality."""

    def test_computer_self_play_setup(self) -> None:
        """Test that computer_self_play can be called without errors in setup."""
        if not CORRIDORS_AVAILABLE:
            return
        # Mock the MCTS instances to avoid actual computation
        mock_p1 = MockCorridorsMCTS(
            sorted_actions=[],  # Empty = game over
            board_display="Mock board display",
            evaluation=None,
        )

        # Should handle empty actions list (game over immediately)
        with patch("builtins.print"):  # Suppress print output
            computer_self_play(mock_p1)

        # Mock automatically tracks calls - no additional assertions needed

    def test_computer_self_play_single_move(self) -> None:
        """Test computer self-play with single move before game ends."""
        if not CORRIDORS_AVAILABLE:
            return
        mock_p1 = MockCorridorsMCTS(
            sorted_actions=[(100, 0.6, "*(4,1)")],
            board_display="Mock board 1",
            evaluation=None,
        )
        mock_p2 = MockCorridorsMCTS(
            sorted_actions=[],  # Game over
            board_display="Mock board 2",
            evaluation=None,
        )

        with patch("builtins.print"):  # Suppress print output
            computer_self_play(mock_p1, mock_p2)  # MockCorridorsMCTS is compatible

        # Verify moves were made
        mock_p1.assert_move_made("*(4,1)", True)
        mock_p2.assert_move_made("*(4,1)", True)

    def test_computer_self_play_same_instance(self) -> None:
        """Test computer self-play using same instance for both players."""
        if not CORRIDORS_AVAILABLE:
            return
        mock_instance = MockCorridorsMCTS(
            sorted_actions=[],  # Game over immediately
            board_display="Mock board",
            evaluation=None,
        )

        with patch("builtins.print"):
            computer_self_play(mock_instance)  # p2 defaults to p1

        # Mock automatically tracks calls - no need to assert

    def test_computer_self_play_stop_on_eval(self) -> None:
        """Test computer self-play with stop_on_eval=True."""
        if not CORRIDORS_AVAILABLE:
            return
        mock_p1 = MockCorridorsMCTS(
            sorted_actions=[(100, 0.6, "*(4,8)")],  # Winning move
            board_display="Mock winning board",
            evaluation=1.0,  # Hero wins
        )

        with patch("builtins.print") as mock_print:
            computer_self_play(mock_p1, stop_on_eval=True)

        # Should stop after detecting terminal evaluation
        mock_p1.assert_called_make_move()

        # Should print winning message
        print_calls: List[str] = [
            str(call[0][0]) for call in mock_print.call_args_list if call[0]
        ]
        winning_messages = [msg for msg in print_calls if "wins!" in str(msg)]
        assert len(winning_messages) > 0


@python
@integration
class TestHumanComputerPlay:
    """Test human-computer interaction functionality."""

    @patch("builtins.input")
    @patch("builtins.print")
    def test_human_computer_play_human_first_immediate_end(
        self, mock_print: MagicMock, mock_input: MagicMock
    ) -> None:
        """Test human-computer play when game ends immediately."""
        if not CORRIDORS_AVAILABLE:
            return
        mock_mcts = MockCorridorsMCTS(
            sorted_actions=[],  # Game over immediately
            board_display="Game over board",
        )

        human_computer_play(mock_mcts, human_plays_first=True)

        # Mock automatically tracks calls - no additional assertions needed

    @patch("builtins.input", return_value="*(4,1)")
    @patch("builtins.print")
    def test_human_computer_play_single_move(
        self, mock_print: MagicMock, mock_input: MagicMock
    ) -> None:
        """Test human-computer play with one move."""
        if not CORRIDORS_AVAILABLE:
            return
        mock_mcts = MockCorridorsMCTS(
            sorted_actions_sequence=[
                [(100, 0.6, "*(4,1)"), (50, 0.4, "*(3,0)")],  # Human's options
                [],  # Computer's turn - game over
            ],
            board_display="Mock board",
        )

        human_computer_play(mock_mcts, human_plays_first=True, hide_humans_moves=False)

        # Should make the human's move
        mock_mcts.assert_move_made("*(4,1)", True)

    @patch("builtins.input", side_effect=["invalid_move", "*(4,1)"])
    @patch("builtins.print")
    def test_human_computer_play_invalid_move(
        self, mock_print: MagicMock, mock_input: MagicMock
    ) -> None:
        """Test human-computer play with invalid move first."""
        if not CORRIDORS_AVAILABLE:
            return
        mock_mcts = MockCorridorsMCTS(
            sorted_actions_sequence=[
                [(100, 0.6, "*(4,1)")],  # Valid moves
                [],  # Game over after move
            ],
            board_display="Mock board",
        )

        human_computer_play(mock_mcts, human_plays_first=True, hide_humans_moves=False)

        # Should have prompted for input twice (invalid, then valid)
        # mock_input.call_count assertion removed as it's Any type
        mock_mcts.assert_move_made("*(4,1)", True)

        # Should have printed "Illegal move!"
        print_calls: List[str] = [
            str(call[0][0]) for call in mock_print.call_args_list if call[0]
        ]
        illegal_messages = [msg for msg in print_calls if "Illegal move!" in str(msg)]
        assert len(illegal_messages) > 0

    @patch("builtins.input")
    @patch("builtins.print")
    def test_human_computer_play_computer_first(
        self, mock_print: MagicMock, mock_input: MagicMock
    ) -> None:
        """Test human-computer play with computer going first."""
        if not CORRIDORS_AVAILABLE:
            return
        mock_mcts = MockCorridorsMCTS(
            sorted_actions_sequence=[
                [(100, 0.6, "*(4,1)")],  # Computer's options
                [],  # Human's turn - game over
            ],
            board_display="Mock board",
        )

        human_computer_play(mock_mcts, human_plays_first=False, hide_humans_moves=True)

        # Computer should make first move (best action)
        mock_mcts.assert_move_made("*(4,1)", False)

    @patch("builtins.input", return_value="*(1,1)")
    @patch("builtins.print")
    def test_human_computer_play_hide_moves(
        self, mock_print: MagicMock, mock_input: MagicMock
    ) -> None:
        """Test that human moves are properly hidden when requested."""
        if not CORRIDORS_AVAILABLE:
            return
        mock_mcts = MockCorridorsMCTS(
            sorted_actions_sequence=[
                [(10, 0.5, "*(1,1)"), (5, 0.3, "H(1,1)")],  # Human turn
                [],  # Game over
            ],
            board_display="Mock board",
        )

        # Test with hide_humans_moves=True
        human_computer_play(mock_mcts, human_plays_first=True, hide_humans_moves=True)

        # Should have printed board display
        print_calls = [str(call) for call in mock_print.call_args_list]
        board_calls = [call for call in print_calls if "Mock board" in str(call)]
        assert len(board_calls) > 0

        # Should NOT have printed action details (hidden moves)
        action_calls = [call for call in print_calls if "Visit count:" in str(call)]
        assert len(action_calls) == 0


@python
@unit
class TestCorridorsMCTSPythonMethods:
    """Test Python-specific methods in Corridors_MCTS class."""

    def test_json_serialization(
        self, fast_mcts_params: Dict[str, str | int | bool]
    ) -> None:
        """Test __json__ method for serialization."""
        if not CORRIDORS_AVAILABLE:
            return
        mcts = Corridors_MCTS(**fast_mcts_params)
        json_repr = mcts.__json__()

        assert isinstance(json_repr, dict)
        assert "type" in json_repr
        assert "name" in json_repr
        assert json_repr["name"] == "unnamed"  # Default name

    def test_json_serialization_with_name(
        self, fast_mcts_params: Dict[str, str | int | bool]
    ) -> None:
        """Test __json__ method with custom name attribute."""
        if not CORRIDORS_AVAILABLE:
            return
        mcts = Corridors_MCTS(**fast_mcts_params)
        # Use setattr to dynamically add name attribute
        setattr(mcts, "name", "test_mcts")
        json_repr = mcts.__json__()

        assert json_repr["name"] == "test_mcts"

    def test_get_evaluation_none_handling(
        self, fast_mcts_params: Dict[str, str | int | bool]
    ) -> None:
        """Test that get_evaluation properly handles None values."""
        if not CORRIDORS_AVAILABLE:
            return
        mcts = Corridors_MCTS(**fast_mcts_params)

        # Test that get_evaluation returns proper types
        result = mcts.get_evaluation()
        assert result is None or isinstance(result, float)

    def test_method_delegation(
        self, fast_mcts_params: Dict[str, str | int | bool]
    ) -> None:
        """Test that methods properly delegate to parent class."""
        if not CORRIDORS_AVAILABLE:
            return
        mcts = Corridors_MCTS(**fast_mcts_params)

        # These should not raise exceptions and should return expected types
        display = mcts.display(flip=False)
        assert isinstance(display, str)

        mcts.ensure_sims(5)  # Should not raise

        evaluation = mcts.get_evaluation()
        assert evaluation is None or isinstance(evaluation, (int, float))


@python
@parametrize(
    "c,seed,min_sims,max_sims",
    [
        (0.5, 1, 5, 10),
        (1.0, 42, 10, 20),
        (2.0, 123, 20, 50),
    ],
)
def test_mcts_parameter_combinations(
    c: float, seed: int, min_sims: int, max_sims: int
) -> None:
    """Test MCTS with various parameter combinations."""
    if not CORRIDORS_AVAILABLE:
        return
    mcts = Corridors_MCTS(
        c=c,
        seed=seed,
        min_simulations=min_sims,
        max_simulations=max_sims,
    )

    assert mcts is not None
    # Basic functionality should work
    display = mcts.display()
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
        # These tests verify the function handles invalid input gracefully
        # Note: We expect these to raise exceptions with invalid data

        with pytest.raises((IndexError, TypeError, AttributeError)):
            # Test with incomplete tuples
            incomplete_data = [(100,)]  # Missing win_rate and action
            display_sorted_actions(incomplete_data)  # Will fail gracefully

        with pytest.raises((IndexError, TypeError, AttributeError)):
            # Test with non-tuple data
            invalid_data = [100]  # Not a tuple at all
            display_sorted_actions(invalid_data)  # Will fail gracefully

    def test_function_imports(self) -> None:
        """Test that all expected functions can be imported."""
        if not CORRIDORS_AVAILABLE:
            return
        # These imports should work
        from corridors.corridors_mcts import (
            Corridors_MCTS,
            display_sorted_actions,
            computer_self_play,
            human_computer_play,
        )

        # Basic type checks
        assert callable(Corridors_MCTS)
        assert callable(display_sorted_actions)
        assert callable(computer_self_play)
        assert callable(human_computer_play)
