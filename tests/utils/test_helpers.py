"""
Common test helper functions.
"""

import asyncio
from typing import Dict, List
from unittest.mock import MagicMock


def create_mock_mcts(
    sorted_actions: List[tuple] = None,
    evaluation: float = None,
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


def assert_valid_game_response(response_data: Dict[str, object]) -> None:
    """
    Assert that a game response has all required fields.

    Args:
        response_data: Game response dictionary
    """
    required_fields = [
        "game_id",
        "status",
        "mode",
        "player1",
        "player2",
        "current_turn",
        "move_count",
        "created_at",
    ]

    for field in required_fields:
        assert field in response_data, f"Missing field: {field}"

    # Validate player structure
    for player_key in ["player1", "player2"]:
        player = response_data[player_key]
        player_fields = ["id", "name", "type", "is_hero"]
        for field in player_fields:
            assert field in player, f"Missing player field: {field}"


def assert_valid_move_response(response_data: Dict[str, object]) -> None:
    """
    Assert that a move response has all required fields.

    Args:
        response_data: Move response dictionary
    """
    required_fields = [
        "success",
        "game_id",
        "move",
        "game_status",
        "next_turn",
        "next_player_type",
    ]

    for field in required_fields:
        assert field in response_data, f"Missing field: {field}"

    # Validate move structure
    move = response_data["move"]
    move_fields = ["player_id", "action", "move_number", "timestamp"]
    for field in move_fields:
        assert field in move, f"Missing move field: {field}"


async def wait_for_condition(
    condition_func: callable, timeout_seconds: float = 5.0, check_interval: float = 0.1
) -> bool:
    """
    Wait for a condition to become true.

    Args:
        condition_func: Function that returns True when condition is met
        timeout_seconds: Maximum time to wait
        check_interval: How often to check the condition

    Returns:
        True if condition was met, False if timeout
    """
    elapsed = 0.0
    while elapsed < timeout_seconds:
        if condition_func():
            return True
        await asyncio.sleep(check_interval)
        elapsed += check_interval

    return False


def extract_game_moves(game_data: Dict[str, object]) -> List[str]:
    """
    Extract move actions from a game response.

    Args:
        game_data: Game response dictionary

    Returns:
        List of move action strings
    """
    if "move_history" not in game_data:
        return []

    return [move["action"] for move in game_data["move_history"]]


def count_test_results(test_output: str) -> Dict[str, int]:
    """
    Parse pytest output to count test results.

    Args:
        test_output: Raw pytest output string

    Returns:
        Dictionary with counts of passed, failed, skipped tests
    """
    results = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}

    lines = test_output.split("\n")
    for line in lines:
        if "passed" in line and "failed" not in line:
            try:
                passed = int(line.split("passed")[0].strip().split()[-1])
                results["passed"] = passed
            except (ValueError, IndexError):
                pass
        if "failed" in line:
            try:
                failed = int(line.split("failed")[0].strip().split()[-1])
                results["failed"] = failed
            except (ValueError, IndexError):
                pass

    return results
