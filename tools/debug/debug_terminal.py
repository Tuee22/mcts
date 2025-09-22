#!/usr/bin/env python3
"""Debug the terminal detection issue."""

import asyncio
from dataclasses import dataclass
from typing import Callable, Optional, List, Tuple
from functools import partial

from corridors import AsyncCorridorsMCTS
from corridors.async_mcts import MCTSConfig


@dataclass(frozen=True)
class TestResult:
    description: str
    evaluation: Optional[float]
    action_count: int
    actions: Tuple[Tuple[int, float, str], ...]


def create_mcts_config() -> MCTSConfig:
    """Factory function for MCTS config."""
    return MCTSConfig(
        c=2.0,
        seed=789,
        min_simulations=150,
        max_simulations=300,
        sim_increment=50,
        use_rollout=True,
        eval_children=False,
        use_puct=False,
        use_probs=False,
        decide_using_visits=True,
    )


async def ensure_and_get_actions(
    mcts: AsyncCorridorsMCTS, flip: bool
) -> Tuple[Tuple[int, float, str], ...]:
    """Ensure simulations and get actions."""
    await mcts.ensure_sims_async(150)
    actions = await mcts.get_sorted_actions_async(flip=flip)
    return tuple(actions)


async def create_test_result(
    description: str,
    mcts: AsyncCorridorsMCTS,
    action_getter: Callable[[], Tuple[Tuple[int, float, str], ...]],
) -> TestResult:
    """Pure function to create test results."""
    actions = await action_getter()
    evaluation = await mcts.get_evaluation_async()
    return TestResult(
        description=description,
        evaluation=evaluation,
        action_count=len(actions),
        actions=actions,
    )


async def execute_move_and_test(
    mcts: AsyncCorridorsMCTS, move: str, flip: bool, description: str
) -> TestResult:
    """Execute a move and return test result."""
    await mcts.make_move_async(move, flip=flip)
    return await create_test_result(
        description, mcts, lambda: ensure_and_get_actions(mcts, False)
    )


def filter_actions_by_type(
    actions: Tuple[Tuple[int, float, str], ...], predicate: Callable[[str], bool]
) -> Tuple[Tuple[int, float, str], ...]:
    """Filter actions by type predicate."""
    return tuple(filter(lambda action: predicate(action[2]), actions))


def get_positional_actions(
    actions: Tuple[Tuple[int, float, str], ...]
) -> Tuple[Tuple[int, float, str], ...]:
    """Get only positional actions (moves starting with '*')."""
    return filter_actions_by_type(actions, lambda move: move.startswith("*("))


def get_wall_actions(
    actions: Tuple[Tuple[int, float, str], ...]
) -> Tuple[Tuple[int, float, str], ...]:
    """Get only wall actions (moves starting with 'V(' or 'H(')."""
    return filter_actions_by_type(actions, lambda move: move.startswith(("V(", "H(")))


async def run_initial_test() -> TestResult:
    """Run initial state test."""
    config = create_mcts_config()
    async with AsyncCorridorsMCTS(config) as mcts:
        print("=== INITIAL STATE ===")
        print("Initial evaluation:", await mcts.get_evaluation_async())
        print()

        return await create_test_result(
            "Initial state", mcts, lambda: ensure_and_get_actions(mcts, True)
        )


async def run_wall_move_test() -> TestResult:
    """Test with wall move V(7,1)."""
    config = create_mcts_config()
    async with AsyncCorridorsMCTS(config) as mcts:
        await ensure_and_get_actions(mcts, True)

        print("Making move V(7,1) with flip=True")
        result = await execute_move_and_test(
            mcts, "V(7,1)", True, "After V(7,1) wall move"
        )

        print("=== POST-MOVE STATE ===")
        print("Number of actions available:", result.action_count)
        print("Evaluation (should be None for non-terminal):", result.evaluation)

        return result


async def run_positional_move_test() -> TestResult:
    """Test with positional move."""
    config = create_mcts_config()
    async with AsyncCorridorsMCTS(config) as mcts:
        print("\n=== TESTING WITH A FRESH INSTANCE ===")
        print(
            "Initial evaluation of fresh instance:", await mcts.get_evaluation_async()
        )

        actions = await ensure_and_get_actions(mcts, True)
        positional_moves = get_positional_actions(actions)

        print(f"Found {len(positional_moves)} positional moves")

        if positional_moves:
            return await execute_move_and_test(
                mcts,
                positional_moves[0][2],
                True,
                f"After positional move {positional_moves[0][2]}",
            )
        else:
            evaluation = await mcts.get_evaluation_async()
            return TestResult("No positional moves found", evaluation, 0, ())


async def run_second_wall_test() -> TestResult:
    """Test with a different wall move."""
    config = create_mcts_config()
    async with AsyncCorridorsMCTS(config) as mcts:
        actions = await ensure_and_get_actions(mcts, True)
        wall_moves = get_wall_actions(actions)

        print("\n=== TESTING ANOTHER WALL MOVE ===")

        if len(wall_moves) > 1:
            second_wall = wall_moves[1][2]
            print(f"Making second wall move {second_wall} with flip=True")
            result = await execute_move_and_test(
                mcts, second_wall, True, f"After {second_wall} wall move"
            )

            print("Actions available after second wall move:", result.action_count)
            print("Evaluation after second wall move:", result.evaluation)

            return result
        else:
            evaluation = await mcts.get_evaluation_async()
            return TestResult("Insufficient wall moves", evaluation, 0, ())


def analyze_actions(actions: Tuple[Tuple[int, float, str], ...]) -> None:
    """Analyze and display action information."""
    print("\n=== ACTION ANALYSIS ===")
    action_analysis = [
        f"Action {i}: visits={action[0]}, equity={action[1]}, move={action[2]}"
        for i, action in enumerate(actions[:10])
    ]
    list(map(print, action_analysis))


async def run_all_tests() -> None:
    """Run all debugging tests functionally."""
    tests = [
        run_initial_test,
        run_wall_move_test,
        run_positional_move_test,
        run_second_wall_test,
    ]

    results = []
    for test in tests:
        result = await test()
        results.append(result)

    # Analyze actions from first test
    if results[0].actions:
        analyze_actions(results[0].actions)

    # Print summary
    print("\n=== TEST SUMMARY ===")
    summary = [
        f"{result.description}: {result.action_count} actions, eval={result.evaluation}"
        for result in results
        if result.action_count > 0
    ]
    list(map(print, summary))


if __name__ == "__main__":
    asyncio.run(run_all_tests())
