#!/usr/bin/env python3
"""Debug by forcing positional moves only."""

import asyncio
from typing import NamedTuple, Optional, Tuple
from itertools import takewhile
from functools import partial

from corridors import AsyncCorridorsMCTS
from corridors.async_mcts import MCTSConfig


class MoveData(NamedTuple):
    move: int
    action: str
    visits: int
    equity: float
    flip: bool
    terminal: bool


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


def get_positional_actions(
    actions: Tuple[Tuple[int, float, str], ...]
) -> Tuple[Tuple[int, float, str], ...]:
    """Get only positional actions (moves starting with '*')."""
    return tuple(filter(lambda action: action[2].startswith("*"), actions))


def select_best_action(
    positional_actions: Tuple[Tuple[int, float, str], ...],
    all_actions: Tuple[Tuple[int, float, str], ...],
) -> Optional[Tuple[int, float, str]]:
    """Select best action, preferring positional moves."""
    return (
        positional_actions[0]
        if positional_actions
        else (all_actions[0] if all_actions else None)
    )


async def execute_move_step(
    mcts: AsyncCorridorsMCTS, move_num: int
) -> Optional[MoveData]:
    """Execute a single move step and return move data."""
    await mcts.ensure_sims_async(150)
    flip_value = move_num % 2 == 0
    all_actions = tuple(await mcts.get_sorted_actions_async(flip=flip_value))
    positional_actions = get_positional_actions(all_actions)

    if not positional_actions:
        print(f"No positional actions available at move {move_num}")
        not all_actions and print("No actions available at all!")

    selected_action = select_best_action(positional_actions, all_actions)

    if not selected_action:
        return None

    # Log action choice
    (
        not positional_actions
        and all_actions
        and print(f"Using non-positional action: {selected_action[2]}")
    )

    # Execute move
    await mcts.make_move_async(selected_action[2], flip=flip_value)
    evaluation = await mcts.get_evaluation_async()
    terminal = evaluation is not None and abs(evaluation) >= 1.0

    move_data = MoveData(
        move=move_num,
        action=selected_action[2],
        visits=selected_action[0],
        equity=selected_action[1],
        flip=flip_value,
        terminal=terminal,
    )

    # Print move information
    print(
        f"Move {move_num}: {selected_action[2]} "
        f"(flip={flip_value}, visits: {selected_action[0]}, equity: {selected_action[1]})"
    )
    print(f"  Evaluation after move: {evaluation}")
    terminal and print(f"  TERMINAL: evaluation {evaluation}")

    return move_data


async def generate_game_moves(
    mcts: AsyncCorridorsMCTS, max_moves: int = 15
) -> Tuple[MoveData, ...]:
    """Generate game moves until terminal or max reached."""
    moves = []
    for move_num in range(max_moves):
        move_data = await execute_move_step(mcts, move_num)
        if move_data is None or move_data.terminal:
            if move_data is not None:
                moves.append(move_data)
            break
        moves.append(move_data)
    return tuple(moves)


async def run_positional_only_game() -> None:
    """Run game with positional moves preference."""
    print("=== TESTING WITH POSITIONAL MOVES ONLY ===")

    config = create_mcts_config()
    async with AsyncCorridorsMCTS(config) as mcts:
        print("Initial evaluation:", await mcts.get_evaluation_async())

        moves = await generate_game_moves(mcts)

        print(f"\nGame with positional moves lasted {len(moves)} moves")
        print("\nFinal board state:")
        print(await mcts.display_async(flip=False))

        # Summary of moves
        print("\n=== MOVE SUMMARY ===")
        move_summaries = [
            f"Move {move.move}: {move.action} "
            f"(flip={move.flip}, visits={move.visits}, equity={move.equity:.3f})"
            for move in moves
        ]
        list(map(print, move_summaries))


async def main() -> None:
    """Main execution function."""
    await run_positional_only_game()


if __name__ == "__main__":
    asyncio.run(main())
