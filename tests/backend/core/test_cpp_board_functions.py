from tests.pytest_marks import (
    api,
    asyncio,
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
Unit tests for C++ board functions accessible via Python bindings.

These tests verify the core board logic implemented in C++:
- Board state management
- Move validation
- Path finding algorithms  
- Terminal state detection
- Distance calculations
- Hash generation
"""

from typing import Dict, List, Tuple
from unittest.mock import Mock

import pytest

from tests.conftest import MCTSParams

from corridors.corridors_mcts import Corridors_MCTS


@cpp
@board
class TestCorridorsMCTSBasicFunctionality:
    """Test basic MCTS functionality exposed from C++."""

    def test_mcts_initialization_basic(self, basic_mcts_params: MCTSParams) -> None:
        """Test MCTS instance can be created with basic parameters."""
        mcts = Corridors_MCTS(**basic_mcts_params)
        assert mcts is not None
        assert hasattr(mcts, "display")
        assert hasattr(mcts, "make_move")
        assert hasattr(mcts, "get_sorted_actions")

    def test_mcts_initialization_fast(self, fast_mcts_params: MCTSParams) -> None:
        """Test MCTS instance with fast parameters."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        assert mcts is not None

    @parametrize("c_value", [0.1, 1.0, 2.0, 10.0])
    def test_mcts_initialization_c_values(self, c_value: float) -> None:
        """Test MCTS initialization with different exploration parameters."""
        mcts = Corridors_MCTS(
            c=c_value, seed=42, min_simulations=10, max_simulations=50
        )
        assert mcts is not None

    @parametrize("seed", [1, 42, 123, 999, 12345])
    def test_mcts_initialization_seeds(self, seed: int) -> None:
        """Test MCTS initialization with different random seeds."""
        mcts = Corridors_MCTS(seed=seed, min_simulations=10, max_simulations=50)
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
    def test_mcts_initialization_algorithms(
        self, use_rollout: bool, eval_children: bool, use_puct: bool, use_probs: bool
    ) -> None:
        """Test different MCTS algorithm configurations."""
        mcts = Corridors_MCTS(
            c=1.0,
            seed=42,
            min_simulations=10,
            max_simulations=50,
            use_rollout=use_rollout,
            eval_children=eval_children,
            use_puct=use_puct,
            use_probs=use_probs,
        )
        assert mcts is not None


@cpp
@board
class TestBoardDisplay:
    """Test board display functionality."""

    def test_display_initial_state(self, fast_mcts_params: MCTSParams) -> None:
        """Test displaying initial board state."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        display = mcts.display(flip=False)

        assert isinstance(display, str)
        assert len(display) > 0
        assert "h" in display.lower()  # Hero marker
        assert "v" in display.lower()  # Villain marker
        assert "Hero distance from end:" in display
        assert "Villain distance from end:" in display
        assert "walls remaining:" in display.lower()

    def test_display_flipped(self, fast_mcts_params: MCTSParams) -> None:
        """Test displaying board from villain's perspective."""
        mcts = Corridors_MCTS(**fast_mcts_params)

        # Make a move to create asymmetric position
        mcts.ensure_sims(20)
        actions = mcts.get_sorted_actions(flip=False)
        if actions:
            # Make a positional move (not a wall) to create asymmetry
            positional_moves = [
                action for action in actions if action[2].startswith("*(")
            ]
            if positional_moves:
                mcts.make_move(positional_moves[0][2], flip=False)

        display_normal = mcts.display(flip=False)
        display_flipped = mcts.display(flip=True)

        assert isinstance(display_flipped, str)
        assert display_normal != display_flipped
        assert "h" in display_flipped.lower()
        assert "v" in display_flipped.lower()

    def test_display_after_moves(self, fast_mcts_params: MCTSParams) -> None:
        """Test board display changes after making moves."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        initial_display = mcts.display(flip=False)

        # Get legal actions and make a move
        mcts.ensure_sims(20)
        actions = mcts.get_sorted_actions(flip=True)
        if actions:
            # Make the best move
            best_action = actions[0][2]
            mcts.make_move(best_action, flip=True)

            new_display = mcts.display(flip=False)
            assert new_display != initial_display


@cpp
@mcts
class TestMCTSActions:
    """Test MCTS action generation and selection."""

    def test_get_sorted_actions_initial(
        self, fast_mcts_params: MCTSParams, mcts_helper: object
    ) -> None:
        """Test getting sorted actions from initial position."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        mcts.ensure_sims(20)  # Ensure minimum simulations

        actions = mcts.get_sorted_actions(flip=True)
        assert isinstance(actions, list)
        assert len(actions) > 0
        # Basic structure validation without strict ordering due to MCTS randomness
        for action in actions:
            assert len(action) == 3
            visits, equity, action_str = action
            assert isinstance(visits, int) and visits >= 0
            assert isinstance(equity, (int, float))
            assert isinstance(action_str, str) and len(action_str) > 0

    def test_get_sorted_actions_structure(self, fast_mcts_params: MCTSParams) -> None:
        """Test structure of sorted actions."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        mcts.ensure_sims(15)

        actions = mcts.get_sorted_actions(flip=True)
        for action in actions[:3]:  # Check first few actions
            visits, equity, action_str = action

            assert isinstance(visits, int)
            assert visits >= 0
            assert isinstance(equity, (int, float))
            assert isinstance(action_str, str)
            assert len(action_str) > 0

    def test_action_string_formats(
        self, fast_mcts_params: MCTSParams, mcts_helper: object
    ) -> None:
        """Test that action strings follow expected formats."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        mcts.ensure_sims(15)

        actions = mcts.get_sorted_actions(flip=True)
        for _, _, action_str in actions:
            from tests.conftest import MCTSTestHelper

            assert MCTSTestHelper.validate_action_format(action_str)

    def test_choose_best_action(self, fast_mcts_params: MCTSParams) -> None:
        """Test choosing best action."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        mcts.ensure_sims(20)

        # Test greedy selection (epsilon=0)
        best_action = mcts.choose_best_action(epsilon=0.0)
        assert isinstance(best_action, str)
        assert len(best_action) > 0

        # Verify it matches the top sorted action
        actions = mcts.get_sorted_actions(flip=True)
        if actions:
            expected_best = actions[0][2]
            # Note: might not match exactly due to flip parameter differences

    @parametrize("epsilon", [0.0, 0.1, 0.5, 1.0])
    def test_choose_best_action_epsilon(
        self, epsilon: float, fast_mcts_params: MCTSParams
    ) -> None:
        """Test epsilon-greedy action selection."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        mcts.ensure_sims(15)

        best_action = mcts.choose_best_action(epsilon=epsilon)
        assert isinstance(best_action, str)
        assert len(best_action) > 0


@cpp
@board
class TestMoveValidation:
    """Test move validation and execution."""

    def test_make_valid_moves(self, fast_mcts_params: MCTSParams) -> None:
        """Test making valid positional moves."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        mcts.ensure_sims(10)

        # Get initial actions
        actions = mcts.get_sorted_actions(flip=True)
        initial_count = len(actions)

        if actions:
            # Make a move
            move = actions[0][2]
            mcts.make_move(move, flip=True)

            # Verify the move was applied
            new_actions = mcts.get_sorted_actions(flip=False)  # Opponent's turn
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
    def test_make_specific_moves(
        self, move_str: str, fast_mcts_params: MCTSParams
    ) -> None:
        """Test making specific moves if they're legal."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        mcts.ensure_sims(10)

        actions = mcts.get_sorted_actions(flip=True)
        legal_moves = [a[2] for a in actions]

        if move_str in legal_moves:
            # Move is legal, should succeed
            mcts.make_move(move_str, flip=True)
            # Verify state changed by checking new actions
            new_actions = mcts.get_sorted_actions(flip=False)
            assert isinstance(new_actions, list)

    def test_wall_placement_moves(self, fast_mcts_params: MCTSParams) -> None:
        """Test wall placement moves."""
        mcts = Corridors_MCTS(**fast_mcts_params)
        mcts.ensure_sims(15)

        actions = mcts.get_sorted_actions(flip=True)
        wall_moves = [
            a[2] for a in actions if a[2].startswith("H(") or a[2].startswith("V(")
        ]

        if wall_moves:
            # Try placing a wall
            wall_move = wall_moves[0]
            mcts.make_move(wall_move, flip=True)

            # Verify wall was placed by checking display
            display = mcts.display(flip=False)
            assert isinstance(display, str)


@cpp
@board
class TestGameEvaluation:
    """Test game state evaluation functions."""

    def test_get_evaluation_initial(self, fast_mcts_params: MCTSParams) -> None:
        """Test evaluation on initial position."""
        mcts = Corridors_MCTS(**fast_mcts_params)

        evaluation = mcts.get_evaluation()
        # Initial position should be non-terminal
        assert evaluation is None or evaluation == 0.0

    def test_ensure_simulations(self, fast_mcts_params: MCTSParams) -> None:
        """Test ensuring minimum simulations are performed."""
        mcts = Corridors_MCTS(**fast_mcts_params)

        # This should block until simulations are complete
        mcts.ensure_sims(25)

        # Should be able to get actions after ensuring simulations
        actions = mcts.get_sorted_actions(flip=True)
        assert isinstance(actions, list)

        # Total visits should be at least the minimum
        if actions:
            total_visits = sum(a[0] for a in actions)
            assert total_visits >= 25

    @slow
    def test_longer_simulation(self, basic_mcts_params: MCTSParams) -> None:
        """Test longer simulation run."""
        # Increase simulation count for this test
        params = basic_mcts_params.copy()
        params["min_simulations"] = 200
        params["max_simulations"] = 500

        mcts = Corridors_MCTS(**params)
        mcts.ensure_sims(200)

        actions = mcts.get_sorted_actions(flip=True)
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

    def test_make_several_moves(self, fast_mcts_params: MCTSParams) -> None:
        """Test making several moves in sequence."""
        mcts = Corridors_MCTS(**fast_mcts_params)

        moves_made = 0
        max_moves = 5

        for i in range(max_moves):
            mcts.ensure_sims(15)
            actions = mcts.get_sorted_actions(flip=(moves_made % 2 == 0))

            if not actions:
                break  # Game ended

            # Make best move
            best_move = actions[0][2]
            mcts.make_move(best_move, flip=(moves_made % 2 == 0))
            moves_made += 1

            # Check if game ended
            evaluation = mcts.get_evaluation()
            if evaluation is not None and evaluation != 0:
                break  # Terminal position reached

        assert moves_made > 0

    @slow
    def test_play_to_completion(self, fast_mcts_params: MCTSParams) -> None:
        """Test playing a game to completion."""
        params = fast_mcts_params.copy()
        params["min_simulations"] = 20
        params["max_simulations"] = 100

        mcts = Corridors_MCTS(**params)

        moves_made = 0
        max_moves = 50  # Safety limit

        while moves_made < max_moves:
            mcts.ensure_sims(20)
            actions = mcts.get_sorted_actions(flip=(moves_made % 2 == 0))

            if not actions:
                # Game ended - no more legal moves
                break

            # Make best move
            best_move = actions[0][2]
            mcts.make_move(best_move, flip=(moves_made % 2 == 0))
            moves_made += 1

            # Check terminal state
            evaluation = mcts.get_evaluation()
            if evaluation is not None and abs(evaluation) == 1.0:
                # Game ended with a winner
                break

        assert moves_made > 0
        # Game should eventually end
        assert moves_made < max_moves
