#!/usr/bin/env python3
"""
Test the async MCTS interface.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend", "python"))

from corridors.async_mcts import AsyncCorridorsMCTS


async def main():
    print("Testing async MCTS interface...")

    async with AsyncCorridorsMCTS() as mcts:
        print("✓ AsyncCorridorsMCTS created")

        # Test simulations
        completed = await mcts.run_simulations_async(100)
        print(f"✓ Completed {completed} simulations")

        # Test visit count
        visits = await mcts.get_visit_count_async()
        print(f"✓ Visit count: {visits}")

        # Test actions
        actions = await mcts.get_sorted_actions_async()
        print(f"✓ Got {len(actions)} legal actions")

        # Test evaluation
        eval_result = await mcts.get_evaluation_async()
        print(f"✓ Evaluation: {eval_result}")

        # Test display
        display = await mcts.display_async()
        print("✓ Board display retrieved")
        print(f"Display preview: {display[:50]}...")

    print("✓ SUCCESS: All async tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
