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
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Tuple

try:
    from python.corridors.corridors_mcts import (
        Corridors_MCTS,
        display_sorted_actions,
        computer_self_play,
        human_computer_play,
    )

    CORRIDORS_AVAILABLE = True
except ImportError:
    CORRIDORS_AVAILABLE = False


@pytest.mark.python
@pytest.mark.display
class TestDisplaySortedActions:
    """Test the display_sorted_actions utility function."""

    def test_display_empty_actions(self):
        """Test displaying empty action list."""
        result = display_sorted_actions([])

        assert isinstance(result, str)
        assert "Total Visits: 0" in result
        assert result.count("\n") >= 2  # Should have header and trailing newline

    def test_display_single_action(self, sample_actions: List[Tuple[int, float, str]]):
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
    ):
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
    ):
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

    def test_display_zero_list_size(self, sample_actions: List[Tuple[int, float, str]]):
        """Test display with list_size=0 shows all actions."""
        result_all = display_sorted_actions(sample_actions)
        result_zero = display_sorted_actions(sample_actions, list_size=0)

        assert result_all == result_zero

    @pytest.mark.parametrize(
        "visits,equity,action",
        [
            (100, 0.5555, "*(1,2)"),
            (0, 0.0, "H(0,0)"),
            (999999, 0.9999, "V(8,7)"),
            (1, -0.5432, "*(0,8)"),
        ],
    )
    def test_display_various_values(self, visits: int, equity: float, action: str):
        """Test displaying various action value combinations."""
        test_actions = [(visits, equity, action)]
        result = display_sorted_actions(test_actions)

        assert f"Total Visits: {visits}" in result
        assert f"Visit count: {visits}" in result
        assert f"{equity:.4f}" in result
        assert f"Action: {action}" in result

    def test_display_formatting_consistency(
        self, sample_actions: List[Tuple[int, float, str]]
    ):
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


@pytest.mark.python
@pytest.mark.integration
class TestComputerSelfPlay:
    """Test computer self-play functionality."""

    def test_computer_self_play_setup(self):
        """Test that computer_self_play can be called without errors in setup."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        # Mock the MCTS instances to avoid actual computation
        mock_p1 = Mock()
        mock_p1.get_sorted_actions.return_value = []  # Empty = game over
        mock_p1.display.return_value = "Mock board display"
        mock_p1.get_evaluation.return_value = None

        # Should handle empty actions list (game over immediately)
        with patch("builtins.print"):  # Suppress print output
            computer_self_play(mock_p1)

        # Verify methods were called
        mock_p1.get_sorted_actions.assert_called()

    def test_computer_self_play_single_move(self):
        """Test computer self-play with single move before game ends."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mock_p1 = Mock()
        mock_p2 = Mock()

        # First call returns actions, second call returns empty (game over)
        mock_p1.get_sorted_actions.side_effect = [
            [(100, 0.6, "*(4,1)")],  # First call - has moves
            [],  # Second call - game over
        ]
        mock_p2.get_sorted_actions.return_value = []  # Game over

        mock_p1.display.return_value = "Mock board 1"
        mock_p2.display.return_value = "Mock board 2"
        mock_p1.get_evaluation.return_value = None
        mock_p2.get_evaluation.return_value = None
        mock_p1.make_move = Mock()
        mock_p2.make_move = Mock()

        with patch("builtins.print"):  # Suppress print output
            computer_self_play(mock_p1, mock_p2)

        # Verify moves were made
        mock_p1.make_move.assert_called_with("*(4,1)", True)
        mock_p2.make_move.assert_called_with("*(4,1)", True)

    def test_computer_self_play_same_instance(self):
        """Test computer self-play using same instance for both players."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mock_instance = Mock()
        mock_instance.get_sorted_actions.return_value = []  # Game over immediately
        mock_instance.display.return_value = "Mock board"
        mock_instance.get_evaluation.return_value = None

        with patch("builtins.print"):
            computer_self_play(mock_instance)  # p2 defaults to p1

        mock_instance.get_sorted_actions.assert_called()

    def test_computer_self_play_stop_on_eval(self):
        """Test computer self-play with stop_on_eval=True."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mock_p1 = Mock()
        mock_p1.get_sorted_actions.return_value = [(100, 0.6, "*(4,8)")]  # Winning move
        mock_p1.display.return_value = "Mock winning board"
        mock_p1.get_evaluation.return_value = 1.0  # Hero wins
        mock_p1.make_move = Mock()

        with patch("builtins.print") as mock_print:
            computer_self_play(mock_p1, stop_on_eval=True)

        # Should stop after detecting terminal evaluation
        mock_p1.make_move.assert_called_once()

        # Should print winning message
        print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
        winning_messages = [msg for msg in print_calls if "wins!" in msg]
        assert len(winning_messages) > 0


@pytest.mark.python
@pytest.mark.integration
class TestHumanComputerPlay:
    """Test human-computer interaction functionality."""

    @patch("builtins.input")
    @patch("builtins.print")
    def test_human_computer_play_human_first_immediate_end(
        self, mock_print, mock_input
    ):
        """Test human-computer play when game ends immediately."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mock_mcts = Mock()
        mock_mcts.get_sorted_actions.return_value = []  # Game over immediately
        mock_mcts.display.return_value = "Game over board"

        human_computer_play(mock_mcts, human_plays_first=True)

        # Should call get_sorted_actions once
        mock_mcts.get_sorted_actions.assert_called_once()

    @patch("builtins.input", return_value="*(4,1)")
    @patch("builtins.print")
    def test_human_computer_play_single_move(self, mock_print, mock_input):
        """Test human-computer play with one move."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mock_mcts = Mock()
        # First call has moves, second call game over
        mock_mcts.get_sorted_actions.side_effect = [
            [(100, 0.6, "*(4,1)"), (50, 0.4, "*(3,0)")],  # Human's options
            [],  # Computer's turn - game over
        ]
        mock_mcts.display.return_value = "Mock board"
        mock_mcts.make_move = Mock()

        human_computer_play(mock_mcts, human_plays_first=True, hide_humans_moves=False)

        # Should make the human's move
        mock_mcts.make_move.assert_called_with("*(4,1)", True)
        mock_input.assert_called()

    @patch("builtins.input", side_effect=["invalid_move", "*(4,1)"])
    @patch("builtins.print")
    def test_human_computer_play_invalid_move(self, mock_print, mock_input):
        """Test human-computer play with invalid move first."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mock_mcts = Mock()
        mock_mcts.get_sorted_actions.side_effect = [
            [(100, 0.6, "*(4,1)")],  # Valid moves
            [],  # Game over after move
        ]
        mock_mcts.display.return_value = "Mock board"
        mock_mcts.make_move = Mock()

        human_computer_play(mock_mcts, human_plays_first=True, hide_humans_moves=False)

        # Should have prompted for input twice (invalid, then valid)
        assert mock_input.call_count == 2
        mock_mcts.make_move.assert_called_with("*(4,1)", True)

        # Should have printed "Illegal move!"
        print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
        illegal_messages = [msg for msg in print_calls if "Illegal move!" in msg]
        assert len(illegal_messages) > 0

    @patch("builtins.input")
    @patch("builtins.print")
    def test_human_computer_play_computer_first(self, mock_print, mock_input):
        """Test human-computer play with computer going first."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mock_mcts = Mock()
        mock_mcts.get_sorted_actions.side_effect = [
            [(100, 0.6, "*(4,1)")],  # Computer's options
            [],  # Human's turn - game over
        ]
        mock_mcts.display.return_value = "Mock board"
        mock_mcts.make_move = Mock()

        human_computer_play(mock_mcts, human_plays_first=False, hide_humans_moves=True)

        # Computer should make first move (best action)
        mock_mcts.make_move.assert_called_with("*(4,1)", False)
        # Human shouldn't be prompted since game ended
        mock_input.assert_not_called()

    @patch("builtins.input", return_value="*(1,1)")
    @patch("builtins.print")
    def test_human_computer_play_hide_moves(self, mock_print, mock_input):
        """Test that human moves are properly hidden when requested."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mock_mcts = Mock()
        # First call returns actions, second call returns empty (game over)
        mock_mcts.get_sorted_actions.side_effect = [
            [(10, 0.5, "*(1,1)"), (5, 0.3, "H(1,1)")],  # Human turn
            [],  # Game over
        ]
        mock_mcts.display.return_value = "Mock board"

        # Test with hide_humans_moves=True
        human_computer_play(mock_mcts, human_plays_first=True, hide_humans_moves=True)

        # Should have printed board display
        print_calls = [str(call) for call in mock_print.call_args_list]
        board_calls = [call for call in print_calls if "Mock board" in call]
        assert len(board_calls) > 0

        # Should NOT have printed action details (hidden moves)
        action_calls = [call for call in print_calls if "Visit count:" in call]
        assert len(action_calls) == 0


@pytest.mark.python
@pytest.mark.unit
class TestCorridorsMCTSPythonMethods:
    """Test Python-specific methods in Corridors_MCTS class."""

    def test_json_serialization(self, fast_mcts_params: Dict[str, Any]):
        """Test __json__ method for serialization."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mcts = Corridors_MCTS(**fast_mcts_params)
        json_repr = mcts.__json__()

        assert isinstance(json_repr, dict)
        assert "type" in json_repr
        assert "name" in json_repr
        assert json_repr["name"] == "unnamed"  # Default name

    def test_json_serialization_with_name(self, fast_mcts_params: Dict[str, Any]):
        """Test __json__ method with custom name attribute."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mcts = Corridors_MCTS(**fast_mcts_params)
        mcts.name = "test_mcts"
        json_repr = mcts.__json__()

        assert json_repr["name"] == "test_mcts"

    def test_get_evaluation_none_handling(self, fast_mcts_params: Dict[str, Any]):
        """Test that get_evaluation properly handles None values."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mcts = Corridors_MCTS(**fast_mcts_params)

        # Mock the super().get_evaluation() to return 0 (falsy)
        with patch.object(
            mcts.__class__.__bases__[0], "get_evaluation", return_value=0
        ):
            result = mcts.get_evaluation()
            assert result is None

        # Mock to return non-zero value
        with patch.object(
            mcts.__class__.__bases__[0], "get_evaluation", return_value=0.5
        ):
            result = mcts.get_evaluation()
            assert result == 0.5

    def test_method_delegation(self, fast_mcts_params: Dict[str, Any]):
        """Test that methods properly delegate to parent class."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        mcts = Corridors_MCTS(**fast_mcts_params)

        # These should not raise exceptions and should return expected types
        display = mcts.display(flip=False)
        assert isinstance(display, str)

        mcts.ensure_sims(5)  # Should not raise

        evaluation = mcts.get_evaluation()
        assert evaluation is None or isinstance(evaluation, (int, float))


@pytest.mark.python
@pytest.mark.parametrize(
    "c,seed,min_sims,max_sims",
    [
        (0.5, 1, 5, 10),
        (1.0, 42, 10, 20),
        (2.0, 123, 20, 50),
    ],
)
def test_mcts_parameter_combinations(c: float, seed: int, min_sims: int, max_sims: int):
    """Test MCTS with various parameter combinations."""
    if not CORRIDORS_AVAILABLE:
        pytest.skip("Corridors C++ module not available")

    mcts = Corridors_MCTS(
        c=c,
        seed=seed,
        min_simulations=min_sims,
        max_simulations=max_sims,
        sim_increment=5,
    )

    assert mcts is not None
    # Basic functionality should work
    display = mcts.display()
    assert isinstance(display, str)


@pytest.mark.python
@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in Python functions."""

    def test_display_sorted_actions_invalid_input(self):
        """Test display_sorted_actions with invalid input."""
        # Should handle empty gracefully
        result = display_sorted_actions([])
        assert isinstance(result, str)

        # Should handle malformed tuples gracefully
        with pytest.raises((IndexError, TypeError)):
            display_sorted_actions([(100,)])  # Missing elements

        with pytest.raises((IndexError, TypeError)):
            display_sorted_actions([100])  # Not a tuple

    def test_function_imports(self):
        """Test that all expected functions can be imported."""
        if not CORRIDORS_AVAILABLE:
            pytest.skip("Corridors C++ module not available")

        # These imports should work
        from python.corridors.corridors_mcts import (
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
