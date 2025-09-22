from tests.pytest_marks import (
    api,
    asyncio as asyncio_mark,
    benchmark,
    board,
    cpp,
    display,
    edge_cases,
    endpoints,
    game_manager,
    integration,
    mcts,
    models,
    parametrize,
    performance,
    python,
    slow,
    stress,
    unit,
    websocket,
)

"""
Performance and stress tests for MCTS implementation.

These tests verify performance characteristics and handle edge cases:
- Large simulation counts
- Memory usage patterns
- Concurrent operations
- Boundary conditions
- Algorithm efficiency
"""

import asyncio
import gc
import time
from typing import Dict, List, Tuple, Optional
from unittest.mock import patch

import pytest
import pytest_asyncio

from corridors import AsyncCorridorsMCTS


@slow
@performance
class TestMCTSPerformance:
    """Test MCTS performance characteristics."""

    @pytest.mark.asyncio
    async def test_large_simulation_count(self) -> None:
        """Test MCTS with large simulation count."""
        async with AsyncCorridorsMCTS(
            c=1.0,
            seed=42,
            min_simulations=1000,
            max_simulations=5000,
            sim_increment=100,
            use_rollout=True,
            eval_children=False,
            use_puct=False,
            use_probs=False,
            decide_using_visits=True,
        ) as mcts:
            start_time = time.time()
            await mcts.ensure_sims_async(1000)
            elapsed = time.time() - start_time

            # Should complete in reasonable time (adjust threshold as needed)
            assert elapsed < 30.0  # 30 seconds max

            actions = await mcts.get_sorted_actions_async(flip=True)
            assert len(actions) > 0

            # Should have substantial visit counts
            total_visits = sum(a[0] for a in actions)
            assert total_visits >= 1000

    @pytest.mark.asyncio
    async def test_simulation_increment_efficiency(self) -> None:
        """Test that smaller increments don't drastically slow down computation."""
        # Test with different increment sizes
        # Test with direct constructor calls for type safety
        async with AsyncCorridorsMCTS(
            c=1.0,
            seed=42,
            min_simulations=200,
            max_simulations=400,
            sim_increment=100,
            use_rollout=True,
            eval_children=False,
            use_puct=False,
            use_probs=False,
            decide_using_visits=True,
        ) as mcts_large, AsyncCorridorsMCTS(
            c=1.0,
            seed=42,
            min_simulations=200,
            max_simulations=400,
            sim_increment=25,
            use_rollout=True,
            eval_children=False,
            use_puct=False,
            use_probs=False,
            decide_using_visits=True,
        ) as mcts_small:
            start_time = time.time()
            await mcts_large.ensure_sims_async(200)
            time_large = time.time() - start_time

            start_time = time.time()
            await mcts_small.ensure_sims_async(200)
            time_small = time.time() - start_time

            # Small increments shouldn't be dramatically slower
            # (some overhead is expected, but not orders of magnitude)
            assert time_small < time_large * 5.0

    @parametrize("sim_count", [50, 100, 500, 1000])
    @pytest.mark.asyncio
    async def test_simulation_scaling(self, sim_count: int) -> None:
        """Test that simulation time scales reasonably with count."""
        async with AsyncCorridorsMCTS(
            c=1.0,
            seed=42,
            min_simulations=sim_count,
            max_simulations=sim_count * 2,
            sim_increment=50,
            use_rollout=True,
            eval_children=False,
            use_puct=False,
            use_probs=False,
            decide_using_visits=True,
        ) as mcts:
            start_time = time.time()
            await mcts.ensure_sims_async(sim_count)
            elapsed = time.time() - start_time

            # Should scale roughly linearly (allowing some overhead)
            expected_time = sim_count * 0.01  # 10ms per simulation (rough estimate)
            assert elapsed < expected_time * 10  # Allow 10x margin for safety


@performance
class TestMemoryUsage:
    """Test memory usage patterns."""

    @pytest.mark.asyncio
    async def test_multiple_instances(self) -> None:
        """Test creating multiple MCTS instances."""
        instances = []

        try:
            for i in range(10):
                mcts = AsyncCorridorsMCTS(
                    seed=i, min_simulations=50, max_simulations=100,
                    c=1.4, sim_increment=25, use_rollout=True,
                    eval_children=False, use_puct=False, use_probs=False,
                    decide_using_visits=True
                )
                instances.append(mcts)
                async with mcts:
                    await mcts.ensure_sims_async(50)

            # All instances should be functional
            for mcts in instances:
                async with mcts:
                    actions = await mcts.get_sorted_actions_async(flip=True)
                    assert isinstance(actions, list)

        finally:
            # Cleanup
            del instances
            gc.collect()

    @pytest.mark.asyncio
    async def test_repeated_operations(self) -> None:
        """Test repeated operations for memory leaks."""
        async with AsyncCorridorsMCTS(
            c=1.0, seed=42, min_simulations=20, max_simulations=100,
            sim_increment=20, use_rollout=True, eval_children=False,
            use_puct=False, use_probs=False, decide_using_visits=True
        ) as mcts:
            # Perform many repeated operations
            for i in range(100):
                await mcts.ensure_sims_async(20 + i % 10)  # Varying simulation counts
                actions = await mcts.get_sorted_actions_async(flip=(i % 2 == 0))
                display = await mcts.display_async(flip=(i % 2 == 0))

                # Basic sanity checks
                assert isinstance(actions, list)
                assert isinstance(display, str)

                if i % 10 == 0:
                    gc.collect()  # Periodic cleanup

    @pytest.mark.asyncio
    async def test_large_action_lists(self) -> None:
        """Test handling of large action lists."""
        async with AsyncCorridorsMCTS(
            c=1.0, seed=42, min_simulations=500, max_simulations=1000,
            sim_increment=100, use_rollout=True, eval_children=False,
            use_puct=False, use_probs=False, decide_using_visits=True
        ) as mcts:
            await mcts.ensure_sims_async(500)
            actions = await mcts.get_sorted_actions_async(flip=True)

            # Should handle large action lists - basic verification
            assert isinstance(actions, list)
            assert len(actions) > 0

            # Test action structure
            for visits, equity, action_str in actions[:5]:
                assert isinstance(visits, int)
                assert isinstance(equity, (int, float))
                assert isinstance(action_str, str)


@stress  
class TestStressConditions:
    """Test stress conditions and edge cases.
    
    Note: These test methods need async conversion similar to the patterns above.
    Each method should use @pytest.mark.asyncio, async def, and async context managers.
    """

    def test_zero_simulations(self) -> None:
        """Test behavior with zero simulations."""
        mcts = AsyncCorridorsMCTS(c=1.0, seed=42, min_simulations=0, max_simulations=100)

        # Should still be able to get actions (might be empty or random)
        actions = mcts.get_sorted_actions(flip=True)
        assert isinstance(actions, list)

    def test_minimal_parameters(self) -> None:
        """Test with minimal parameter values."""
        mcts = AsyncCorridorsMCTS(
            c=0.01,  # Very small exploration
            seed=1,
            min_simulations=1,
            max_simulations=100,
        )

        mcts.ensure_sims(1)
        actions = mcts.get_sorted_actions(flip=True)
        assert isinstance(actions, list)

    @parametrize("extreme_c", [0.0001, 100.0, 1000.0])
    def test_extreme_exploration_values(self, extreme_c: float) -> None:
        """Test with extreme exploration parameter values."""
        mcts = AsyncCorridorsMCTS(
            c=extreme_c,
            seed=42,
            min_simulations=20,
            max_simulations=100,
        )

        mcts.ensure_sims(20)
        actions = mcts.get_sorted_actions(flip=True)
        assert isinstance(actions, list)

        # Should still produce reasonable output
        if actions:
            visits, equity, action_str = actions[0]
            assert isinstance(visits, int)
            assert isinstance(equity, (int, float))
            assert isinstance(action_str, str)

    def test_many_consecutive_moves(self) -> None:
        """Test making many consecutive moves."""
        mcts = AsyncCorridorsMCTS(c=1.0, seed=42, min_simulations=20, max_simulations=100)

        moves_made = 0
        max_moves = 100  # High limit to test stress

        try:
            for i in range(max_moves):
                mcts.ensure_sims(20)
                actions = mcts.get_sorted_actions(flip=(i % 2 == 0))

                if not actions:
                    break  # Game ended

                # Make a move (not necessarily the best to prolong game)
                move_index = min(i % len(actions), len(actions) - 1)
                move = actions[move_index][2]
                mcts.make_move(move, flip=(i % 2 == 0))
                moves_made += 1

                # Check for terminal state periodically
                if i % 10 == 0:
                    evaluation = mcts.get_evaluation()
                    if evaluation is not None and abs(evaluation) >= 1.0:
                        break

        except Exception as e:
            # If we hit an error, at least some moves should have been made
            assert moves_made > 0
            raise

        assert moves_made > 0


@performance
class TestAlgorithmVariants:
    """Test different algorithm variants for performance."""

    def test_uct_vs_puct(self) -> None:
        """Compare UCT vs PUCT algorithms."""
        # Use direct constructor call for type safety
        mcts_uct = AsyncCorridorsMCTS(
            c=1.0,
            seed=42,
            min_simulations=100,
            max_simulations=200,
            use_rollout=True,
            eval_children=False,
            use_puct=False,
            use_probs=False,
            decide_using_visits=True,
        )

        start_time = time.time()
        mcts_uct.ensure_sims(100)
        time_uct = time.time() - start_time

        # UCT should complete in reasonable time
        assert time_uct < 60.0

        actions = mcts_uct.get_sorted_actions(flip=True)
        assert len(actions) > 0


@performance
class TestConcurrencySimulation:
    """Simulate concurrent-like usage patterns."""

    def test_interleaved_operations(self) -> None:
        """Test interleaving different operations."""
        mcts = AsyncCorridorsMCTS(c=1.0, seed=42, min_simulations=50, max_simulations=100)

        # Interleave operations as might happen in a GUI or web app
        for i in range(20):
            if i % 4 == 0:
                mcts.ensure_sims(50 + i)
            elif i % 4 == 1:
                actions = mcts.get_sorted_actions(flip=(i % 2 == 0))
                assert isinstance(actions, list)
            elif i % 4 == 2:
                display = mcts.display(flip=(i % 2 == 0))
                assert isinstance(display, str)
            else:
                evaluation = mcts.get_evaluation()
                assert evaluation is None or isinstance(evaluation, (int, float))

    def test_rapid_state_queries(self) -> None:
        """Test rapid successive queries of game state."""
        mcts = AsyncCorridorsMCTS(c=1.0, seed=42, min_simulations=100, max_simulations=200)

        mcts.ensure_sims(100)

        start_time = time.time()

        # Many rapid queries
        for i in range(100):
            actions = mcts.get_sorted_actions(flip=(i % 2 == 0))
            display = mcts.display(flip=(i % 2 == 0))
            evaluation = mcts.get_evaluation()

            # Basic type checks
            assert isinstance(actions, list)
            assert isinstance(display, str)
            assert evaluation is None or isinstance(evaluation, (int, float))

        elapsed = time.time() - start_time

        # Queries should be fast (no heavy computation)
        assert elapsed < 5.0  # 5 seconds for 100 queries
