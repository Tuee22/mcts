"""
Common test helper functions.
"""

import asyncio
from typing import Callable, Dict, List, Optional, Tuple, TypeVar, Union
from unittest.mock import MagicMock

T = TypeVar("T")


def create_mock_mcts(
    sorted_actions: Optional[List[Tuple[int, float, str]]] = None,
    evaluation: Optional[float] = None,
    display: str = "Mock Board",
) -> MagicMock:
    """
    Create a mock MCTS instance with configurable behavior.

    Args:
        sorted_actions: List of (visits, equity, action) tuples
        evaluation: Position evaluation (-1 to 1)
        display: Board display string

    Returns:
        Configured MagicMock instance
    """
    if sorted_actions is None:
        sorted_actions = [
            (100, 0.8, "*(4,1)"),
            (50, 0.6, "*(3,0)"),
            (30, 0.4, "H(4,0)"),
        ]

    mock_mcts = MagicMock()
    mock_mcts.get_sorted_actions.return_value = sorted_actions
    mock_mcts.choose_best_action.return_value = (
        sorted_actions[0][2] if sorted_actions else "*(4,1)"
    )
    mock_mcts.get_evaluation.return_value = evaluation
    mock_mcts.display.return_value = display
    mock_mcts.ensure_sims.return_value = None
    mock_mcts.make_move.return_value = None

    return mock_mcts


def assert_valid_game_response(
    response_data: Dict[str, object],
) -> None:
    """
    Assert that a game response contains all required fields with valid values.

    Args:
        response_data: Game response dictionary to validate
    """
    # Required top-level fields
    required_fields = ["id", "status", "player1", "player2", "current_player", "board"]
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"

    # Validate ID format
    game_id = response_data["id"]
    assert (
        isinstance(game_id, str) and len(game_id) > 0
    ), "Game ID must be non-empty string"

    # Validate status
    valid_statuses = ["waiting", "in_progress", "finished", "abandoned"]
    assert (
        response_data["status"] in valid_statuses
    ), f"Invalid status: {response_data['status']}"

    # Validate players
    for player_key in ["player1", "player2"]:
        player = response_data[player_key]
        assert isinstance(player, dict), f"{player_key} must be a dictionary"
        assert "name" in player, f"{player_key} missing name field"
        assert "type" in player, f"{player_key} missing type field"
        assert player["type"] in [
            "human",
            "machine",
        ], f"Invalid {player_key} type: {player['type']}"

    # Validate current player
    current_player = response_data["current_player"]
    assert current_player in [1, 2], f"Invalid current_player: {current_player}"

    # Validate board
    board = response_data["board"]
    assert isinstance(board, dict), "Board must be a dictionary"


def assert_valid_move_response(
    response_data: Dict[str, object],
) -> None:
    """
    Assert that a move response contains all required fields with valid values.

    Args:
        response_data: Move response dictionary to validate
    """
    required_fields = ["success", "action", "game_state"]
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"

    # Validate success flag
    assert isinstance(response_data["success"], bool), "Success must be a boolean"

    # Validate action
    action = response_data["action"]
    assert (
        isinstance(action, str) and len(action) > 0
    ), "Action must be non-empty string"

    # If move was successful, validate game state
    if response_data["success"]:
        game_state = response_data["game_state"]
        assert isinstance(game_state, dict), "Game state must be a dictionary"
        assert_valid_game_response(game_state)


def create_test_websocket_message(
    msg_type: str, data: Optional[Dict[str, object]] = None
) -> str:
    """
    Create a properly formatted WebSocket message for testing.

    Args:
        msg_type: Message type (e.g., "move", "analysis", "status")
        data: Optional message data

    Returns:
        JSON-encoded WebSocket message string
    """
    import json

    message: Dict[str, object] = {"type": msg_type}
    if data is not None:
        message["data"] = data

    return json.dumps(message)


def assert_websocket_message_format(message: str) -> Dict[str, object]:
    """
    Assert that a WebSocket message has proper format and return parsed data.

    Args:
        message: Raw WebSocket message string

    Returns:
        Parsed message dictionary
    """
    import json

    # Must be valid JSON
    try:
        data = json.loads(message)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON in WebSocket message: {e}")

    # Must be a dictionary
    assert isinstance(data, dict), "WebSocket message must be a JSON object"

    # Must have type field
    assert "type" in data, "WebSocket message must have 'type' field"
    assert isinstance(data["type"], str), "Message type must be a string"

    return data


async def wait_for_condition(
    condition: Callable[[], bool], timeout: float = 10.0, interval: float = 0.1
) -> None:
    """
    Wait for a condition to become true with timeout.

    Args:
        condition: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Check interval in seconds
    """
    import time

    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition():
            return
        await asyncio.sleep(interval)

    raise TimeoutError(f"Condition not met within {timeout} seconds")


def generate_test_game_config(
    player1_type: str = "human",
    player2_type: str = "human",
    board_size: int = 9,
    **kwargs: object,
) -> Dict[str, object]:
    """
    Generate a test game configuration with sensible defaults.

    Args:
        player1_type: Type of player 1 ("human" or "machine")
        player2_type: Type of player 2 ("human" or "machine")
        board_size: Size of the game board
        **kwargs: Additional configuration options

    Returns:
        Game configuration dictionary
    """
    config: Dict[str, object] = {
        "player1_type": player1_type,
        "player2_type": player2_type,
        "player1_name": "TestPlayer1",
        "player2_name": "TestPlayer2",
        "settings": {
            "board_size": board_size,
            "time_limit_seconds": 30,
            "use_analysis": False,
        },
    }

    # Merge any additional settings
    if "settings" in kwargs:
        settings = kwargs["settings"]
        if isinstance(settings, dict) and isinstance(config["settings"], dict):
            config["settings"].update(settings)
        del kwargs["settings"]
    config.update(kwargs)

    return config
