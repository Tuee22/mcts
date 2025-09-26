"""
Functional configuration for game cleanup with automatic test detection.

This module provides immutable configuration types and environment detection
for the automatic game cleanup system.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Final


class RunMode(Enum):
    """Runtime mode detection for cleanup configuration."""

    TEST = "test"
    PRODUCTION = "production"


@dataclass(frozen=True)
class CleanupConfig:
    """Immutable cleanup configuration based on runtime environment."""

    mode: RunMode
    inactivity_timeout: int  # seconds until game considered inactive
    cleanup_interval: int  # seconds between cleanup checks

    @classmethod
    def from_environment(cls) -> CleanupConfig:
        """
        Create config based on automatic environment detection.

        Uses PYTEST_CURRENT_TEST to distinguish test vs production mode.
        """
        mode = (
            RunMode.TEST
            if os.environ.get("PYTEST_CURRENT_TEST")
            else RunMode.PRODUCTION
        )

        # Test mode: aggressive cleanup for resource efficiency
        # Production mode: conservative cleanup to avoid interrupting games
        timeout, interval = (
            (60, 10) if mode == RunMode.TEST else (3600, 60)  # (timeout, interval)
        )

        return cls(mode=mode, inactivity_timeout=timeout, cleanup_interval=interval)

    @property
    def is_test_mode(self) -> bool:
        """Check if running in test mode."""
        return self.mode == RunMode.TEST

    @property
    def is_production_mode(self) -> bool:
        """Check if running in production mode."""
        return self.mode == RunMode.PRODUCTION


# Constants for timeout values
TEST_TIMEOUT: Final[int] = 60  # 1 minute for tests
PRODUCTION_TIMEOUT: Final[int] = 3600  # 1 hour for production
TEST_INTERVAL: Final[int] = 10  # 10 seconds for test mode
PRODUCTION_INTERVAL: Final[int] = 60  # 1 minute for production mode
