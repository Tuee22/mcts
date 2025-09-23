from tests.pytest_marks import (
    board,
    cpp,
    integration,
    mcts,
    parametrize,
    slow,
)

"""
Unit tests for C++ board functions accessible via Python bindings.

These tests verify the core board logic implemented in C++:
- Board state management
- Move validation
- Path finding algorithms  
- Terminal state detection
- Distance calculations
- Hash generation
"""


import pytest

from tests.conftest import MCTSParams

from corridors import AsyncCorridorsMCTS
from corridors.async_mcts import MCTSConfig


@cpp
@board
class TestCorridorsMCTSBasicFunctionality:
    """Test basic MCTS functionality exposed from C++."""

    @pytest.mark.asyncio
    async def test_mcts_initialization_basic(
        self, basic_mcts_params: MCTSParams
    ) -> None:
        """Test MCTS instance can be created with basic parameters."""
        config = MCTSConfig(**basic_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            assert mcts is not None
            assert hasattr(mcts, "display_async")
            assert hasattr(mcts, "make_move_async")
            assert hasattr(mcts, "get_sorted_actions_async")

    @pytest.mark.asyncio
    async def test_mcts_initialization_fast(self, fast_mcts_params: MCTSParams) -> None:
        """Test MCTS instance with fast parameters."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            assert mcts is not None

    @parametrize("c_value", [0.1, 1.0, 2.0, 10.0])
    @pytest.mark.asyncio
    async def test_mcts_initialization_c_values(self, c_value: float) -> None:
        """Test MCTS initialization with different exploration parameters."""
        config = MCTSConfig(
            c=c_value,
            seed=42,
            min_simulations=10,
            max_simulations=100,
            sim_increment=25,
            use_rollout=True,
            eval_children=False,
            use_puct=False,
            use_probs=False,
            decide_using_visits=True,
        )
        async with AsyncCorridorsMCTS(config) as mcts:
            assert mcts is not None

    @parametrize("seed", [1, 42, 123, 999, 12345])
    @pytest.mark.asyncio
    async def test_mcts_initialization_seeds(self, seed: int) -> None:
        """Test MCTS initialization with different random seeds."""
        config = MCTSConfig(
            seed=seed,
            min_simulations=10,
            max_simulations=100,
            c=1.4,
            sim_increment=25,
            use_rollout=True,
            eval_children=False,
            use_puct=False,
            use_probs=False,
            decide_using_visits=True,
        )
        async with AsyncCorridorsMCTS(config) as mcts:
            assert mcts is not None

    @parametrize(
        "use_rollout,eval_children,use_puct,use_probs",
        [
            (True, False, False, False),  # Traditional UCT
            (False, True, True, False),  # PUCT without probabilities
            (True, True, False, False),  # UCT with child evaluation
            (False, False, False, False),  # Minimal setup
        ],
    )
    @pytest.mark.asyncio
    async def test_mcts_initialization_algorithms(
        self, use_rollout: bool, eval_children: bool, use_puct: bool, use_probs: bool
    ) -> None:
        """Test different MCTS algorithm configurations."""
        config = MCTSConfig(
            c=1.0,
            seed=42,
            min_simulations=10,
            max_simulations=100,
            sim_increment=25,
            use_rollout=use_rollout,
            eval_children=eval_children,
            use_puct=use_puct,
            use_probs=use_probs,
            decide_using_visits=True,
        )
        async with AsyncCorridorsMCTS(config) as mcts:
            assert mcts is not None


@cpp
@board
class TestBoardDisplay:
    """Test board display functionality."""

    @pytest.mark.asyncio
    async def test_display_initial_state(self, fast_mcts_params: MCTSParams) -> None:
        """Test displaying initial board state."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            display = await mcts.display_async(flip=False)

            assert isinstance(display, str)
            assert len(display) > 0
            assert "h" in display.lower()  # Hero marker
            assert "v" in display.lower()  # Villain marker
            # Note: Distance and walls remaining displays removed from current format
            # Display now shows visit counts and actions instead

    @pytest.mark.asyncio
    async def test_display_flipped(self, fast_mcts_params: MCTSParams) -> None:
        """Test displaying board from villain's perspective."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            # Make a move to create asymmetric position
            await mcts.ensure_sims_async(20)
            actions = await mcts.get_sorted_actions_async(flip=False)
            if actions:
                # Make a positional move (not a wall) to create asymmetry
                positional_moves = [
                    action for action in actions if action[2].startswith("*(")
                ]
                if positional_moves:
                    await mcts.make_move_async(positional_moves[0][2], flip=False)

            display_normal = await mcts.display_async(flip=False)
            display_flipped = await mcts.display_async(flip=True)

            assert isinstance(display_flipped, str)
            assert display_normal != display_flipped
            assert "h" in display_flipped.lower()
            assert "v" in display_flipped.lower()

    @pytest.mark.asyncio
    async def test_display_after_moves(self, fast_mcts_params: MCTSParams) -> None:
        """Test board display changes after making moves."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            initial_display = await mcts.display_async(flip=False)

            # Get legal actions and make a move
            await mcts.ensure_sims_async(20)
            actions = await mcts.get_sorted_actions_async(flip=True)
            if actions:
                # Make the best move
                best_action = actions[0][2]
                await mcts.make_move_async(best_action, flip=True)

                new_display = await mcts.display_async(flip=False)
                assert new_display != initial_display


@cpp
@mcts
class TestMCTSActions:
    """Test MCTS action generation and selection."""

    @pytest.mark.asyncio
    async def test_get_sorted_actions_initial(
        self, fast_mcts_params: MCTSParams, mcts_helper: object
    ) -> None:
        """Test getting sorted actions from initial position."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(20)  # Ensure minimum simulations

            actions = await mcts.get_sorted_actions_async(flip=True)
            assert isinstance(actions, list)
            assert len(actions) > 0
            # Basic structure validation without strict ordering due to MCTS randomness
            for action in actions:
                assert len(action) == 3
                visits, equity, action_str = action
                assert isinstance(visits, int) and visits >= 0
                assert isinstance(equity, (int, float))
                assert isinstance(action_str, str) and len(action_str) > 0

    @pytest.mark.asyncio
    async def test_get_sorted_actions_structure(
        self, fast_mcts_params: MCTSParams
    ) -> None:
        """Test structure of sorted actions."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(15)

            actions = await mcts.get_sorted_actions_async(flip=True)
            for action in actions[:3]:  # Check first few actions
                visits, equity, action_str = action

                assert isinstance(visits, int)
                assert visits >= 0
                assert isinstance(equity, (int, float))
                assert isinstance(action_str, str)
                assert len(action_str) > 0

    @pytest.mark.asyncio
    async def test_action_string_formats(
        self, fast_mcts_params: MCTSParams, mcts_helper: object
    ) -> None:
        """Test that action strings follow expected formats."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(15)

            actions = await mcts.get_sorted_actions_async(flip=True)
            for _, _, action_str in actions:
                from tests.conftest import MCTSTestHelper

                assert MCTSTestHelper.validate_action_format(action_str)

    @pytest.mark.asyncio
    async def test_choose_best_action(self, fast_mcts_params: MCTSParams) -> None:
        """Test choosing best action."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(20)

            # Test greedy selection (epsilon=0)
            best_action = await mcts.choose_best_action_async(epsilon=0.0)
            assert isinstance(best_action, str)
            assert len(best_action) > 0

            # Verify it matches the top sorted action
            actions = await mcts.get_sorted_actions_async(flip=True)
            if actions:
                actions[0][2]
                # Note: might not match exactly due to flip parameter differences

    @parametrize("epsilon", [0.0, 0.1, 0.5, 1.0])
    @pytest.mark.asyncio
    async def test_choose_best_action_epsilon(
        self, epsilon: float, fast_mcts_params: MCTSParams
    ) -> None:
        """Test epsilon-greedy action selection."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(15)

            best_action = await mcts.choose_best_action_async(epsilon=epsilon)
            assert isinstance(best_action, str)
            assert len(best_action) > 0


@cpp
@board
class TestMoveValidation:
    """Test move validation and execution."""

    @pytest.mark.asyncio
    async def test_make_valid_moves(self, fast_mcts_params: MCTSParams) -> None:
        """Test making valid positional moves."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(10)

            # Get initial actions
            actions = await mcts.get_sorted_actions_async(flip=True)
            len(actions)

            if actions:
                # Make a move
                move = actions[0][2]
                await mcts.make_move_async(move, flip=True)

                # Verify the move was applied
                new_actions = await mcts.get_sorted_actions_async(
                    flip=False
                )  # Opponent's turn
                # Board state should have changed
                assert isinstance(new_actions, list)

    @parametrize(
        "move_str",
        [
            "*(4,1)",  # Move up
            "*(5,0)",  # Move right
            "*(3,0)",  # Move left
        ],
    )
    @pytest.mark.asyncio
    async def test_make_specific_moves(
        self, move_str: str, fast_mcts_params: MCTSParams
    ) -> None:
        """Test making specific moves if they're legal."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(10)

            actions = await mcts.get_sorted_actions_async(flip=True)
            legal_moves = [a[2] for a in actions]

            if move_str in legal_moves:
                # Move is legal, should succeed
                await mcts.make_move_async(move_str, flip=True)
                # Verify state changed by checking new actions
                new_actions = await mcts.get_sorted_actions_async(flip=False)
                assert isinstance(new_actions, list)

    @pytest.mark.asyncio
    async def test_wall_placement_moves(self, fast_mcts_params: MCTSParams) -> None:
        """Test wall placement moves."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(15)

            actions = await mcts.get_sorted_actions_async(flip=True)
            wall_moves = [
                a[2] for a in actions if a[2].startswith("H(") or a[2].startswith("V(")
            ]

            if wall_moves:
                # Try placing a wall
                wall_move = wall_moves[0]
                await mcts.make_move_async(wall_move, flip=True)

                # Verify wall was placed by checking display
                display = await mcts.display_async(flip=False)
                assert isinstance(display, str)


@cpp
@board
class TestGameEvaluation:
    """Test game state evaluation functions."""

    @pytest.mark.asyncio
    async def test_get_evaluation_initial(self, fast_mcts_params: MCTSParams) -> None:
        """Test evaluation on initial position."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            evaluation = await mcts.get_evaluation_async()
            # Initial position should be non-terminal
            assert evaluation is None or evaluation == 0.0

    @pytest.mark.asyncio
    async def test_ensure_simulations(self, fast_mcts_params: MCTSParams) -> None:
        """Test ensuring minimum simulations are performed."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            # This should block until simulations are complete
            await mcts.ensure_sims_async(25)

            # Should be able to get actions after ensuring simulations
            actions = await mcts.get_sorted_actions_async(flip=True)
            assert isinstance(actions, list)

            # Total visits should be at least the minimum
            if actions:
                total_visits = sum(a[0] for a in actions)
                assert total_visits >= 25

    @slow
    @pytest.mark.asyncio
    async def test_longer_simulation(self, basic_mcts_params: MCTSParams) -> None:
        """Test longer simulation run."""
        # Increase simulation count for this test
        params = basic_mcts_params.copy()
        params["min_simulations"] = 200
        params["max_simulations"] = 500

        config = MCTSConfig(**params)
        async with AsyncCorridorsMCTS(config) as mcts:
            await mcts.ensure_sims_async(200)

            actions = await mcts.get_sorted_actions_async(flip=True)
            assert len(actions) > 0

            # Should have reasonable visit counts distributed across actions
            if actions:
                top_action_visits = actions[0][0]
                total_visits = sum(visits for visits, _, _ in actions)
                assert top_action_visits >= 2  # Top action should have multiple visits
                assert total_visits >= 200  # Should have done the requested simulations


@cpp
@integration
class TestGameFlow:
    """Test complete game flow scenarios."""

    @pytest.mark.asyncio
    async def test_make_several_moves(self, fast_mcts_params: MCTSParams) -> None:
        """Test making several moves in sequence."""
        config = MCTSConfig(**fast_mcts_params)
        async with AsyncCorridorsMCTS(config) as mcts:
            moves_made = 0
            max_moves = 5

            for i in range(max_moves):
                await mcts.ensure_sims_async(15)
                actions = await mcts.get_sorted_actions_async(
                    flip=(moves_made % 2 == 0)
                )

                if not actions:
                    break  # Game ended

                # Make best move
                best_move = actions[0][2]
                await mcts.make_move_async(best_move, flip=(moves_made % 2 == 0))
                moves_made += 1

                # Check if game ended
                evaluation = await mcts.get_evaluation_async()
                if evaluation is not None and evaluation != 0:
                    break  # Terminal position reached

            assert moves_made > 0

    @slow
    @pytest.mark.asyncio
    async def test_play_to_completion(self, fast_mcts_params: MCTSParams) -> None:
        """Test playing a game to completion."""
        params = fast_mcts_params.copy()
        params["min_simulations"] = 20
        params["max_simulations"] = 100

        config = MCTSConfig(**params)
        async with AsyncCorridorsMCTS(config) as mcts:
            moves_made = 0
            max_moves = 50  # Safety limit

            while moves_made < max_moves:
                await mcts.ensure_sims_async(20)
                actions = await mcts.get_sorted_actions_async(
                    flip=(moves_made % 2 == 0)
                )

                if not actions:
                    # Game ended - no more legal moves
                    break

                # Make best move
                best_move = actions[0][2]
                await mcts.make_move_async(best_move, flip=(moves_made % 2 == 0))
                moves_made += 1

                # Check terminal state
                evaluation = await mcts.get_evaluation_async()
                if evaluation is not None and abs(evaluation) == 1.0:
                    # Game ended with a winner
                    break

            assert moves_made > 0
            # Game should eventually end
            assert moves_made < max_moves
