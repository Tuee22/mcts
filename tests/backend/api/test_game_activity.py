"""
Tests for game activity tracking functionality.

This module tests that last_activity timestamps are properly updated
throughout the game lifecycle.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, cast
from unittest.mock import patch, AsyncMock

patch_object = patch.object

import pytest

from backend.api.game_manager import GameManager
from backend.api.game_states import ActiveGame, WaitingGame, CompletedGame
from backend.api.game_transitions import process_move_transition, resign_game_transition
from backend.api.models import (
    GameSettings,
    Player,
    PlayerType,
    BoardState,
    GameMode,
    Position,
    Move,
)


class TestGameStateActivityTracking:
    """Test that game states properly track activity."""

    @pytest.fixture
    def sample_player_1(self) -> Player:
        """Create a sample player 1."""
        return Player(
            id="player1", name="Player 1", type=PlayerType.HUMAN, is_hero=True
        )

    @pytest.fixture
    def sample_player_2(self) -> Player:
        """Create a sample player 2."""
        return Player(
            id="player2", name="Player 2", type=PlayerType.MACHINE, is_hero=False
        )

    @pytest.fixture
    def sample_board_state(self) -> BoardState:
        """Create a sample board state."""
        return BoardState(
            hero_position=Position(x=2, y=4),
            villain_position=Position(x=2, y=0),
            walls=[],
        )

    def test_waiting_game_has_last_activity(self) -> None:
        """Test that WaitingGame has last_activity field."""
        now = datetime.now(timezone.utc)

        with patch("backend.api.game_states.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.timezone = timezone

            game = WaitingGame(
                game_id="test-waiting",
                mode=GameMode.PVP,
                settings=GameSettings(),
                created_at=now,
            )

            assert hasattr(game, "last_activity")
            assert game.last_activity == now

    def test_active_game_has_last_activity(
        self,
        sample_player_1: Player,
        sample_player_2: Player,
        sample_board_state: BoardState,
    ) -> None:
        """Test that ActiveGame has last_activity field."""
        now = datetime.now(timezone.utc)

        with patch("backend.api.game_states.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.timezone = timezone

            game = ActiveGame(
                game_id="test-active",
                mode=GameMode.PVM,
                player1=sample_player_1,
                player2=sample_player_2,
                current_turn=1,
                move_history=[],
                board_state=sample_board_state,
                settings=GameSettings(),
                created_at=now,
                started_at=now,
            )

            assert hasattr(game, "last_activity")
            assert game.last_activity == now

    def test_completed_game_has_last_activity(
        self,
        sample_player_1: Player,
        sample_player_2: Player,
        sample_board_state: BoardState,
    ) -> None:
        """Test that CompletedGame has last_activity field."""
        now = datetime.now(timezone.utc)

        with patch("backend.api.game_states.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.timezone = timezone

            game = CompletedGame(
                game_id="test-completed",
                mode=GameMode.PVM,
                player1=sample_player_1,
                player2=sample_player_2,
                move_history=[],
                board_state=sample_board_state,
                winner=1,
                termination_reason="checkmate",
                settings=GameSettings(),
                created_at=now - timedelta(hours=1),
                started_at=now - timedelta(hours=1),
                ended_at=now,
            )

            assert hasattr(game, "last_activity")
            assert game.last_activity == now

    def test_with_updated_activity_creates_new_object(
        self,
        sample_player_1: Player,
        sample_player_2: Player,
        sample_board_state: BoardState,
    ) -> None:
        """Test that with_updated_activity creates a new object."""
        original_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        game = ActiveGame(
            game_id="test-update",
            mode=GameMode.PVM,
            player1=sample_player_1,
            player2=sample_player_2,
            current_turn=1,
            move_history=[],
            board_state=sample_board_state,
            settings=GameSettings(),
            created_at=original_time,
            started_at=original_time,
            last_activity=original_time,
        )

        # Update activity
        updated_game = game.with_updated_activity()

        # Should be different objects
        assert updated_game is not game
        assert id(updated_game) != id(game)

        # Activity should be updated
        assert updated_game.last_activity > original_time

        # Other fields should be unchanged
        assert updated_game.game_id == game.game_id
        assert updated_game.player1 == game.player1
        assert updated_game.player2 == game.player2
        assert updated_game.current_turn == game.current_turn

    def test_with_updated_activity_waiting_game(self) -> None:
        """Test with_updated_activity for WaitingGame."""
        original_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        game = WaitingGame(
            game_id="test-waiting-update",
            mode=GameMode.PVP,
            settings=GameSettings(),
            created_at=original_time,
            last_activity=original_time,
        )

        updated_game = game.with_updated_activity()

        assert updated_game is not game
        assert updated_game.last_activity > original_time
        assert updated_game.game_id == game.game_id
        assert updated_game.mode == game.mode


class TestGameTransitionActivityUpdates:
    """Test that game transitions update activity timestamps."""

    @pytest.fixture
    def sample_active_game(self) -> ActiveGame:
        """Create a sample active game."""
        old_time = datetime.now(timezone.utc) - timedelta(minutes=30)

        player1 = Player(
            id="player1", name="Player 1", type=PlayerType.HUMAN, is_hero=True
        )
        player2 = Player(
            id="player2", name="Player 2", type=PlayerType.MACHINE, is_hero=False
        )

        board_state = BoardState(
            hero_position=Position(x=2, y=4),
            villain_position=Position(x=2, y=0),
            walls=[],
        )

        return ActiveGame(
            game_id="test-transition",
            mode=GameMode.PVM,
            player1=player1,
            player2=player2,
            current_turn=1,
            move_history=[],
            board_state=board_state,
            settings=GameSettings(),
            created_at=old_time,
            started_at=old_time,
            last_activity=old_time,
        )

    def test_move_transition_updates_activity(
        self, sample_active_game: ActiveGame
    ) -> None:
        """Test that processing a move updates last_activity."""
        original_activity = sample_active_game.last_activity

        # Create a new board state for after the move
        new_board_state = BoardState(
            hero_position=Position(x=2, y=3),  # Player moved
            villain_position=Position(x=2, y=0),
            walls=[],
        )

        # Process a move transition
        result = process_move_transition(
            sample_active_game,
            "player1",
            "*(3,2)",  # Move action
            None,  # No evaluation
            ["*(2,2)", "*(3,1)"],  # Next legal moves
            new_board_state,
        )

        # Should have new game state with updated activity
        new_game = result.new_state
        assert isinstance(new_game, ActiveGame)
        assert new_game.last_activity > original_activity

        # Move should be recorded
        assert len(new_game.move_history) == 1
        assert new_game.move_history[0].player_id == "player1"
        assert new_game.move_history[0].action == "*(3,2)"

    def test_resignation_updates_activity(self, sample_active_game: ActiveGame) -> None:
        """Test that resignation updates last_activity."""
        original_activity = sample_active_game.last_activity

        # Process resignation
        result = resign_game_transition(sample_active_game, "player1")

        # Should have completed game with updated activity
        completed_game = result.new_state
        assert isinstance(completed_game, CompletedGame)
        assert completed_game.last_activity > original_activity
        assert completed_game.termination_reason == "resignation"
        assert completed_game.winner == 2  # Player 2 wins when Player 1 resigns

    def test_game_completion_updates_activity(
        self, sample_active_game: ActiveGame
    ) -> None:
        """Test that game completion updates last_activity."""
        original_activity = sample_active_game.last_activity

        # Create a board state indicating game end
        final_board_state = BoardState(
            hero_position=Position(x=2, y=0),  # Player reached end
            villain_position=Position(x=2, y=1),
            walls=[],
        )

        # Process a winning move (no legal moves left)
        result = process_move_transition(
            sample_active_game,
            "player1",
            "*(0,2)",
            1.0,  # Winning evaluation
            [],  # No legal moves left
            final_board_state,
        )

        # Should create completed game with updated activity
        completed_game = result.new_state
        assert isinstance(completed_game, CompletedGame)
        assert completed_game.last_activity > original_activity
        assert completed_game.winner == 1


class TestGameManagerActivityTracking:
    """Test that GameManager properly tracks activity."""

    def test_create_game_sets_initial_activity(self) -> None:
        """Test that creating a game sets initial last_activity."""
        manager = GameManager()

        # Create game
        game = asyncio.run(
            manager.create_game(
                PlayerType.HUMAN, PlayerType.MACHINE, "Test Player", "AI Player"
            )
        )

        # Should have recent last_activity
        now = datetime.now(timezone.utc)
        time_diff = (now - game.last_activity).total_seconds()
        assert time_diff < 5  # Should be within 5 seconds

    def test_make_move_updates_activity(self) -> None:
        """Test that making a move through GameManager updates activity."""
        manager = GameManager()

        # Create game
        game = asyncio.run(
            manager.create_game(
                PlayerType.HUMAN, PlayerType.MACHINE, "Test Player", "AI Player"
            )
        )

        original_activity = game.last_activity

        # Mock the MCTS registry and all required async methods
        with patch_object(manager, "mcts_registry") as mock_registry:
            # Mock the async get method
            mock_mcts = AsyncMock()
            mock_registry.get = AsyncMock(return_value=mock_mcts)

            # Mock all MCTS async methods used in _analyze_game_position
            mock_mcts.make_move_async = AsyncMock()
            mock_mcts.get_evaluation_async = AsyncMock(return_value=None)
            mock_mcts.get_sorted_actions_async = AsyncMock(
                return_value=[(None, None, "*(3,2)"), (None, None, "*(2,3)")]
            )
            mock_mcts.display_async = AsyncMock(return_value="test board display")

            # Make a move using the correct player ID
            # Type narrowing: we know this is an ActiveGame from the create_game call
            assert isinstance(game, ActiveGame)
            current_player = game.get_current_player()
            response = asyncio.run(
                manager.make_move(game.game_id, current_player.id, "*(3,2)")
            )

            # Check that activity was updated
            updated_game = manager._games[game.game_id]
            assert updated_game.last_activity > original_activity


class TestActivityTimestampPrecision:
    """Test timestamp precision and edge cases."""

    def test_activity_timestamps_are_utc(
        self,
        sample_player_1: Optional[Player] = None,
        sample_player_2: Optional[Player] = None,
        sample_board_state: Optional[BoardState] = None,
    ) -> None:
        """Test that all activity timestamps are in UTC."""
        # Create fixtures if not provided
        if not sample_player_1:
            sample_player_1 = Player(
                id="player1", name="Player 1", type=PlayerType.HUMAN, is_hero=True
            )
        if not sample_player_2:
            sample_player_2 = Player(
                id="player2", name="Player 2", type=PlayerType.MACHINE, is_hero=False
            )
        if not sample_board_state:
            sample_board_state = BoardState(
                hero_position=Position(x=2, y=4),
                villain_position=Position(x=2, y=0),
                walls=[],
            )

        game = ActiveGame(
            game_id="test-utc",
            mode=GameMode.PVM,
            player1=sample_player_1,
            player2=sample_player_2,
            current_turn=1,
            move_history=[],
            board_state=sample_board_state,
            settings=GameSettings(),
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
        )

        # Default last_activity should be UTC
        assert game.last_activity.tzinfo == timezone.utc

        # Updated activity should be UTC
        updated_game = game.with_updated_activity()
        assert updated_game.last_activity.tzinfo == timezone.utc

    def test_activity_timestamp_monotonic_increase(self) -> None:
        """Test that activity timestamps always increase."""
        game = WaitingGame(
            game_id="test-monotonic",
            mode=GameMode.PVP,
            settings=GameSettings(),
            created_at=datetime.now(timezone.utc),
        )

        # Get multiple updates in sequence
        updates = []
        for _ in range(5):
            game = game.with_updated_activity()
            updates.append(game.last_activity)

        # Each timestamp should be greater than the previous
        for i in range(1, len(updates)):
            assert updates[i] >= updates[i - 1]

    def test_activity_preserves_other_fields(self) -> None:
        """Test that updating activity preserves all other fields."""
        original_time = datetime.now(timezone.utc) - timedelta(hours=1)

        game = WaitingGame(
            game_id="test-preserve",
            mode=GameMode.PVM,
            settings=GameSettings(board_size=7),
            created_at=original_time,
            last_activity=original_time,
        )

        updated_game = game.with_updated_activity()

        # All non-activity fields should be identical
        assert updated_game.game_id == game.game_id
        assert updated_game.mode == game.mode
        assert updated_game.settings == game.settings
        assert updated_game.created_at == game.created_at

        # Only last_activity should change
        assert updated_game.last_activity != game.last_activity
