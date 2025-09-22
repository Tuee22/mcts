#!/usr/bin/env python3
"""Debug the actual board state after wall moves."""

import asyncio
from typing import Optional
from corridors import AsyncCorridorsMCTS
from corridors.async_mcts import MCTSConfig


async def print_board_analysis(name: str, mcts: AsyncCorridorsMCTS) -> None:
    """Analyze and print board state information."""
    print(f"=== {name} ===")
    display = await mcts.display_async(flip=False)
    print("Board state:")
    print(display)

    # Extract positions from display
    lines = display.strip().split("\n")
    hero_pos = villain_pos = None
    for y, line in enumerate(lines):
        if "h" in line.lower():
            x = line.lower().find("h") // 4  # Each column is ~4 chars wide
            hero_pos = (x, len(lines) - 1 - y)  # Flip y coordinate
        if "v" in line.lower():
            x = line.lower().find("v") // 4
            villain_pos = (x, len(lines) - 1 - y)

    print(f"Hero position (estimated): {hero_pos}")
    print(f"Villain position (estimated): {villain_pos}")
    if hero_pos and hero_pos[1] == 8:
        print("*** HERO AT WINNING POSITION (y=8) ***")
    if villain_pos and villain_pos[1] == 0:
        print("*** VILLAIN AT WINNING POSITION (y=0) ***")

    eval_result = await mcts.get_evaluation_async()
    print(f"Evaluation: {eval_result}")
    actions = await mcts.get_sorted_actions_async(flip=False)
    print(f"Actions available: {len(actions)}")
    print()


async def main() -> None:
    """Debug board state after various moves."""
    # Test the problematic sequence
    config1 = MCTSConfig(
        c=2.0,
        seed=789,
        min_simulations=50,
        max_simulations=100,
        sim_increment=50,
        use_rollout=True,
        eval_children=False,
        use_puct=False,
        use_probs=False,
        decide_using_visits=True,
    )
    async with AsyncCorridorsMCTS(config1) as mcts1:
        await print_board_analysis("INITIAL STATE", mcts1)
        await mcts1.ensure_sims_async(50)
        print("Making wall move V(7,1) with flip=True")
        await mcts1.make_move_async("V(7,1)", flip=True)
        await print_board_analysis("AFTER V(7,1) WITH FLIP=TRUE", mcts1)

    # Compare with a positional move
    config2 = MCTSConfig(
        c=2.0,
        seed=789,
        min_simulations=50,
        max_simulations=100,
        sim_increment=50,
        use_rollout=True,
        eval_children=False,
        use_puct=False,
        use_probs=False,
        decide_using_visits=True,
    )
    async with AsyncCorridorsMCTS(config2) as mcts2:
        await mcts2.ensure_sims_async(50)
        print("Making positional move *(3,0) with flip=True")
        await mcts2.make_move_async("*(3,0)", flip=True)
        await print_board_analysis("AFTER *(3,0) WITH FLIP=TRUE", mcts2)

    # Test the same wall move WITHOUT flip to see the difference
    config3 = MCTSConfig(
        c=2.0,
        seed=789,
        min_simulations=50,
        max_simulations=100,
        sim_increment=50,
        use_rollout=True,
        eval_children=False,
        use_puct=False,
        use_probs=False,
        decide_using_visits=True,
    )
    async with AsyncCorridorsMCTS(config3) as mcts3:
        await mcts3.ensure_sims_async(50)
        actions = await mcts3.get_sorted_actions_async(
            flip=False
        )  # Get actions without flip
        wall_actions = [a for a in actions if a[2].startswith("V(")]
        if wall_actions:
            wall_move = wall_actions[0][2]
            print(f"Making wall move {wall_move} with flip=False")
            await mcts3.make_move_async(wall_move, flip=False)
            await print_board_analysis(f"AFTER {wall_move} WITH FLIP=FALSE", mcts3)


if __name__ == "__main__":
    asyncio.run(main())
