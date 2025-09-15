#!/usr/bin/env python3
"""
Test the updated GameManager with async MCTS.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend", "python"))

from backend.api.game_manager import GameManager
from backend.api.models import PlayerType, GameSettings


async def main():
    print("Testing GameManager with async MCTS...")

    gm = GameManager()
    print("✓ GameManager created")

    try:
        # Test game creation
        game = await gm.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.MACHINE,
            player1_name="Test Player",
            player2_name="AI Player",
        )
        print(f"✓ Game created: {game.game_id}")

        # Test MCTS registry
        mcts = await gm.mcts_registry.get(game.game_id)
        if mcts:
            print("✓ MCTS instance retrieved from registry")

            # Test some operations
            visits = await mcts.get_visit_count_async()
            print(f"✓ Initial visit count: {visits}")

            actions = await mcts.get_sorted_actions_async()
            print(f"✓ Got {len(actions)} legal actions")

        # Test cleanup
        await gm.cleanup()
        print("✓ Cleanup successful")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        await gm.cleanup()

    print("✓ SUCCESS: All GameManager tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
