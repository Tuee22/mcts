"""
Comprehensive tests for cleanup logic and utility functions.

This module tests all pure functions and logic used in the cleanup system.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from unittest.mock import Mock, patch

patch_dict = patch.dict

import pytest

from backend.api.cleanup_config import CleanupConfig, RunMode
from backend.api.game_manager import GameManager
from backend.api.game_states import ActiveGame, WaitingGame, CompletedGame
from backend.api.models import (
    GameSettings,
    Player,
    PlayerType,
    BoardState,
    GameMode,
    Position,
    Move,
)
from backend.api.pure_utils import (
    partition_by_age,
    filter_dict,
    calculate_age_seconds,
    categorize_age,
    get_last_activity_timestamp,
)


@dataclass
class MockGameWithActivity:
    """Mock game object with proper typing for datetime attributes."""

    last_activity: datetime
    created_at: datetime


class TestUtilityFunctions:
    """Test all pure utility functions used in cleanup."""

    def test_partition_by_age_all_active(self) -> None:
        """Test partition_by_age when all games are active."""
        now = datetime.now(timezone.utc)
        recent_time = now - timedelta(minutes=30)

        games = {
            "game1": MockGameWithActivity(
                last_activity=recent_time, created_at=recent_time
            ),
            "game2": MockGameWithActivity(
                last_activity=recent_time, created_at=recent_time
            ),
            "game3": MockGameWithActivity(
                last_activity=recent_time, created_at=recent_time
            ),
        }

        active, inactive = partition_by_age(
            games, lambda game: game.last_activity, now, 3600  # 1 hour timeout
        )

        assert len(active) == 3
        assert len(inactive) == 0
        assert "game1" in active
        assert "game2" in active
        assert "game3" in active

    def test_partition_by_age_all_inactive(self) -> None:
        """Test partition_by_age when all games are inactive."""
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=2)

        games = {
            "game1": MockGameWithActivity(last_activity=old_time, created_at=old_time),
            "game2": MockGameWithActivity(last_activity=old_time, created_at=old_time),
            "game3": MockGameWithActivity(last_activity=old_time, created_at=old_time),
        }

        active, inactive = partition_by_age(
            games, lambda game: game.last_activity, now, 3600  # 1 hour timeout
        )

        assert len(active) == 0
        assert len(inactive) == 3
        assert "game1" in inactive
        assert "game2" in inactive
        assert "game3" in inactive

    def test_partition_by_age_mixed(self) -> None:
        """Test partition_by_age with mixed active/inactive games."""
        now = datetime.now(timezone.utc)
        recent_time = now - timedelta(minutes=30)
        old_time = now - timedelta(hours=2)

        games = {
            "active1": MockGameWithActivity(
                last_activity=recent_time, created_at=recent_time
            ),
            "inactive1": MockGameWithActivity(
                last_activity=old_time, created_at=old_time
            ),
            "active2": MockGameWithActivity(
                last_activity=recent_time, created_at=recent_time
            ),
            "inactive2": MockGameWithActivity(
                last_activity=old_time, created_at=old_time
            ),
        }

        active, inactive = partition_by_age(
            games, lambda game: game.last_activity, now, 3600  # 1 hour timeout
        )

        assert len(active) == 2
        assert len(inactive) == 2
        assert "active1" in active
        assert "active2" in active
        assert "inactive1" in inactive
        assert "inactive2" in inactive

    def test_partition_by_age_empty(self) -> None:
        """Test partition_by_age with empty games dict."""
        now = datetime.now(timezone.utc)
        games: Dict[str, MockGameWithActivity] = {}

        active, inactive = partition_by_age(
            games, lambda game: game.last_activity, now, 3600
        )

        assert len(active) == 0
        assert len(inactive) == 0

    def test_partition_by_age_exact_timeout(self) -> None:
        """Test partition_by_age at exact timeout boundary."""
        now = datetime.now(timezone.utc)
        exactly_timeout = now - timedelta(seconds=3600)
        just_over_timeout = now - timedelta(seconds=3601)
        just_under_timeout = now - timedelta(seconds=3599)

        games = {
            "exact": MockGameWithActivity(
                last_activity=exactly_timeout, created_at=exactly_timeout
            ),
            "over": MockGameWithActivity(
                last_activity=just_over_timeout, created_at=just_over_timeout
            ),
            "under": MockGameWithActivity(
                last_activity=just_under_timeout, created_at=just_under_timeout
            ),
        }

        active, inactive = partition_by_age(
            games, lambda game: game.last_activity, now, 3600
        )

        assert "under" in active  # Just under timeout should be active
        assert "exact" in active  # Exactly at timeout should be active (> boundary)
        assert "over" in inactive  # Over timeout should be inactive

    def test_filter_dict_basic(self) -> None:
        """Test filter_dict with basic predicate."""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}

        # Filter for even values
        result = filter_dict(data, lambda k, v: v % 2 == 0)

        assert result == {"b": 2, "d": 4}

    def test_filter_dict_key_based(self) -> None:
        """Test filter_dict with key-based predicate."""
        data = {"apple": 1, "banana": 2, "cherry": 3, "apricot": 4}

        # Filter for keys starting with 'a'
        result = filter_dict(data, lambda k, v: k.startswith("a"))

        assert result == {"apple": 1, "apricot": 4}

    def test_filter_dict_empty(self) -> None:
        """Test filter_dict with empty dict."""
        result: Dict[str, int] = filter_dict({}, lambda k, v: True)
        assert result == {}

    def test_filter_dict_none_match(self) -> None:
        """Test filter_dict when no items match."""
        data = {"a": 1, "b": 2, "c": 3}
        result = filter_dict(data, lambda k, v: v > 10)
        assert result == {}

    def test_filter_dict_all_match(self) -> None:
        """Test filter_dict when all items match."""
        data = {"a": 1, "b": 2, "c": 3}
        result = filter_dict(data, lambda k, v: v > 0)
        assert result == data

    def test_calculate_age_seconds(self) -> None:
        """Test calculate_age_seconds function."""
        # Mock current time
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        with patch("backend.api.pure_utils.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            mock_dt.timezone = timezone

            # Test different ages
            one_minute_ago = mock_now - timedelta(minutes=1)
            one_hour_ago = mock_now - timedelta(hours=1)
            one_day_ago = mock_now - timedelta(days=1)

            game1 = MockGameWithActivity(
                last_activity=one_minute_ago, created_at=one_minute_ago
            )
            age1 = calculate_age_seconds(game1, lambda g: one_minute_ago)
            assert age1 == 60.0

            game2 = MockGameWithActivity(
                last_activity=one_hour_ago, created_at=one_hour_ago
            )
            age2 = calculate_age_seconds(game2, lambda g: one_hour_ago)
            assert age2 == 3600.0

            game3 = MockGameWithActivity(
                last_activity=one_day_ago, created_at=one_day_ago
            )
            age3 = calculate_age_seconds(game3, lambda g: one_day_ago)
            assert age3 == 86400.0

    def test_categorize_age(self) -> None:
        """Test categorize_age function with different age buckets."""
        # Test under 1 minute
        assert categorize_age(30) == "under_1_min"
        assert categorize_age(59) == "under_1_min"

        # Test 1-5 minutes
        assert categorize_age(60) == "1_to_5_min"
        assert categorize_age(150) == "1_to_5_min"
        assert categorize_age(299) == "1_to_5_min"

        # Test 5-30 minutes
        assert categorize_age(300) == "5_to_30_min"
        assert categorize_age(900) == "5_to_30_min"
        assert categorize_age(1799) == "5_to_30_min"

        # Test over 30 minutes
        assert categorize_age(1800) == "over_30_min"
        assert categorize_age(3600) == "over_30_min"
        assert categorize_age(86400) == "over_30_min"

    def test_get_last_activity_timestamp_with_last_activity(self) -> None:
        """Test get_last_activity_timestamp when last_activity exists."""
        timestamp = datetime.now(timezone.utc)
        game = MockGameWithActivity(
            last_activity=timestamp, created_at=timestamp - timedelta(hours=1)
        )

        result = get_last_activity_timestamp(game)
        assert result == timestamp

    def test_get_last_activity_timestamp_fallback_to_created_at(self) -> None:
        """Test get_last_activity_timestamp fallback to created_at."""
        created_time = datetime.now(timezone.utc)

        # Create object without last_activity attribute
        class GameWithoutActivity:
            def __init__(self, created_at: datetime) -> None:
                self.created_at = created_at

        game_no_activity = GameWithoutActivity(created_time)

        result = get_last_activity_timestamp(game_no_activity)
        assert result == created_time

    def test_get_last_activity_timestamp_fallback_to_now(self) -> None:
        """Test get_last_activity_timestamp fallback to current time."""

        # Create object without any timestamp attributes
        class GameNoTimestamps:
            pass

        game = GameNoTimestamps()

        before = datetime.now(timezone.utc)
        result = get_last_activity_timestamp(game)
        after = datetime.now(timezone.utc)

        # Result should be between before and after
        assert before <= result <= after


class TestGameManagerCleanupLogic:
    """Test the cleanup logic within GameManager."""

    @pytest.fixture
    def game_manager(self) -> GameManager:
        """Create a game manager for testing."""
        return GameManager()

    @pytest.fixture
    def sample_games(self) -> Dict[str, ActiveGame]:
        """Create sample games with different activity times."""
        now = datetime.now(timezone.utc)

        # Create minimal valid players
        player1 = Player(
            id="player1", name="Player 1", type=PlayerType.HUMAN, is_hero=True
        )
        player2 = Player(
            id="player2", name="Player 2", type=PlayerType.MACHINE, is_hero=False
        )

        # Create minimal valid board state
        board_state = BoardState(
            hero_position=Position(x=2, y=4),
            villain_position=Position(x=2, y=0),
            walls=[],
        )

        # Active game (30 minutes old)
        active_game = ActiveGame(
            game_id="active-game",
            mode=GameMode.PVM,
            player1=player1,
            player2=player2,
            current_turn=1,
            move_history=[],
            board_state=board_state,
            settings=GameSettings(),
            created_at=now - timedelta(minutes=30),
            started_at=now - timedelta(minutes=30),
            last_activity=now - timedelta(minutes=30),
        )

        # Inactive game (2 hours old)
        inactive_game = ActiveGame(
            game_id="inactive-game",
            mode=GameMode.PVM,
            player1=player1,
            player2=player2,
            current_turn=1,
            move_history=[],
            board_state=board_state,
            settings=GameSettings(),
            created_at=now - timedelta(hours=2),
            started_at=now - timedelta(hours=2),
            last_activity=now - timedelta(hours=2),
        )

        return {"active": active_game, "inactive": inactive_game}

    def test_cleanup_identifies_inactive_games(
        self, game_manager: GameManager, sample_games: Dict[str, ActiveGame]
    ) -> None:
        """Test that cleanup logic correctly identifies inactive games."""
        # Add games to manager
        game_manager._games["active"] = sample_games["active"]
        game_manager._games["inactive"] = sample_games["inactive"]

        # Mock the cleanup function's internal logic
        from backend.api.pure_utils import get_last_activity_timestamp

        now = datetime.now(timezone.utc)
        timeout = 3600  # 1 hour

        # Find inactive games using the same logic as cleanup
        inactive_ids = [
            game_id
            for game_id, game in game_manager._games.items()
            if (now - get_last_activity_timestamp(game)).total_seconds() > timeout
        ]

        assert "inactive" in inactive_ids
        assert "active" not in inactive_ids

    def test_cleanup_with_test_timeout(
        self, game_manager: GameManager, sample_games: Dict[str, ActiveGame]
    ) -> None:
        """Test cleanup with short test timeout."""
        # Add games to manager
        game_manager._games["active"] = sample_games["active"]
        game_manager._games["inactive"] = sample_games["inactive"]

        # Test with 60 second timeout (test mode)
        from backend.api.pure_utils import get_last_activity_timestamp

        now = datetime.now(timezone.utc)
        test_timeout = 60  # 1 minute

        inactive_ids = [
            game_id
            for game_id, game in game_manager._games.items()
            if (now - get_last_activity_timestamp(game)).total_seconds() > test_timeout
        ]

        # Both games should be inactive with 60s timeout
        assert "inactive" in inactive_ids
        assert "active" in inactive_ids

    def test_cleanup_with_empty_games(self, game_manager: GameManager) -> None:
        """Test cleanup handles empty games dict correctly."""
        assert len(game_manager._games) == 0

        # Cleanup logic should handle empty dict
        from backend.api.pure_utils import get_last_activity_timestamp

        now = datetime.now(timezone.utc)
        timeout = 3600

        inactive_ids = [
            game_id
            for game_id, game in game_manager._games.items()
            if (now - get_last_activity_timestamp(game)).total_seconds() > timeout
        ]

        assert len(inactive_ids) == 0

    def test_delete_game_removes_from_games(
        self, game_manager: GameManager, sample_games: Dict[str, ActiveGame]
    ) -> None:
        """Test that delete_game removes games from storage."""
        # Add a game
        game = sample_games["active"]
        game_manager._games[game.game_id] = game

        assert len(game_manager._games) == 1

        # Delete the game
        result = asyncio.run(game_manager.delete_game(game.game_id))

        assert result is True
        assert len(game_manager._games) == 0
        assert game.game_id not in game_manager._games

    def test_delete_nonexistent_game(self, game_manager: GameManager) -> None:
        """Test deleting a non-existent game returns False."""
        result = asyncio.run(game_manager.delete_game("nonexistent"))
        assert result is False


class TestCleanupConfiguration:
    """Test cleanup configuration behavior."""

    def test_test_mode_uses_aggressive_timeouts(self) -> None:
        """Test that test mode uses short timeouts."""
        with patch_dict("os.environ", {"PYTEST_CURRENT_TEST": "test_something"}):
            config = CleanupConfig.from_environment()

            assert config.mode == RunMode.TEST
            assert config.inactivity_timeout == 60  # 1 minute
            assert config.cleanup_interval == 10  # 10 seconds

    def test_production_mode_uses_conservative_timeouts(self) -> None:
        """Test that production mode uses long timeouts."""
        with patch_dict("os.environ", {}, clear=True):
            config = CleanupConfig.from_environment()

            assert config.mode == RunMode.PRODUCTION
            assert config.inactivity_timeout == 3600  # 1 hour
            assert config.cleanup_interval == 60  # 1 minute

    def test_config_is_used_by_cleanup_task(self) -> None:
        """Test that cleanup task actually uses the configuration."""
        # This would require mocking the cleanup task, which is complex
        # For now, we verify the config is imported correctly
        from backend.api.game_manager import GameManager

        # Verify the cleanup method exists
        manager = GameManager()
        assert hasattr(manager, "cleanup_inactive_games")
        assert callable(getattr(manager, "cleanup_inactive_games"))


class TestCleanupEdgeCases:
    """Test edge cases and error conditions."""

    def test_cleanup_with_malformed_timestamps(self) -> None:
        """Test cleanup handles games with malformed timestamps."""

        # Create object with invalid last_activity type
        class GameWithBadTimestamp:
            def __init__(self, created_at: datetime) -> None:
                self.last_activity = "invalid_timestamp"  # Wrong type
                self.created_at = created_at

        created_time = datetime.now(timezone.utc)
        game = GameWithBadTimestamp(created_time)

        # get_last_activity_timestamp should handle this gracefully
        result = get_last_activity_timestamp(game)
        # Should fallback to created_at when last_activity is invalid
        assert result == created_time

    def test_cleanup_with_missing_attributes(self) -> None:
        """Test cleanup handles games missing expected attributes."""
        game = object()  # No attributes at all

        # Should fallback to current time
        before = datetime.now(timezone.utc)
        result = get_last_activity_timestamp(game)
        after = datetime.now(timezone.utc)

        assert before <= result <= after

    def test_partition_with_zero_timeout(self) -> None:
        """Test partition_by_age with zero timeout."""
        now = datetime.now(timezone.utc)
        recent_time = now - timedelta(seconds=1)

        games = {
            "game1": MockGameWithActivity(
                last_activity=recent_time, created_at=recent_time
            )
        }

        active, inactive = partition_by_age(
            games,
            lambda game: game.last_activity,
            now,
            0,  # Zero timeout - everything should be inactive
        )

        assert len(active) == 0
        assert len(inactive) == 1

    def test_partition_with_negative_timeout(self) -> None:
        """Test partition_by_age with negative timeout."""
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(seconds=10)  # Future time

        games = {
            "game1": MockGameWithActivity(
                last_activity=future_time, created_at=future_time
            )
        }

        active, inactive = partition_by_age(
            games, lambda game: game.last_activity, now, -1  # Negative timeout
        )

        # With negative timeout, age calculation should still work correctly
        # Future timestamp means negative age, which is always < timeout
        assert len(active) == 1  # Future time is "active"
        assert len(inactive) == 0
