"""
Dedicated performance benchmarks using pytest-benchmark.

These tests focus purely on wall-clock timing with statistical analysis.
Run with: pytest tests/test_benchmarks.py --benchmark-only
"""

import pytest
from typing import Dict, Any

try:
    from python.corridors.corridors_mcts import Corridors_MCTS, display_sorted_actions

    CORRIDORS_AVAILABLE = True
except ImportError:
    CORRIDORS_AVAILABLE = False


@pytest.mark.benchmark
class TestMCTSBenchmarks:
    """Benchmark core MCTS operations."""

    @pytest.mark.parametrize("sim_count", [100, 500, 1000, 2000])
    def test_simulation_performance(self, benchmark, sim_count: int):
        """Benchmark MCTS simulation time scaling."""
        mcts = Corridors_MCTS(
            c=1.4,
            seed=42,
            min_simulations=sim_count,
            max_simulations=sim_count,
        )

        def run_simulations():
            mcts.ensure_sims(sim_count)
            return mcts.get_sorted_actions(flip=True)

        actions = benchmark(run_simulations)
        assert len(actions) > 0

        # Verify quality - total visits should match simulation count
        total_visits = sum(a[0] for a in actions)
        assert total_visits >= sim_count * 0.9  # Allow some tolerance

    def test_action_retrieval_performance(self, benchmark):
        """Benchmark action retrieval speed."""
        mcts = Corridors_MCTS(
            c=1.4, seed=42, min_simulations=1000, max_simulations=1000
        )
        mcts.ensure_sims(1000)  # Pre-compute

        def get_actions():
            return mcts.get_sorted_actions(flip=True)

        actions = benchmark(get_actions)
        assert len(actions) > 0

    def test_display_performance(self, benchmark):
        """Benchmark board display generation."""
        mcts = Corridors_MCTS(c=1.4, seed=42, min_simulations=500, max_simulations=500)
        mcts.ensure_sims(500)

        def generate_display():
            return mcts.display(flip=False)

        display = benchmark(generate_display)
        assert isinstance(display, str)
        assert len(display) > 0

    def test_move_execution_performance(self, benchmark):
        """Benchmark move execution speed."""

        def execute_moves():
            mcts = Corridors_MCTS(
                c=1.4, seed=123, min_simulations=100, max_simulations=100
            )
            mcts.ensure_sims(100)

            moves_made = 0
            for i in range(10):  # Make 10 moves
                actions = mcts.get_sorted_actions(flip=(i % 2 == 0))
                if not actions:
                    break
                mcts.make_move(actions[0][2], flip=(i % 2 == 0))
                moves_made += 1

            return moves_made

        moves = benchmark(execute_moves)
        assert moves > 0

    @pytest.mark.parametrize("c_value", [0.1, 1.0, 2.0, 10.0])
    def test_exploration_parameter_impact(self, benchmark, c_value: float):
        """Benchmark impact of different exploration parameters."""

        def run_with_c():
            mcts = Corridors_MCTS(
                c=c_value,
                seed=42,
                min_simulations=500,
                max_simulations=500,
            )
            mcts.ensure_sims(500)
            return mcts.get_sorted_actions(flip=True)

        actions = benchmark(run_with_c)
        assert len(actions) > 0

    def test_complete_game_performance(self, benchmark):
        """Benchmark complete game from start to finish."""

        def play_complete_game():
            p1 = Corridors_MCTS(
                c=1.4, seed=111, min_simulations=200, max_simulations=200
            )
            p2 = Corridors_MCTS(
                c=1.4, seed=222, min_simulations=200, max_simulations=200
            )

            p1.ensure_sims(200)
            p2.ensure_sims(200)

            moves_made = 0
            is_hero_turn = True

            for move_num in range(100):  # Safety limit
                current_player = p1 if is_hero_turn else p2
                other_player = p2 if is_hero_turn else p1

                actions = current_player.get_sorted_actions(flip=is_hero_turn)
                if not actions:
                    break

                # Make move
                best_action = actions[0][2]
                current_player.make_move(best_action, flip=is_hero_turn)
                other_player.make_move(best_action, flip=is_hero_turn)

                moves_made += 1

                # Check terminal
                evaluation = current_player.get_evaluation()
                if evaluation is not None and abs(evaluation) >= 1.0:
                    break

                is_hero_turn = not is_hero_turn

            return moves_made

        moves = benchmark(play_complete_game)
        assert moves > 5  # Should make reasonable number of moves

    def test_rollout_performance(self, benchmark):
        """Benchmark random rollout performance specifically."""

        def run_rollout_simulation():
            mcts = Corridors_MCTS(
                c=1.4,
                seed=42,
                min_simulations=500,
                max_simulations=500,
                use_rollout=True,  # Only test rollouts since eval is not implemented
                eval_children=False,
                use_puct=False,
                use_probs=False,
                decide_using_visits=True,
            )

            mcts.ensure_sims(500)
            actions = mcts.get_sorted_actions(flip=True)

            # Make a few moves to test performance during gameplay
            moves_made = 0
            for i in range(5):
                if actions:
                    mcts.make_move(actions[0][2], flip=(i % 2 == 0))
                    actions = mcts.get_sorted_actions(flip=(i % 2 == 1))
                    moves_made += 1
                else:
                    break

            return moves_made

        moves = benchmark(run_rollout_simulation)
        assert moves >= 0

    def test_self_play_benchmark(self, benchmark):
        """Benchmark self-play game performance with computer vs computer."""

        def run_self_play():
            from python.corridors.corridors_mcts import computer_self_play
            import io
            import sys

            # Capture output to avoid printing during benchmark
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                p1 = Corridors_MCTS(
                    c=1.4, seed=333, min_simulations=100, max_simulations=100
                )
                p2 = Corridors_MCTS(
                    c=1.4, seed=444, min_simulations=100, max_simulations=100
                )

                # Track game state before and after
                initial_actions = len(p1.get_sorted_actions(flip=True))

                # Run abbreviated self-play (limit moves for benchmark)
                moves_made = 0
                is_hero_turn = True

                p1.ensure_sims(100)
                p2.ensure_sims(100)

                for move_num in range(20):  # Limit to 20 moves for benchmark
                    current_player = p1 if is_hero_turn else p2
                    other_player = p2 if is_hero_turn else p1

                    actions = current_player.get_sorted_actions(flip=is_hero_turn)
                    if not actions:
                        break

                    # Make best move
                    best_action = actions[0][2]
                    current_player.make_move(best_action, flip=is_hero_turn)
                    other_player.make_move(best_action, flip=is_hero_turn)
                    moves_made += 1

                    # Check for game end
                    evaluation = current_player.get_evaluation()
                    if evaluation is not None and abs(evaluation) >= 1.0:
                        break

                    is_hero_turn = not is_hero_turn

                return moves_made

            finally:
                sys.stdout = old_stdout

        moves = benchmark(run_self_play)
        assert moves > 0

    @pytest.mark.parametrize("sim_count", [50, 200, 500])
    def test_random_rollout_scaling(self, benchmark, sim_count: int):
        """Benchmark random rollout performance at different simulation counts."""

        def run_random_rollouts():
            mcts = Corridors_MCTS(
                c=1.4,
                seed=42,
                min_simulations=sim_count,
                max_simulations=sim_count,
                use_rollout=True,  # Enable random rollouts
                eval_children=False,
                use_puct=False,
                use_probs=False,
                decide_using_visits=True,
            )

            # Run simulations
            mcts.ensure_sims(sim_count)

            # Get actions and make some moves to trigger more rollouts
            actions = mcts.get_sorted_actions(flip=True)
            rollout_moves = 0

            for i in range(3):  # Make 3 moves to generate new rollouts
                if actions:
                    mcts.make_move(actions[0][2], flip=(i % 2 == 0))
                    # Force more simulations after move
                    mcts.ensure_sims(sim_count // 4)  # Additional sims
                    actions = mcts.get_sorted_actions(flip=(i % 2 == 1))
                    rollout_moves += 1
                else:
                    break

            return rollout_moves

        moves = benchmark(run_random_rollouts)
        assert moves >= 0


@pytest.mark.benchmark
class TestPythonFunctionBenchmarks:
    """Benchmark pure Python functions."""

    def test_display_sorted_actions_performance(self, benchmark):
        """Benchmark action display formatting."""
        # Create large action list
        actions = [(1000 - i, 0.9 - i * 0.01, f"*(4,{i%9})") for i in range(100)]

        def format_actions():
            return display_sorted_actions(actions)

        result = benchmark(format_actions)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_display_sorted_actions_scaling(self, benchmark):
        """Benchmark display performance with very large action lists."""
        # Simulate a position with many possible moves
        actions = [
            (500 - i, 0.5 + i * 0.001, f"{'HV'[i%2]}({i%8},{i//8%8})")
            for i in range(1000)
        ]

        def format_large_list():
            return display_sorted_actions(actions, list_size=50)  # Limit display

        result = benchmark(format_large_list)
        assert isinstance(result, str)


# Custom benchmark configuration for this module
def pytest_configure(config):
    """Configure benchmark settings."""
    if hasattr(config, "option") and hasattr(config.option, "benchmark_disable"):
        # Only configure if pytest-benchmark is available
        try:
            import pytest_benchmark

            config.addinivalue_line(
                "markers",
                "benchmark: marks tests as benchmarks (run with --benchmark-only)",
            )
        except ImportError:
            pass
