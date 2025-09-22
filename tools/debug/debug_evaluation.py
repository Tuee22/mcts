#!/usr/bin/env python3
"""Debug the evaluation issue in integration tests."""

import asyncio
from corridors import AsyncCorridorsMCTS
from corridors.async_mcts import MCTSConfig


async def main():
    """Debug evaluation issue with async MCTS."""
    # Reproduce the exact same setup as the failing test
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
        print("=== INITIAL STATE ===")
        print("Display:")
        print(await mcts.display_async(flip=False))
        print()
        print("Initial evaluation:", await mcts.get_evaluation_async())

        # Ensure simulations
        print("Ensuring 150 simulations...")
        await mcts.ensure_sims_async(150)

        # Get actions for the first move (Hero turn, move_num % 2 == 0 is True, so flip=True)
        print("Getting actions with flip=True (Hero turn)...")
        actions = await mcts.get_sorted_actions_async(flip=True)
        print(f"Number of actions: {len(actions)}")

        if actions:
            best_action = actions[0]
            print(f"Best action: {best_action}")
            print(
                f"Best action details: visits={best_action[0]}, equity={best_action[1]}, action='{best_action[2]}'"
            )

            print("\n=== MAKING MOVE ===")
            print(f"Making move: {best_action[2]} with flip=True")
            # Make the move
            await mcts.make_move_async(best_action[2], flip=True)

            print("\n=== STATE AFTER MOVE ===")
            print("Display after move:")
            print(await mcts.display_async(flip=False))
            print()

            # Check evaluation after move
            evaluation = await mcts.get_evaluation_async()
            print(f"Evaluation after move: {evaluation}")
            print(
                f"Terminal condition check: evaluation is not None = {evaluation is not None}"
            )
            if evaluation is not None:
                print(f"abs(evaluation) = {abs(evaluation)}")
                print(f"abs(evaluation) >= 1.0 = {abs(evaluation) >= 1.0}")

            # If the evaluation is exactly -1.0 or 1.0, let's examine the board state
            if evaluation is not None and abs(evaluation) >= 1.0:
                print(f"TERMINAL: evaluation {evaluation} >= 1.0 (absolute value)")
                print("This explains why the game ends after just one move!")

                # Let's see what actions are available after this move
                print("\n=== CHECKING POST-MOVE STATE ===")
                actions_after = await mcts.get_sorted_actions_async(
                    flip=False
                )  # Villain's turn
                print(f"Actions available after move: {len(actions_after)}")
                if len(actions_after) == 0:
                    print("No actions available - position is terminal")
                else:
                    print(
                        "Actions still available, so evaluation logic might be incorrect"
                    )
                    for i, action in enumerate(actions_after[:3]):
                        print(f"  Action {i}: {action}")
        else:
            print("No actions available initially!")


if __name__ == "__main__":
    asyncio.run(main())
