"""
Tests for the automatic game cleanup functionality.
"""

import asyncio
import os
import pytest
from unittest.mock import patch_dict
from datetime import datetime, timezone, timedelta

from backend.api.cleanup_config import CleanupConfig, RunMode
from backend.api.game_manager import GameManager
from backend.api.game_states import ActiveGame
from backend.api.models import (
    GameSettings,
    Player,
    PlayerType,
    BoardState,
    GameMode,
    Position,
)


class TestCleanupConfig:
    """Test the cleanup configuration."""

    def test_from_environment_test_mode(self) -> None:
        """Test that test mode is detected correctly."""
        with patch_dict(os.environ, {"PYTEST_CURRENT_TEST": "test_something"}):
            config = CleanupConfig.from_environment()
            assert config.mode == RunMode.TEST
            assert config.inactivity_timeout == 60  # 1 minute
            assert config.cleanup_interval == 10  # 10 seconds

    def test_from_environment_production_mode(self) -> None:
        """Test that production mode is detected correctly."""
        with patch_dict(os.environ, {}, clear=True):
            config = CleanupConfig.from_environment()
            assert config.mode == RunMode.PRODUCTION
            assert config.inactivity_timeout == 3600  # 1 hour
            assert config.cleanup_interval == 60  # 1 minute

    def test_from_environment_empty_pytest_var(self) -> None:
        """Test that empty PYTEST_CURRENT_TEST is treated as production."""
        with patch_dict(os.environ, {"PYTEST_CURRENT_TEST": ""}, clear=True):
            config = CleanupConfig.from_environment()
            assert config.mode == RunMode.PRODUCTION

    def test_from_environment_none_pytest_var(self) -> None:
        """Test that None PYTEST_CURRENT_TEST is treated as production."""
        with patch_dict(os.environ, {}, clear=True):
            # Ensure PYTEST_CURRENT_TEST is not set
            if "PYTEST_CURRENT_TEST" in os.environ:
                del os.environ["PYTEST_CURRENT_TEST"]
            config = CleanupConfig.from_environment()
            assert config.mode == RunMode.PRODUCTION

    def test_properties(self) -> None:
        """Test config properties."""
        test_config = CleanupConfig(RunMode.TEST, 60, 10)
        assert test_config.is_test_mode
        assert not test_config.is_production_mode

        prod_config = CleanupConfig(RunMode.PRODUCTION, 3600, 60)
        assert not prod_config.is_test_mode
        assert prod_config.is_production_mode

    def test_config_immutability(self) -> None:
        """Test that config objects are immutable."""
        config = CleanupConfig(RunMode.TEST, 60, 10)

        # Verify config is frozen by checking the frozen dataclass
        # We can't test assignment directly due to mypy restrictions
        # Instead, verify the dataclass has frozen=True behavior
        assert hasattr(config.__class__, "__dataclass_fields__")
        assert getattr(config.__class__, "__dataclass_params__").frozen

    def test_run_mode_enum_values(self) -> None:
        """Test RunMode enum has correct values."""
        assert RunMode.TEST.value == "test"
        assert RunMode.PRODUCTION.value == "production"

        # Test enum comparison - focus on meaningful comparisons
        assert RunMode.TEST == RunMode.TEST
        assert RunMode.PRODUCTION == RunMode.PRODUCTION
        # Test that enum instances are different
        test_mode = RunMode.TEST
        prod_mode = RunMode.PRODUCTION
        assert test_mode != prod_mode

    def test_config_constants_exist(self) -> None:
        """Test that configuration constants are defined."""
        from backend.api.cleanup_config import (
            TEST_TIMEOUT,
            PRODUCTION_TIMEOUT,
            TEST_INTERVAL,
            PRODUCTION_INTERVAL,
        )

        assert TEST_TIMEOUT == 60
        assert PRODUCTION_TIMEOUT == 3600
        assert TEST_INTERVAL == 10
        assert PRODUCTION_INTERVAL == 60

    def test_config_values_match_constants(self) -> None:
        """Test that config values match the defined constants."""
        test_config = CleanupConfig.from_environment()

        if test_config.is_test_mode:
            from backend.api.cleanup_config import TEST_TIMEOUT, TEST_INTERVAL

            assert test_config.inactivity_timeout == TEST_TIMEOUT
            assert test_config.cleanup_interval == TEST_INTERVAL
        else:
            from backend.api.cleanup_config import (
                PRODUCTION_TIMEOUT,
                PRODUCTION_INTERVAL,
            )

            assert test_config.inactivity_timeout == PRODUCTION_TIMEOUT
            assert test_config.cleanup_interval == PRODUCTION_INTERVAL


class TestGameManagerCleanup:
    """Test the game manager cleanup functionality."""

    def test_cleanup_detects_test_mode(self) -> None:
        """Test that cleanup task detects test mode from environment."""
        # This test runs in pytest, so PYTEST_CURRENT_TEST should be set
        assert os.environ.get("PYTEST_CURRENT_TEST") is not None

        config = CleanupConfig.from_environment()
        assert config.mode == RunMode.TEST
        assert config.inactivity_timeout == 60  # 1 minute for tests

    def test_delete_game_functionality(self) -> None:
        """Test that games can be deleted from the manager."""
        game_manager = GameManager()

        # Create a simple mock game using create_game
        game = asyncio.run(
            game_manager.create_game(
                PlayerType.HUMAN, PlayerType.MACHINE, "Test Player", "AI Player"
            )
        )

        assert len(game_manager._games) == 1

        # Delete game
        result = asyncio.run(game_manager.delete_game(game.game_id))
        assert result is True
        assert len(game_manager._games) == 0

        # Try to delete non-existent game
        result = asyncio.run(game_manager.delete_game("non-existent"))
        assert result is False

    def test_cleanup_configuration_in_tests(self) -> None:
        """Verify cleanup runs with test configuration during tests."""
        config = CleanupConfig.from_environment()

        # In pytest environment, should use test settings
        assert config.mode == RunMode.TEST
        assert config.inactivity_timeout == 60  # 1 minute
        assert config.cleanup_interval == 10  # 10 seconds

        print(
            f"✅ Test mode detected: timeout={config.inactivity_timeout}s, interval={config.cleanup_interval}s"
        )
