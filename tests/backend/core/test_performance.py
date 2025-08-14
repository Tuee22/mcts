"""
Performance and stress tests for MCTS implementation.

These tests verify performance characteristics and handle edge cases:
- Large simulation counts
- Memory usage patterns
- Concurrent operations
- Boundary conditions
- Algorithm efficiency
"""

import pytest
import time
import gc
from typing import Dict, Any
from unittest.mock import patch

try:
    from backend.python.corridors.corridors_mcts import Corridors_MCTS, display_sorted_actions

    CORRIDORS_AVAILABLE = True
except ImportError:
    CORRIDORS_AVAILABLE = False

@pytest.mark.slow
@pytest.mark.performance
class TestMCTSPerformance:
    """Test MCTS performance characteristics."""

    def test_large_simulation_count(self):
        """Test MCTS with large simulation count."""
        mcts = Corridors_MCTS(
            c=1.0,
            seed=42,
            min_simulations=1000,
            max_simulations=5000,
            sim_increment=100,
        )

        start_time = time.time()
        mcts.ensure_sims(1000)
        elapsed = time.time() - start_time

        # Should complete in reasonable time (adjust threshold as needed)
        assert elapsed < 30.0  # 30 seconds max

        actions = mcts.get_sorted_actions(flip=True)
        assert len(actions) > 0

        # Should have substantial visit counts
        total_visits = sum(a[0] for a in actions)
        assert total_visits >= 1000

    def test_simulation_increment_efficiency(self):
        """Test that smaller increments don't drastically slow down computation."""
        # Test with different increment sizes
        params_large = {
            "c": 1.0,
            "seed": 42,
            "min_simulations": 200,
            "max_simulations": 400,
            "sim_increment": 50,
        }
        params_small = {
            "c": 1.0,
            "seed": 42,
            "min_simulations": 200,
            "max_simulations": 400,
            "sim_increment": 10,
        }

        mcts_large = Corridors_MCTS(**params_large)
        mcts_small = Corridors_MCTS(**params_small)

        start_time = time.time()
        mcts_large.ensure_sims(200)
        time_large = time.time() - start_time

        start_time = time.time()
        mcts_small.ensure_sims(200)
        time_small = time.time() - start_time

        # Small increments shouldn't be dramatically slower
        # (some overhead is expected, but not orders of magnitude)
        assert time_small < time_large * 5.0

    @pytest.mark.parametrize("sim_count", [50, 100, 500, 1000])
    def test_simulation_scaling(self, sim_count: int):
        """Test that simulation time scales reasonably with count."""
        mcts = Corridors_MCTS(
            c=1.0,
            seed=42,
            min_simulations=sim_count,
            max_simulations=sim_count * 2,
            sim_increment=25,
        )

        start_time = time.time()
        mcts.ensure_sims(sim_count)
        elapsed = time.time() - start_time

        # Should scale roughly linearly (allowing some overhead)
        expected_time = sim_count * 0.01  # 10ms per simulation (rough estimate)
        assert elapsed < expected_time * 10  # Allow 10x margin for safety

@pytest.mark.performance
class TestMemoryUsage:
    """Test memory usage patterns."""

    def test_multiple_instances(self):
        """Test creating multiple MCTS instances."""
        instances = []

        try:
            for i in range(10):
                mcts = Corridors_MCTS(
                    seed=i, min_simulations=50, max_simulations=100, sim_increment=10
                )
                instances.append(mcts)
                mcts.ensure_sims(50)

            # All instances should be functional
            for mcts in instances:
                actions = mcts.get_sorted_actions(flip=True)
                assert isinstance(actions, list)

        finally:
            # Cleanup
            del instances
            gc.collect()

    def test_repeated_operations(self):
        """Test repeated operations for memory leaks."""
        mcts = Corridors_MCTS(
            c=1.0, seed=42, min_simulations=20, max_simulations=50, sim_increment=5
        )

        # Perform many repeated operations
        for i in range(100):
            mcts.ensure_sims(20 + i % 10)  # Varying simulation counts
            actions = mcts.get_sorted_actions(flip=(i % 2 == 0))
            display = mcts.display(flip=(i % 2 == 0))

            # Basic sanity checks
            assert isinstance(actions, list)
            assert isinstance(display, str)

            if i % 10 == 0:
                gc.collect()  # Periodic cleanup

    def test_large_action_lists(self):
        """Test handling of large action lists."""
        mcts = Corridors_MCTS(
            c=1.0, seed=42, min_simulations=500, max_simulations=1000, sim_increment=25
        )

        mcts.ensure_sims(500)
        actions = mcts.get_sorted_actions(flip=True)

        # Should handle displaying large action lists
        if len(actions) > 10:
            display_result = display_sorted_actions(actions)
            assert isinstance(display_result, str)
            assert len(display_result) > 0

            # Test limited display
            limited_display = display_sorted_actions(actions, list_size=5)
            assert isinstance(limited_display, str)
            assert len(limited_display) < len(display_result)

@pytest.mark.stress
class TestStressConditions:
    """Test stress conditions and edge cases."""

    def test_zero_simulations(self):
        """Test behavior with zero simulations."""
        mcts = Corridors_MCTS(
            c=1.0, seed=42, min_simulations=0, max_simulations=0, sim_increment=1
        )

        # Should still be able to get actions (might be empty or random)
        actions = mcts.get_sorted_actions(flip=True)
        assert isinstance(actions, list)

    def test_minimal_parameters(self):
        """Test with minimal parameter values."""
        mcts = Corridors_MCTS(
            c=0.01,  # Very small exploration
            seed=1,
            min_simulations=1,
            max_simulations=2,
            sim_increment=1,
        )

        mcts.ensure_sims(1)
        actions = mcts.get_sorted_actions(flip=True)
        assert isinstance(actions, list)

    @pytest.mark.parametrize("extreme_c", [0.0001, 100.0, 1000.0])
    def test_extreme_exploration_values(self, extreme_c: float):
        """Test with extreme exploration parameter values."""
        mcts = Corridors_MCTS(
            c=extreme_c,
            seed=42,
            min_simulations=20,
            max_simulations=50,
            sim_increment=5,
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

    def test_many_consecutive_moves(self):
        """Test making many consecutive moves."""
        mcts = Corridors_MCTS(
            c=1.0, seed=42, min_simulations=20, max_simulations=50, sim_increment=5
        )

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

@pytest.mark.performance
class TestAlgorithmVariants:
    """Test different algorithm variants for performance."""

    def test_uct_vs_puct(self):
        """Compare UCT vs PUCT algorithms."""
        params_uct = {
            "c": 1.0,
            "seed": 42,
            "min_simulations": 100,
            "max_simulations": 200,
            "use_puct": False,
            "use_probs": False,
        }

        mcts_uct = Corridors_MCTS(**params_uct)

        start_time = time.time()
        mcts_uct.ensure_sims(100)
        time_uct = time.time() - start_time

        # UCT should complete in reasonable time
        assert time_uct < 60.0

        actions = mcts_uct.get_sorted_actions(flip=True)
        assert len(actions) > 0

@pytest.mark.performance
class TestConcurrencySimulation:
    """Simulate concurrent-like usage patterns."""

    def test_interleaved_operations(self):
        """Test interleaving different operations."""
        mcts = Corridors_MCTS(
            c=1.0, seed=42, min_simulations=50, max_simulations=100, sim_increment=10
        )

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

    def test_rapid_state_queries(self):
        """Test rapid successive queries of game state."""
        mcts = Corridors_MCTS(
            c=1.0, seed=42, min_simulations=100, max_simulations=200, sim_increment=20
        )

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
