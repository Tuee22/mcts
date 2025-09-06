"""Comprehensive tests for test helper functions."""

import asyncio
import json
import pytest
from typing import Dict, List, Tuple, Union
from unittest.mock import MagicMock

from tests.utils.test_helpers import (
    assert_valid_game_response,
    assert_valid_move_response,
    assert_websocket_message_format,
    create_mock_mcts,
    create_test_websocket_message,
    generate_test_game_config,
    wait_for_condition,
)


class TestCreateMockMCTS:
    """Test the create_mock_mcts helper function."""

    def test_create_mock_mcts_with_defaults(self) -> None:
        """Test creating mock MCTS with default parameters."""
        mock = create_mock_mcts()

        # Verify it's a MagicMock
        assert isinstance(mock, MagicMock)

        # Test default behavior
        # The mock was configured to return the expected values
        expected_actions = [
            (100, 0.8, "*(4,1)"),
            (50, 0.6, "*(3,0)"),
            (30, 0.4, "H(4,0)"),
        ]

        # Verify the mock was called properly by checking its configuration
        assert mock.get_sorted_actions.return_value == expected_actions
        assert mock.choose_best_action.return_value == "*(4,1)"
        assert mock.display.return_value == "Mock Board"
        assert mock.get_evaluation.return_value is None

    def test_create_mock_mcts_with_custom_actions(self) -> None:
        """Test creating mock MCTS with custom actions."""
        custom_actions = [
            (200, 0.9, "*(5,5)"),
            (150, 0.7, "V(2,3)"),
            (100, 0.5, "H(1,4)"),
        ]

        mock = create_mock_mcts(sorted_actions=custom_actions)

        # Verify the mock was configured correctly
        assert mock.get_sorted_actions.return_value == custom_actions
        assert mock.choose_best_action.return_value == "*(5,5)"  # First action

    def test_create_mock_mcts_with_evaluation(self) -> None:
        """Test creating mock MCTS with position evaluation."""
        mock = create_mock_mcts(evaluation=0.75)

        # Verify the mock was configured correctly
        assert mock.get_evaluation.return_value == 0.75

    def test_create_mock_mcts_with_custom_display(self) -> None:
        """Test creating mock MCTS with custom display."""
        custom_display = "Custom Test Board\n1 2 3\n4 5 6"
        mock = create_mock_mcts(display=custom_display)

        # Verify the mock was configured correctly
        assert mock.display.return_value == custom_display

    def test_create_mock_mcts_empty_actions(self) -> None:
        """Test creating mock MCTS with empty actions list."""
        mock = create_mock_mcts(sorted_actions=[])

        # Verify the mock was configured correctly
        assert mock.get_sorted_actions.return_value == []
        # Should still return default action
        assert mock.choose_best_action.return_value == "*(4,1)"

    def test_mock_mcts_method_calls(self) -> None:
        """Test that mock MCTS methods can be called without error."""
        mock = create_mock_mcts()

        # These should not raise exceptions
        mock.ensure_sims()
        mock.make_move("*(3,3)")

        # Verify return values are as expected
        assert mock.ensure_sims.return_value is None
        assert mock.make_move.return_value is None


class TestAssertValidGameResponse:
    """Test the assert_valid_game_response helper function."""

    def test_valid_game_response(self) -> None:
        """Test with a valid game response."""
        response = {
            "id": "game123",
            "status": "in_progress",
            "player1": {"name": "Alice", "type": "human"},
            "player2": {"name": "Bob", "type": "machine"},
            "current_player": 1,
            "board": {"size": 9, "walls": []},
        }

        # Should not raise any assertion errors
        assert_valid_game_response(response)

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise assertions."""
        base_response = {
            "id": "game123",
            "status": "in_progress",
            "player1": {"name": "Alice", "type": "human"},
            "player2": {"name": "Bob", "type": "machine"},
            "current_player": 1,
            "board": {"size": 9},
        }

        required_fields = [
            "id",
            "status",
            "player1",
            "player2",
            "current_player",
            "board",
        ]

        for field in required_fields:
            response = base_response.copy()
            del response[field]

            with pytest.raises(
                AssertionError, match=f"Missing required field: {field}"
            ):
                assert_valid_game_response(response)

    def test_invalid_game_id(self) -> None:
        """Test invalid game ID formats."""
        response = {
            "id": "",  # Empty string
            "status": "in_progress",
            "player1": {"name": "Alice", "type": "human"},
            "player2": {"name": "Bob", "type": "machine"},
            "current_player": 1,
            "board": {"size": 9},
        }

        with pytest.raises(AssertionError, match="Game ID must be non-empty string"):
            assert_valid_game_response(response)

    def test_invalid_status(self) -> None:
        """Test invalid game status values."""
        response = {
            "id": "game123",
            "status": "invalid_status",
            "player1": {"name": "Alice", "type": "human"},
            "player2": {"name": "Bob", "type": "machine"},
            "current_player": 1,
            "board": {"size": 9},
        }

        with pytest.raises(AssertionError, match="Invalid status: invalid_status"):
            assert_valid_game_response(response)

    def test_valid_statuses(self) -> None:
        """Test all valid status values."""
        valid_statuses = ["waiting", "in_progress", "finished", "abandoned"]

        base_response = {
            "id": "game123",
            "player1": {"name": "Alice", "type": "human"},
            "player2": {"name": "Bob", "type": "machine"},
            "current_player": 1,
            "board": {"size": 9},
        }

        for status in valid_statuses:
            response = base_response.copy()
            response["status"] = status

            # Should not raise any assertion errors
            assert_valid_game_response(response)

    def test_invalid_player_structure(self) -> None:
        """Test invalid player dictionary structures."""
        response = {
            "id": "game123",
            "status": "in_progress",
            "player1": "not_a_dict",  # Should be dict
            "player2": {"name": "Bob", "type": "machine"},
            "current_player": 1,
            "board": {"size": 9},
        }

        with pytest.raises(AssertionError, match="player1 must be a dictionary"):
            assert_valid_game_response(response)

    def test_missing_player_fields(self) -> None:
        """Test missing name/type fields in player dictionaries."""
        response = {
            "id": "game123",
            "status": "in_progress",
            "player1": {"type": "human"},  # Missing name
            "player2": {"name": "Bob", "type": "machine"},
            "current_player": 1,
            "board": {"size": 9},
        }

        with pytest.raises(AssertionError, match="player1 missing name field"):
            assert_valid_game_response(response)

    def test_invalid_player_type(self) -> None:
        """Test invalid player type values."""
        response = {
            "id": "game123",
            "status": "in_progress",
            "player1": {"name": "Alice", "type": "robot"},  # Invalid type
            "player2": {"name": "Bob", "type": "machine"},
            "current_player": 1,
            "board": {"size": 9},
        }

        with pytest.raises(AssertionError, match="Invalid player1 type: robot"):
            assert_valid_game_response(response)

    def test_invalid_current_player(self) -> None:
        """Test invalid current_player values."""
        response = {
            "id": "game123",
            "status": "in_progress",
            "player1": {"name": "Alice", "type": "human"},
            "player2": {"name": "Bob", "type": "machine"},
            "current_player": 3,  # Should be 1 or 2
            "board": {"size": 9},
        }

        with pytest.raises(AssertionError, match="Invalid current_player: 3"):
            assert_valid_game_response(response)

    def test_invalid_board_structure(self) -> None:
        """Test invalid board structure."""
        response = {
            "id": "game123",
            "status": "in_progress",
            "player1": {"name": "Alice", "type": "human"},
            "player2": {"name": "Bob", "type": "machine"},
            "current_player": 1,
            "board": "not_a_dict",  # Should be dict
        }

        with pytest.raises(AssertionError, match="Board must be a dictionary"):
            assert_valid_game_response(response)


class TestAssertValidMoveResponse:
    """Test the assert_valid_move_response helper function."""

    def test_valid_successful_move(self) -> None:
        """Test with a valid successful move response."""
        response = {
            "success": True,
            "action": "*(4,1)",
            "game_state": {
                "id": "game123",
                "status": "in_progress",
                "player1": {"name": "Alice", "type": "human"},
                "player2": {"name": "Bob", "type": "machine"},
                "current_player": 2,
                "board": {"size": 9, "walls": []},
            },
        }

        # Should not raise any assertion errors
        assert_valid_move_response(response)

    def test_valid_failed_move(self) -> None:
        """Test with a valid failed move response."""
        response = {
            "success": False,
            "action": "*(9,9)",  # Invalid move
            "game_state": {"error": "Invalid move"},
        }

        # Should not raise any assertion errors (game_state validation skipped for failed moves)
        assert_valid_move_response(response)

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise assertions."""
        base_response = {
            "success": True,
            "action": "*(4,1)",
            "game_state": {
                "id": "game123",
                "status": "in_progress",
                "player1": {"name": "Alice", "type": "human"},
                "player2": {"name": "Bob", "type": "machine"},
                "current_player": 2,
                "board": {"size": 9},
            },
        }

        required_fields = ["success", "action", "game_state"]

        for field in required_fields:
            response = base_response.copy()
            del response[field]

            with pytest.raises(
                AssertionError, match=f"Missing required field: {field}"
            ):
                assert_valid_move_response(response)

    def test_invalid_success_type(self) -> None:
        """Test invalid success field type."""
        response: Dict[str, object] = {
            "success": "true",  # Should be boolean
            "action": "*(4,1)",
            "game_state": {},
        }

        with pytest.raises(AssertionError, match="Success must be a boolean"):
            assert_valid_move_response(response)

    def test_invalid_action_format(self) -> None:
        """Test invalid action formats."""
        response = {
            "success": True,
            "action": "",  # Empty string
            "game_state": {
                "id": "game123",
                "status": "in_progress",
                "player1": {"name": "Alice", "type": "human"},
                "player2": {"name": "Bob", "type": "machine"},
                "current_player": 2,
                "board": {"size": 9},
            },
        }

        with pytest.raises(AssertionError, match="Action must be non-empty string"):
            assert_valid_move_response(response)

    def test_invalid_game_state_for_successful_move(self) -> None:
        """Test that successful moves validate game state."""
        response = {
            "success": True,
            "action": "*(4,1)",
            "game_state": "not_a_dict",  # Should be dict
        }

        with pytest.raises(AssertionError, match="Game state must be a dictionary"):
            assert_valid_move_response(response)


class TestWebSocketHelpers:
    """Test WebSocket message helper functions."""

    def test_create_test_websocket_message_basic(self) -> None:
        """Test creating basic WebSocket message."""
        message = create_test_websocket_message("move")
        parsed = json.loads(message)

        assert parsed == {"type": "move"}

    def test_create_test_websocket_message_with_data(self) -> None:
        """Test creating WebSocket message with data."""
        data = {"action": "*(4,1)", "player": 1}
        message = create_test_websocket_message("move", data)
        parsed = json.loads(message)

        expected = {"type": "move", "data": {"action": "*(4,1)", "player": 1}}
        assert parsed == expected

    def test_assert_websocket_message_format_valid(self) -> None:
        """Test validating properly formatted WebSocket message."""
        message = '{"type": "move", "data": {"action": "*(4,1)"}}'

        parsed = assert_websocket_message_format(message)
        expected = {"type": "move", "data": {"action": "*(4,1)"}}
        assert parsed == expected

    def test_assert_websocket_message_format_invalid_json(self) -> None:
        """Test that invalid JSON raises assertion."""
        message = "not valid json"

        with pytest.raises(AssertionError, match="Invalid JSON in WebSocket message"):
            assert_websocket_message_format(message)

    def test_assert_websocket_message_format_not_object(self) -> None:
        """Test that non-object JSON raises assertion."""
        message = '"just a string"'

        with pytest.raises(
            AssertionError, match="WebSocket message must be a JSON object"
        ):
            assert_websocket_message_format(message)

    def test_assert_websocket_message_format_missing_type(self) -> None:
        """Test that missing type field raises assertion."""
        message = '{"data": {"some": "data"}}'

        with pytest.raises(
            AssertionError, match="WebSocket message must have 'type' field"
        ):
            assert_websocket_message_format(message)

    def test_assert_websocket_message_format_invalid_type(self) -> None:
        """Test that non-string type raises assertion."""
        message = '{"type": 123, "data": {}}'

        with pytest.raises(AssertionError, match="Message type must be a string"):
            assert_websocket_message_format(message)


class TestWaitForCondition:
    """Test the wait_for_condition helper function."""

    @pytest.mark.asyncio
    async def test_wait_for_condition_immediate_success(self) -> None:
        """Test waiting for condition that's immediately true."""
        condition = lambda: True

        # Should return immediately
        await wait_for_condition(condition, timeout=1.0)

    @pytest.mark.asyncio
    async def test_wait_for_condition_eventual_success(self) -> None:
        """Test waiting for condition that becomes true."""
        counter = [0]  # Use list for mutable reference

        def condition() -> bool:
            counter[0] += 1
            return counter[0] >= 3

        # Should succeed after a few checks
        await wait_for_condition(condition, timeout=2.0, interval=0.05)
        assert counter[0] >= 3

    @pytest.mark.asyncio
    async def test_wait_for_condition_timeout(self) -> None:
        """Test that timeout raises TimeoutError."""
        condition = lambda: False

        with pytest.raises(TimeoutError, match="Condition not met within 0.1 seconds"):
            await wait_for_condition(condition, timeout=0.1, interval=0.01)

    @pytest.mark.asyncio
    async def test_wait_for_condition_custom_interval(self) -> None:
        """Test custom check interval."""
        import time

        start_time = time.time()
        checks = [0]

        def condition() -> bool:
            checks[0] += 1
            return checks[0] >= 3

        await wait_for_condition(condition, timeout=1.0, interval=0.2)

        # Should have taken at least 2 intervals (0.4 seconds)
        elapsed = time.time() - start_time
        assert elapsed >= 0.35  # Allow some tolerance


class TestGenerateTestGameConfig:
    """Test the generate_test_game_config helper function."""

    def test_generate_config_defaults(self) -> None:
        """Test generating config with all defaults."""
        config = generate_test_game_config()

        expected = {
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": "TestPlayer1",
            "player2_name": "TestPlayer2",
            "settings": {
                "board_size": 9,
                "time_limit_seconds": 30,
                "use_analysis": False,
            },
        }

        assert config == expected

    def test_generate_config_custom_players(self) -> None:
        """Test generating config with custom player types."""
        config = generate_test_game_config(player1_type="machine", player2_type="human")

        assert config["player1_type"] == "machine"
        assert config["player2_type"] == "human"
        assert config["player1_name"] == "TestPlayer1"
        assert config["player2_name"] == "TestPlayer2"

    def test_generate_config_custom_board_size(self) -> None:
        """Test generating config with custom board size."""
        config = generate_test_game_config(board_size=7)

        settings = config["settings"]
        assert isinstance(settings, dict)
        assert settings["board_size"] == 7
        assert settings["time_limit_seconds"] == 30  # Other defaults unchanged

    def test_generate_config_additional_kwargs(self) -> None:
        """Test generating config with additional top-level options."""
        config = generate_test_game_config(
            player1_name="CustomPlayer1",
            player2_name="CustomPlayer2",
            custom_field="custom_value",
        )

        assert config["player1_name"] == "CustomPlayer1"
        assert config["player2_name"] == "CustomPlayer2"
        assert config["custom_field"] == "custom_value"

    def test_generate_config_custom_settings(self) -> None:
        """Test generating config with custom settings."""
        custom_settings = {
            "time_limit_seconds": 60,
            "use_analysis": True,
            "custom_setting": "test_value",
        }

        config = generate_test_game_config(settings=custom_settings)

        expected_settings = {
            "board_size": 9,  # Default preserved
            "time_limit_seconds": 60,  # Overridden
            "use_analysis": True,  # Overridden
            "custom_setting": "test_value",  # Added
        }

        assert config["settings"] == expected_settings

    def test_generate_config_settings_merge(self) -> None:
        """Test that settings are properly merged with defaults."""
        config = generate_test_game_config(
            board_size=7,  # This should be ignored in favor of settings
            settings={"board_size": 5, "new_option": True},
        )

        # Settings should take precedence and be merged
        expected_settings = {
            "board_size": 5,  # From settings, not the board_size parameter
            "time_limit_seconds": 30,  # Default
            "use_analysis": False,  # Default
            "new_option": True,  # Added from settings
        }

        assert config["settings"] == expected_settings
