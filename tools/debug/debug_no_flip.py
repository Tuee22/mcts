#!/usr/bin/env python3
"""Debug by testing moves without any flip logic."""

import asyncio
from enum import Enum
from typing import NamedTuple, Optional, Tuple, List
from functools import reduce

from corridors import AsyncCorridorsMCTS
from corridors.async_mcts import MCTSConfig


class FlipMode(Enum):
    NEVER = 0
    ALTERNATING = 1
    ALWAYS = 2


class MoveResult(NamedTuple):
    move: int
    action: str
    visits: int
    equity: float
    flip: bool
    evaluation: Optional[float]
    total_actions: int = 0


class GameState(NamedTuple):
    mcts: AsyncCorridorsMCTS
    moves: Tuple[MoveResult, ...]
    terminal: bool = False


def get_flip_value(move_num: int, mode: FlipMode) -> bool:
    """Pure function to determine flip value based on mode."""
    return {
        FlipMode.NEVER: False,
        FlipMode.ALTERNATING: move_num % 2 == 0,
        FlipMode.ALWAYS: True,
    }[mode]


def create_move_result(
    move_num: int,
    action: Tuple[int, float, str],
    flip: bool,
    evaluation: Optional[float],
    total_actions: int,
) -> MoveResult:
    """Pure function to create move result."""
    return MoveResult(
        move=move_num,
        action=action[2],
        visits=action[0],
        equity=action[1],
        flip=flip,
        evaluation=evaluation,
        total_actions=total_actions,
    )


async def execute_move(
    state: GameState, move_num: int, flip_mode: FlipMode
) -> GameState:
    """Execute a single move asynchronously."""
    await state.mcts.ensure_sims_async(150)
    flip = get_flip_value(move_num, flip_mode)
    actions = await state.mcts.get_sorted_actions_async(flip=flip)

    if not actions:
        print(f"No actions available at move {move_num}")
        return GameState(state.mcts, state.moves, True)

    best_action = actions[0]
    await state.mcts.make_move_async(best_action[2], flip=flip)
    evaluation = await state.mcts.get_evaluation_async()

    move_result = create_move_result(
        move_num, best_action, flip, evaluation, len(actions)
    )

    print(
        f"Move {move_num}: {best_action[2]} (flip={flip}, visits: {best_action[0]}, equity: {best_action[1]})"
    )
    evaluation is not None and print(f"  Evaluation after move: {evaluation}")

    terminal = evaluation is not None and abs(evaluation) >= 1.0
    terminal and print(f"  TERMINAL: evaluation {evaluation}")

    return GameState(state.mcts, state.moves + (move_result,), terminal)


async def play_game(
    mcts: AsyncCorridorsMCTS, flip_mode: FlipMode, max_moves: int = 10
) -> Tuple[MoveResult, ...]:
    """Async game player."""
    state = GameState(mcts, ())

    for move_num in range(max_moves):
        if state.terminal:
            break
        state = await execute_move(state, move_num, flip_mode)

    return state.moves


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


async def run_test(description: str, flip_mode: FlipMode) -> None:
    """Run a single test with given flip mode."""
    print(f"\n{'=' * 60}")
    print(f"\n=== {description} ===")

    config = create_mcts_config()
    async with AsyncCorridorsMCTS(config) as mcts:
        print("Initial evaluation:", await mcts.get_evaluation_async())

        moves = await play_game(mcts, flip_mode)
        print(f"\nGame lasted {len(moves)} moves with {description.lower()}")


async def main():
    """Main execution function."""
    tests = [
        ("TESTING WITHOUT FLIP", FlipMode.NEVER),
        ("TESTING WITH ALTERNATING FLIP (original logic)", FlipMode.ALTERNATING),
        ("TESTING WITH CONSISTENT FLIP=TRUE", FlipMode.ALWAYS),
    ]

    for description, flip_mode in tests:
        await run_test(description, flip_mode)


if __name__ == "__main__":
    asyncio.run(main())
