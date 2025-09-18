"""
Dedicated performance benchmarks using pytest-benchmark.

These tests focus purely on wall-clock timing with statistical analysis.
Run with: pytest tests/test_benchmarks.py --benchmark-only
"""

from typing import Dict, List, Tuple

import pytest
from _pytest.config import Config
from pytest_benchmark.plugin import BenchmarkFixture

# Import required modules - tests will fail properly if not available
from corridors import AsyncCorridorsMCTS
import asyncio


def display_sorted_actions(actions: List[Tuple[int, float, str]], list_size: int = None) -> str:
    """Format sorted actions for display."""
    if list_size is not None:
        actions = actions[:list_size]
    
    result = []
    for visits, equity, action in actions:
        result.append(f"{action}: {visits} visits, {equity:.4f} equity")
    return "\n".join(result)


@pytest.mark.benchmark
class TestMCTSBenchmarks:
    """Benchmark core MCTS operations."""

    @pytest.mark.parametrize("sim_count", [100, 500, 1000, 2000])
    def test_simulation_performance(
        self, benchmark: BenchmarkFixture, sim_count: int
    ) -> None:
        """Benchmark MCTS simulation time scaling."""
        mcts = AsyncCorridorsMCTS(
            c=1.4,
            seed=42,
            min_simulations=sim_count,
            max_simulations=sim_count,
            sim_increment=50,
            use_rollout=True,
            eval_children=False,
            use_puct=False,
            use_probs=False,
            decide_using_visits=True
        )

        async def run_simulations() -> List[Tuple[int, float, str]]:
            await mcts.ensure_sims_async(sim_count)
            return await mcts.get_sorted_actions_async(flip=True)

        # Run async function in benchmark
        def run_benchmark():
            return asyncio.run(run_simulations())

        actions = benchmark(run_benchmark)
        assert len(actions) > 0

        # Verify quality - total visits should match simulation count
        total_visits = sum(a[0] for a in actions)
        assert total_visits >= sim_count * 0.9  # Allow some tolerance

    def test_action_retrieval_performance(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark action retrieval speed."""
        mcts = AsyncCorridorsMCTS(
            c=1.4, seed=42, min_simulations=1000, max_simulations=1000,
            sim_increment=50, use_rollout=True, eval_children=False,
            use_puct=False, use_probs=False, decide_using_visits=True
        )
        
        # Pre-compute simulations
        asyncio.run(mcts.ensure_sims_async(1000))

        def get_actions() -> List[Tuple[int, float, str]]:
            return asyncio.run(mcts.get_sorted_actions_async(flip=True))

        actions = benchmark(get_actions)
        assert len(actions) > 0

    def test_display_performance(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark board display generation."""
        mcts = AsyncCorridorsMCTS(
            c=1.4, seed=42, min_simulations=500, max_simulations=500,
            sim_increment=50, use_rollout=True, eval_children=False,
            use_puct=False, use_probs=False, decide_using_visits=True
        )
        asyncio.run(mcts.ensure_sims_async(500))

        def generate_display() -> str:
            return asyncio.run(mcts.display_async(flip=False))

        display = benchmark(generate_display)
        assert isinstance(display, str)
        assert len(display) > 0

    def test_move_execution_performance(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark move execution speed."""

        def execute_moves() -> int:
            mcts = AsyncCorridorsMCTS(
                c=1.4, seed=123, min_simulations=100, max_simulations=100,
                sim_increment=50, use_rollout=True, eval_children=False,
                use_puct=False, use_probs=False, decide_using_visits=True
            )
            asyncio.run(mcts.ensure_sims_async(100))

            moves_made = 0
            for i in range(10):  # Make 10 moves
                actions = asyncio.run(mcts.get_sorted_actions_async(flip=(i % 2 == 0)))
                if not actions:
                    break
                asyncio.run(mcts.make_move_async(actions[0][2], flip=(i % 2 == 0)))
                moves_made += 1

            return moves_made

        moves = benchmark(execute_moves)
        assert moves > 0

    @pytest.mark.parametrize("c_value", [0.1, 1.0, 2.0, 10.0])
    def test_exploration_parameter_impact(
        self, benchmark: BenchmarkFixture, c_value: float
    ) -> None:
        """Benchmark impact of different exploration parameters."""

        def run_with_c() -> List[Tuple[int, float, str]]:
            mcts = AsyncCorridorsMCTS(
                c=c_value,
                seed=42,
                min_simulations=500,
                max_simulations=500,
                sim_increment=50,
                use_rollout=True,
                eval_children=False,
                use_puct=False,
                use_probs=False,
                decide_using_visits=True
            )
            asyncio.run(mcts.ensure_sims_async(500))
            return asyncio.run(mcts.get_sorted_actions_async(flip=True))

        actions = benchmark(run_with_c)
        assert len(actions) > 0

    def test_complete_game_performance(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark complete game from start to finish."""

        def play_complete_game() -> int:
            p1 = AsyncCorridorsMCTS(
                c=1.4, seed=111, min_simulations=200, max_simulations=200,
                sim_increment=50, use_rollout=True, eval_children=False,
                use_puct=False, use_probs=False, decide_using_visits=True
            )
            p2 = AsyncCorridorsMCTS(
                c=1.4, seed=222, min_simulations=200, max_simulations=200,
                sim_increment=50, use_rollout=True, eval_children=False,
                use_puct=False, use_probs=False, decide_using_visits=True
            )

            asyncio.run(p1.ensure_sims_async(200))
            asyncio.run(p2.ensure_sims_async(200))

            moves_made = 0
            is_hero_turn = True

            for move_num in range(100):  # Safety limit
                current_player = p1 if is_hero_turn else p2
                other_player = p2 if is_hero_turn else p1

                actions = asyncio.run(current_player.get_sorted_actions_async(flip=is_hero_turn))
                if not actions:
                    break

                # Make move
                best_action = actions[0][2]
                asyncio.run(current_player.make_move_async(best_action, flip=is_hero_turn))
                asyncio.run(other_player.make_move_async(best_action, flip=is_hero_turn))

                moves_made += 1

                # Check terminal
                evaluation = asyncio.run(current_player.get_evaluation_async())
                if evaluation is not None and abs(evaluation) >= 1.0:
                    break

                is_hero_turn = not is_hero_turn

            return moves_made

        moves = benchmark(play_complete_game)
        assert moves > 5  # Should make reasonable number of moves

    def test_rollout_performance(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark random rollout performance specifically."""

        def run_rollout_simulation() -> int:
            mcts = AsyncCorridorsMCTS(
                c=1.4,
                seed=42,
                min_simulations=500,
                max_simulations=500,
                sim_increment=50,
                use_rollout=True,  # Only test rollouts since eval is not implemented
                eval_children=False,
                use_puct=False,
                use_probs=False,
                decide_using_visits=True,
            )

            asyncio.run(mcts.ensure_sims_async(500))
            actions = asyncio.run(mcts.get_sorted_actions_async(flip=True))

            # Make a few moves to test performance during gameplay
            moves_made = 0
            for i in range(5):
                if actions:
                    asyncio.run(mcts.make_move_async(actions[0][2], flip=(i % 2 == 0)))
                    actions = asyncio.run(mcts.get_sorted_actions_async(flip=(i % 2 == 1)))
                    moves_made += 1
                else:
                    break

            return moves_made

        moves = benchmark(run_rollout_simulation)
        assert moves >= 0

    def test_self_play_benchmark(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark self-play game performance with computer vs computer."""

        def run_self_play() -> int:
            import io
            import sys

            from corridors.corridors_mcts import computer_self_play

            # Capture output to avoid printing during benchmark
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                p1 = AsyncCorridorsMCTS(
                    c=1.4, seed=333, min_simulations=100, max_simulations=100,
                    sim_increment=50, use_rollout=True, eval_children=False,
                    use_puct=False, use_probs=False, decide_using_visits=True
                )
                p2 = AsyncCorridorsMCTS(
                    c=1.4, seed=444, min_simulations=100, max_simulations=100,
                    sim_increment=50, use_rollout=True, eval_children=False,
                    use_puct=False, use_probs=False, decide_using_visits=True
                )

                # Track game state before and after
                initial_actions = len(asyncio.run(p1.get_sorted_actions_async(flip=True)))

                # Run abbreviated self-play (limit moves for benchmark)
                moves_made = 0
                is_hero_turn = True

                asyncio.run(p1.ensure_sims_async(100))
                asyncio.run(p2.ensure_sims_async(100))

                for move_num in range(20):  # Limit to 20 moves for benchmark
                    current_player = p1 if is_hero_turn else p2
                    other_player = p2 if is_hero_turn else p1

                    actions = asyncio.run(current_player.get_sorted_actions_async(flip=is_hero_turn))
                    if not actions:
                        break

                    # Make best move
                    best_action = actions[0][2]
                    asyncio.run(current_player.make_move_async(best_action, flip=is_hero_turn))
                    asyncio.run(other_player.make_move_async(best_action, flip=is_hero_turn))
                    moves_made += 1

                    # Check for game end
                    evaluation = asyncio.run(current_player.get_evaluation_async())
                    if evaluation is not None and abs(evaluation) >= 1.0:
                        break

                    is_hero_turn = not is_hero_turn

                return moves_made

            finally:
                sys.stdout = old_stdout

        moves = benchmark(run_self_play)
        assert moves > 0

    @pytest.mark.parametrize("sim_count", [50, 200, 500])
    def test_random_rollout_scaling(
        self, benchmark: BenchmarkFixture, sim_count: int
    ) -> None:
        """Benchmark random rollout performance at different simulation counts."""

        def run_random_rollouts() -> int:
            mcts = AsyncCorridorsMCTS(
                c=1.4,
                seed=42,
                min_simulations=sim_count,
                max_simulations=sim_count,
                sim_increment=50,
                use_rollout=True,  # Enable random rollouts
                eval_children=False,
                use_puct=False,
                use_probs=False,
                decide_using_visits=True,
            )

            # Run simulations
            asyncio.run(mcts.ensure_sims_async(sim_count))

            # Get actions and make some moves to trigger more rollouts
            actions = asyncio.run(mcts.get_sorted_actions_async(flip=True))
            rollout_moves = 0

            for i in range(3):  # Make 3 moves to generate new rollouts
                if actions:
                    asyncio.run(mcts.make_move_async(actions[0][2], flip=(i % 2 == 0)))
                    # Force more simulations after move
                    asyncio.run(mcts.ensure_sims_async(sim_count // 4))  # Additional sims
                    actions = asyncio.run(mcts.get_sorted_actions_async(flip=(i % 2 == 1)))
                    rollout_moves += 1
                else:
                    break

            return rollout_moves

        moves = benchmark(run_random_rollouts)
        assert moves >= 0


@pytest.mark.benchmark
class TestPythonFunctionBenchmarks:
    """Benchmark pure Python functions."""

    def test_display_sorted_actions_performance(
        self, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark action display formatting."""
        # Create large action list
        actions = [(1000 - i, 0.9 - i * 0.01, f"*(4,{i%9})") for i in range(100)]

        def format_actions() -> str:
            return display_sorted_actions(actions)

        result = benchmark(format_actions)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_display_sorted_actions_scaling(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark display performance with very large action lists."""
        # Simulate a position with many possible moves
        actions = [
            (500 - i, 0.5 + i * 0.001, f"{'HV'[i%2]}({i%8},{i//8%8})")
            for i in range(1000)
        ]

        def format_large_list() -> str:
            return display_sorted_actions(actions, list_size=50)  # Limit display

        result = benchmark(format_large_list)
        assert isinstance(result, str)


# Custom benchmark configuration for this module
def pytest_configure(config: Config) -> None:
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
