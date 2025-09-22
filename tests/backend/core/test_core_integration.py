from tests.pytest_marks import (
    cpp,
    display,
    integration,
    parametrize,
    performance,
    slow,
)

"""
Integration tests for the complete MCTS system.

These tests verify that all components work together correctly:
- End-to-end game scenarios
- Python-C++ integration
- Real gameplay simulation
- System behavior under realistic conditions
"""

import time
from typing import Dict, List, Tuple

import pytest

from corridors import AsyncCorridorsMCTS
from corridors.async_mcts import MCTSConfig


@integration
@slow
class TestCompleteGameScenarios:
    """Test complete game scenarios from start to finish."""

    @pytest.mark.asyncio
    async def test_full_computer_self_play(self) -> None:
        """Test a complete computer self-play game."""
        # Use reasonable parameters for a full game
        p1_config = MCTSConfig(
            c=1.4,
            seed=123,
            min_simulations=100,
            max_simulations=500,
            sim_increment=50,
            use_rollout=True,
            eval_children=False,
            use_puct=False,
            use_probs=False,
            decide_using_visits=True,
        )
        p2_config = MCTSConfig(
            c=1.4,
            seed=456,  # Different seed for variation
            min_simulations=100,
            max_simulations=500,
            sim_increment=50,
            use_rollout=True,
            eval_children=False,
            use_puct=False,
            use_probs=False,
            decide_using_visits=True,
        )
        async with AsyncCorridorsMCTS(p1_config) as p1, AsyncCorridorsMCTS(
            p2_config
        ) as p2:
            moves_made = []
            game_states = []

            # Ensure initial simulations
            await p1.ensure_sims_async(100)
            await p2.ensure_sims_async(100)

            # Track game progression
            is_hero_turn = True
            max_moves = 200  # Safety limit (increased for more complex games)

            for move_count in range(max_moves):
                current_player = p1 if is_hero_turn else p2
                other_player = p2 if is_hero_turn else p1

                # Get current board state
                display = await current_player.display_async(flip=not is_hero_turn)
                game_states.append(display)

                # Get available actions
                actions = await current_player.get_sorted_actions_async(
                    flip=is_hero_turn
                )

                if not actions:
                    # Game ended - no legal moves
                    break

                # Choose best action
                best_action = actions[0][2]
                moves_made.append(
                    (move_count, is_hero_turn, best_action, actions[0][0])
                )  # move, player, action, visits

                # Make move on both boards
                await current_player.make_move_async(best_action, flip=is_hero_turn)
                await other_player.make_move_async(best_action, flip=is_hero_turn)

                # Ensure simulations for both players after move
                await current_player.ensure_sims_async(50)
                await other_player.ensure_sims_async(50)

                # Check for terminal state
                evaluation = await current_player.get_evaluation_async()
                if evaluation is not None and abs(evaluation) >= 0.95:
                    winner = "Hero" if (evaluation > 0) == is_hero_turn else "Villain"
                    break

                # Switch players
                is_hero_turn = not is_hero_turn

            # Verify game completed properly
            assert len(moves_made) > 0, "No moves were made"
            assert len(moves_made) < max_moves, "Game didn't end within move limit"
            assert len(game_states) > 0, "No game states recorded"

            # Verify move quality - actions should have reasonable visit counts
            for move_num, player, action, visits in moves_made[
                :10
            ]:  # Check first 10 moves
                assert (
                    visits >= 1
                ), f"Move {move_num} had no visits: {visits}"  # More realistic expectation

            print(f"Game completed in {len(moves_made)} moves")

    @pytest.mark.asyncio
    async def test_single_player_game_to_completion(self) -> None:
        """Test a single-player game played to completion."""
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
            move_sequence = []
            max_moves = 200  # Increase limit for corridors games which can be longer

            for move_num in range(max_moves):
                # Ensure adequate simulations
                await mcts.ensure_sims_async(150)

                # Get game state
                actions = await mcts.get_sorted_actions_async(flip=(move_num % 2 == 0))

                if not actions:
                    # Game ended
                    break

                # Record move details
                best_action = actions[0]
                move_sequence.append(
                    {
                        "move": move_num,
                        "player": "Hero" if move_num % 2 == 0 else "Villain",
                        "action": best_action[2],
                        "visits": best_action[0],
                        "equity": best_action[1],
                        "total_actions": len(actions),
                    }
                )

                # Make the move
                await mcts.make_move_async(best_action[2], flip=(move_num % 2 == 0))

                # Check if the game is actually terminal
                # Don't rely on evaluation alone - check if there are legal moves remaining
                # and use the C++ terminal detection
                if await mcts.is_terminal_async():
                    evaluation = await mcts.get_evaluation_async()
                    if evaluation is not None:
                        winner = "Hero" if evaluation > 0 else "Villain"
                        if move_num % 2 != 0:  # Adjust for perspective
                            winner = "Villain" if winner == "Hero" else "Hero"
                    break

            assert (
                len(move_sequence) > 5
            ), f"Game ended too quickly after {len(move_sequence)} moves"
            assert (
                len(move_sequence) < max_moves
            ), f"Game didn't complete within {max_moves} moves (got {len(move_sequence)} moves)"

            # Verify game progression makes sense
            for i, move_data in enumerate(move_sequence):
                visits = move_data["visits"]
                total_actions = move_data["total_actions"]
                assert (
                    isinstance(visits, int) and visits > 0
                ), f"Move {i} had zero visits"
                assert isinstance(
                    move_data["equity"], (int, float)
                ), f"Move {i} had invalid equity"
                assert (
                    isinstance(total_actions, int) and total_actions > 0
                ), f"Move {i} had no available actions"

    @parametrize(
        "algorithm_params",
        [
            {"use_rollout": True, "eval_children": False, "use_puct": False},
            {"use_rollout": True, "eval_children": True, "use_puct": False},
            # Note: use_rollout=False requires custom eval function which is not implemented
            # Add more algorithm variations as they become available
        ],
    )
    @pytest.mark.asyncio
    async def test_different_algorithms_complete_games(
        self, algorithm_params: Dict[str, bool]
    ) -> None:
        """Test that different algorithm configurations can complete games."""
        config = MCTSConfig(
            c=1.2,
            seed=999,
            min_simulations=80,
            max_simulations=200,
            sim_increment=40,
            use_rollout=algorithm_params.get("use_rollout", True),
            eval_children=algorithm_params.get("eval_children", False),
            use_puct=algorithm_params.get("use_puct", False),
            use_probs=algorithm_params.get("use_probs", False),
            decide_using_visits=algorithm_params.get("decide_using_visits", True),
        )
        async with AsyncCorridorsMCTS(config) as mcts:
            moves_completed = 0
            max_moves = 30  # Shorter test for parameter variations

            for move_num in range(max_moves):
                await mcts.ensure_sims_async(80)
                actions = await mcts.get_sorted_actions_async(flip=(move_num % 2 == 0))

                if not actions:
                    break

                await mcts.make_move_async(actions[0][2], flip=(move_num % 2 == 0))
                moves_completed += 1

                # Early termination check
                if await mcts.get_evaluation_async() is not None:
                    break

            assert moves_completed > 0, f"No moves completed with {algorithm_params}"


@integration
@cpp
class TestCPythonIntegration:
    """Test integration between Python and C++ components."""

    @pytest.mark.asyncio
    async def test_data_type_consistency(self) -> None:
        """Test that data types are consistent across Python-C++ boundary."""
        config = MCTSConfig(c=1.0, seed=42, min_simulations=50, max_simulations=100)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(50)

            # Test display string handling
            display = await mcts.display_async(flip=False)
            assert isinstance(display, str)
            assert len(display) > 0

            # Test action list structure
            actions = await mcts.get_sorted_actions_async(flip=True)
            assert isinstance(actions, list)

            for action in actions[:5]:  # Test first 5 actions
                assert len(action) == 3
                visits, equity, action_str = action

                # Verify types match expectations
                assert isinstance(visits, int)
                assert visits >= 0
                assert isinstance(equity, (int, float))
                assert isinstance(action_str, str)
                assert len(action_str) > 0

    @pytest.mark.asyncio
    async def test_move_execution_consistency(self) -> None:
        """Test that moves are executed consistently between calls."""
        config = MCTSConfig(c=1.0, seed=111, min_simulations=30, max_simulations=100)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(30)

            # Get initial state
            initial_display = await mcts.display_async(flip=False)
            initial_actions = await mcts.get_sorted_actions_async(flip=True)

            assert len(initial_actions) > 0

            # Make a move
            move_to_make = initial_actions[0][2]
            await mcts.make_move_async(move_to_make, flip=True)

            # Verify state changed
            new_display = await mcts.display_async(flip=False)
            new_actions = await mcts.get_sorted_actions_async(
                flip=False
            )  # Other player's turn

        assert new_display != initial_display, "Board display should change after move"
        assert isinstance(new_actions, list), "Should get valid actions list"

        # The exact actions may be different due to perspective flip, but should be valid
        for action in new_actions[:3]:
            assert len(action) == 3
            assert isinstance(action[2], str)

    @pytest.mark.asyncio
    async def test_evaluation_function_integration(self) -> None:
        """Test evaluation function returns consistent types."""
        config = MCTSConfig(c=1.0, seed=222, min_simulations=40, max_simulations=100)
        async with AsyncCorridorsMCTS(config) as mcts:
            # Test evaluation at different stages
            initial_eval = await mcts.get_evaluation_async()
            assert initial_eval is None or isinstance(initial_eval, (int, float))

            await mcts.ensure_sims_async(40)

            # Make some moves and check evaluations
            for i in range(5):
                actions = await mcts.get_sorted_actions_async(flip=(i % 2 == 0))
                if not actions:
                    break

                await mcts.make_move_async(actions[0][2], flip=(i % 2 == 0))

                evaluation = await mcts.get_evaluation_async()
                assert evaluation is None or isinstance(evaluation, (int, float))

                if evaluation is not None and abs(evaluation) >= 1.0:
                    # Terminal state reached
                    assert evaluation in [
                        -1.0,
                        1.0,
                    ], f"Terminal evaluation should be ±1.0, got {evaluation}"
                    break


@integration
@performance
class TestRealisticUsagePatterns:
    """Test realistic usage patterns and performance."""

    @pytest.mark.asyncio
    async def test_interactive_session_simulation(self) -> None:
        """Simulate an interactive session with varied queries."""
        config = MCTSConfig(c=1.5, seed=333, min_simulations=100, max_simulations=200)
        async with AsyncCorridorsMCTS(config) as mcts:
            # Simulate user behavior: checking state, making moves, checking again
            session_log = []

            # Initial exploration
            start_time = time.time()
            await mcts.ensure_sims_async(100)
            session_log.append(("ensure_sims", time.time() - start_time))

            for interaction in range(10):
                # User checks current state
                start_time = time.time()
                display = await mcts.display_async(flip=False)
                session_log.append(("display", time.time() - start_time))

                # User gets available actions
                start_time = time.time()
                actions = await mcts.get_sorted_actions_async(
                    flip=(interaction % 2 == 0)
                )
                session_log.append(("get_actions", time.time() - start_time))

                if not actions:
                    break

                # User makes a move (sometimes not the best one)
                move_index = min(interaction % 3, len(actions) - 1)  # Vary move choice
                start_time = time.time()
                await mcts.make_move_async(
                    actions[move_index][2], flip=(interaction % 2 == 0)
                )
                session_log.append(("make_move", time.time() - start_time))

                # User checks evaluation
                start_time = time.time()
                evaluation = await mcts.get_evaluation_async()
                session_log.append(("get_evaluation", time.time() - start_time))

                if evaluation is not None and abs(evaluation) >= 1.0:
                    break

            # Verify performance characteristics
            display_times = [t for op, t in session_log if op == "display"]
            action_times = [t for op, t in session_log if op == "get_actions"]

            if display_times:
                avg_display_time = sum(display_times) / len(display_times)
                assert (
                    avg_display_time < 0.1
                ), f"Display too slow: {avg_display_time}s average"

            if action_times:
                avg_action_time = sum(action_times) / len(action_times)
                assert (
                    avg_action_time < 0.1
                ), f"Get actions too slow: {avg_action_time}s average"

    @pytest.mark.asyncio
    async def test_tournament_style_games(self) -> None:
        """Test multiple games as in a tournament setting."""
        results = []

        for game_num in range(3):  # Play 3 games
            p1_config = MCTSConfig(
                c=1.4,
                seed=100 + game_num,
                min_simulations=80,
                max_simulations=160,
            )
            p2_config = MCTSConfig(
                c=1.4,
                seed=200 + game_num,
                min_simulations=80,
                max_simulations=160,
            )
            async with AsyncCorridorsMCTS(p1_config) as p1, AsyncCorridorsMCTS(
                p2_config
            ) as p2:
                game_result = await self._play_game_async(p1, p2, max_moves=120)
                results.append(game_result)

        # Verify all games completed
        for i, result in enumerate(results):
            moves = result["moves"]
            assert isinstance(moves, int), f"Game {i} moves should be int"
            assert moves > 0, f"Game {i} had no moves"
            assert moves <= 120, f"Game {i} exceeded move limit"
            assert result["winner"] in [
                "Hero",
                "Villain",
                "Incomplete",
            ], f"Game {i} had invalid winner"

        # At least some games should complete
        completed_games = [r for r in results if r["winner"] != "Incomplete"]
        assert len(completed_games) > 0, "No games completed"

    async def _play_game_async(
        self, p1: AsyncCorridorsMCTS, p2: AsyncCorridorsMCTS, max_moves: int
    ) -> Dict[str, str | int | bool]:
        """Helper to play a single game between two MCTS instances."""
        await p1.ensure_sims_async(80)
        await p2.ensure_sims_async(80)

        moves = 0
        is_hero_turn = True

        for move_num in range(max_moves):
            current_player = p1 if is_hero_turn else p2
            other_player = p2 if is_hero_turn else p1

            actions = await current_player.get_sorted_actions_async(flip=is_hero_turn)

            if not actions:
                winner = "Villain" if is_hero_turn else "Hero"
                return {"moves": moves, "winner": winner, "reason": "no_moves"}

            # Make best move
            best_action = actions[0][2]
            await current_player.make_move_async(best_action, flip=is_hero_turn)
            await other_player.make_move_async(best_action, flip=is_hero_turn)

            moves += 1

            # Ensure simulations for evaluation
            await current_player.ensure_sims_async(40)

            # Check terminal state
            evaluation = await current_player.get_evaluation_async()
            if evaluation is not None and abs(evaluation) >= 0.95:
                winner = "Hero" if (evaluation > 0) == is_hero_turn else "Villain"
                return {"moves": moves, "winner": winner, "reason": "terminal"}

            is_hero_turn = not is_hero_turn

        return {"moves": moves, "winner": "Incomplete", "reason": "max_moves"}


@integration
@display
class TestDisplayIntegration:
    """Test display functionality integration."""

    @pytest.mark.asyncio
    async def test_display_consistency_during_game(self) -> None:
        """Test that display remains consistent during game progression."""
        config = MCTSConfig(c=1.0, seed=444, min_simulations=50, max_simulations=100)
        async with AsyncCorridorsMCTS(config) as mcts:
            displays = []

            for move_num in range(8):
                await mcts.ensure_sims_async(50)

                # Capture display from both perspectives
                hero_display = await mcts.display_async(flip=False)
                villain_display = await mcts.display_async(flip=True)

                displays.append(
                    {
                        "move": move_num,
                        "hero_view": hero_display,
                        "villain_view": villain_display,
                    }
                )

                # Verify display properties
                assert isinstance(hero_display, str)
                assert isinstance(villain_display, str)
                assert len(hero_display) > 100, "Display too short"
                assert len(villain_display) > 100, "Display too short"
                assert "h" in hero_display.lower(), "Hero marker missing"
                assert "v" in hero_display.lower(), "Villain marker missing"

                # Make a move
                actions = await mcts.get_sorted_actions_async(flip=(move_num % 2 == 0))
                if not actions:
                    break

                await mcts.make_move_async(actions[0][2], flip=(move_num % 2 == 0))

            # Verify displays change over time
            if len(displays) > 1:
                assert (
                    displays[0]["hero_view"] != displays[-1]["hero_view"]
                ), "Display should change during game"

    @pytest.mark.asyncio
    async def test_action_display_integration(self) -> None:
        """Test integration between action generation and display."""

        # Local utility function for displaying actions
        def display_sorted_actions(actions: List[Tuple[int, float, str]]) -> str:
            """Format sorted actions for display."""
            return "\n".join(
                f"{action}: {visits} visits, {equity:.4f} equity"
                for visits, equity, action in actions
            )

        config = MCTSConfig(c=1.0, seed=555, min_simulations=60, max_simulations=120)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(60)
            actions = await mcts.get_sorted_actions_async(flip=True)

            assert len(actions) > 0

            # Test displaying actions
            display_result = display_sorted_actions(actions)
            assert isinstance(display_result, str)

            # Verify action strings are valid for the current board state
            for visits, equity, action_str in actions[:5]:
                assert isinstance(action_str, str)
                assert len(action_str) > 3, f"Action string too short: {action_str}"

                # Action should be executable (test first few)
                try:
                    config = MCTSConfig(
                        c=1.0, seed=555, min_simulations=10, max_simulations=100
                    )
                    async with AsyncCorridorsMCTS(config) as test_mcts:
                        await test_mcts.ensure_sims_async(10)
                        test_actions = await test_mcts.get_sorted_actions_async(
                            flip=True
                        )

                        if action_str in [a[2] for a in test_actions]:
                            await test_mcts.make_move_async(action_str, flip=True)
                            # Should not raise exception
                except Exception as e:
                    pytest.fail(f"Action {action_str} caused error: {e}")


@integration
@slow
class TestLongRunningScenarios:
    """Test long-running scenarios and stability."""

    @pytest.mark.asyncio
    async def test_extended_simulation_session(self) -> None:
        """Test extended simulation and query session."""
        config = MCTSConfig(c=1.2, seed=666, min_simulations=200, max_simulations=1000)
        async with AsyncCorridorsMCTS(config) as mcts:
            # Extended simulation session
            simulation_targets = [200, 400, 600, 800, 1000]

            for target in simulation_targets:
                start_time = time.time()
                await mcts.ensure_sims_async(target)
                elapsed = time.time() - start_time

                # Should complete in reasonable time
                assert elapsed < 60, f"Simulation to {target} took too long: {elapsed}s"

                # Verify functionality at each stage
                actions = await mcts.get_sorted_actions_async(flip=True)
                assert isinstance(actions, list)

                if actions:
                    total_visits = sum(a[0] for a in actions)
                    # In MCTS, root has one more visit than sum of children
                    # so we expect total_visits to be target-1 or target
                    assert (
                        total_visits >= target - 1
                    ), f"Total visits {total_visits} less than target-1 {target-1}"

            # Make some moves and verify stability
            for i in range(5):
                actions = await mcts.get_sorted_actions_async(flip=(i % 2 == 0))
                if actions:
                    await mcts.make_move_async(actions[0][2], flip=(i % 2 == 0))

                    # Verify system is still stable
                    display = await mcts.display_async(flip=False)
                    assert isinstance(display, str)
                    assert len(display) > 0
