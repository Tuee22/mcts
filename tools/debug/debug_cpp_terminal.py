#!/usr/bin/env python3
"""Debug by checking what board.is_terminal() returns."""

import asyncio
from corridors import AsyncCorridorsMCTS
from corridors.async_mcts import MCTSConfig


async def main() -> None:
    """Debug terminal detection in C++ board logic."""
    # I need to create a debug version that exposes the board's is_terminal method to Python
    # For now, let me trace what's happening by looking at the evaluation logic more carefully
    config = MCTSConfig(
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
    async with AsyncCorridorsMCTS(config) as mcts:
        print("=== BEFORE MOVE ===")
        print(
            "Initial evaluation:", await mcts.get_evaluation_async()
        )  # Should be None
        print()

        await mcts.ensure_sims_async(150)
        print("Making wall move V(7,1) with flip=True")
        await mcts.make_move_async("V(7,1)", flip=True)

        print("\n=== AFTER WALL MOVE ===")
        eval_result = await mcts.get_evaluation_async()
        print("Evaluation:", eval_result, type(eval_result))
        actions = await mcts.get_sorted_actions_async(flip=False)
        print("Actions available:", len(actions))

        # The fact that there are 127 actions but evaluation is -1.0 means either:
        # 1. The board.is_terminal() is incorrectly returning true when it shouldn't
        # 2. The get_terminal_eval() is being called inappropriately
        # 3. There's a logic error in the modified get_evaluation() method

        # Let's test if the issue happens immediately after a wall placement
        print("\n=== TESTING SECOND MOVE ===")
        if actions:
            next_move = actions[0][2]  # Get the best move for villain
            print(f"Making villain move {next_move} with flip=False")
            await mcts.make_move_async(next_move, flip=False)
            eval_after_second = await mcts.get_evaluation_async()
            print("Evaluation after second move:", eval_after_second)
            actions_after_second = await mcts.get_sorted_actions_async(flip=True)
            print("Actions after second move:", len(actions_after_second))

    # Maybe the problem is that placing a wall is being interpreted as winning the game?
    # The wall V(7,1) is placed near one of the end zones, maybe that's confusing the terminal detection
    print("\n=== TESTING DIFFERENT WALL POSITIONS ===")
    for wall_pos in ["V(4,4)", "H(4,4)", "V(1,1)", "H(1,1)"]:
        test_config = MCTSConfig(
            c=1.0,
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
        async with AsyncCorridorsMCTS(test_config) as mcts_test:
            await mcts_test.ensure_sims_async(50)
            actions_before = await mcts_test.get_sorted_actions_async(flip=True)
            # Check if this wall position is legal
            legal_moves = [a[2] for a in actions_before]
            if wall_pos in legal_moves:
                print(f"Testing wall position {wall_pos}:")
                await mcts_test.make_move_async(wall_pos, flip=True)
                eval_result = await mcts_test.get_evaluation_async()
                actions_after_list = await mcts_test.get_sorted_actions_async(
                    flip=False
                )
                actions_after = len(actions_after_list)
                print(f"  Evaluation: {eval_result}, Actions: {actions_after}")
            else:
                print(f"Wall position {wall_pos} not legal")


if __name__ == "__main__":
    asyncio.run(main())
