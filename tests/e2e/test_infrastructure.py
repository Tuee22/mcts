"""Test infrastructure for E2E tests with type safety."""

from typing import (
    NamedTuple,
    Literal,
    Optional,
    List,
    Dict,
    Awaitable,
    TypeVar,
    Callable,
)
from datetime import datetime
from pathlib import Path
import asyncio
import functools
import json

T = TypeVar("T")


# Type-safe test result structures
class TestResult(NamedTuple):
    """Structured test result with no Any types."""

    name: str
    status: Literal["passed", "failed", "timeout", "skipped"]
    duration_ms: float
    error_message: Optional[str]
    browser: Literal["chromium", "firefox", "webkit"]
    timestamp: datetime


class TestMetrics:
    """Test metrics collector - for observability, not skip decisions."""

    def __init__(self, metrics_file: Path) -> None:
        self.metrics_file = metrics_file
        self.results: List[TestResult] = []

    def record(self, result: TestResult) -> None:
        """Record test result for analysis."""
        self.results.append(result)
        self._persist()

    def _persist(self) -> None:
        """Save metrics to JSON file."""
        data = [
            {
                "name": r.name,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "error_message": r.error_message,
                "browser": r.browser,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in self.results
        ]
        self.metrics_file.write_text(json.dumps(data, indent=2))

    def get_slowest_tests(self, count: int = 10) -> List[TestResult]:
        """Get slowest tests for optimization analysis."""
        return sorted(self.results, key=lambda r: r.duration_ms, reverse=True)[:count]

    def get_failure_rate(self) -> float:
        """Calculate overall failure rate."""
        if not self.results:
            return 0.0
        failed_count = sum(1 for r in self.results if r.status == "failed")
        return failed_count / len(self.results)


class TestInfrastructureError(Exception):
    """Infrastructure failures are not test failures."""

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        self.message = message
        self.cause = cause
        super().__init__(message)


async def with_timeout(coro: Awaitable[T], timeout: float, operation_name: str) -> T:
    """
    Wrap async operation with timeout and clear error.

    This ensures we get clear errors instead of hanging.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError as e:
        raise TestInfrastructureError(
            f"Operation '{operation_name}' exceeded {timeout}s timeout. "
            f"This indicates a test quality issue that needs fixing."
        ) from e


def create_timeout_wrapper(
    func: Callable[[object], Awaitable[T]], timeout_seconds: float
) -> Callable[[object], Awaitable[T]]:
    """Create a timeout wrapper for async functions."""

    @functools.wraps(func)
    async def wrapper(arg: object) -> T:
        return await with_timeout(
            func(arg), timeout=timeout_seconds, operation_name=func.__name__
        )

    return wrapper


# Commonly used selectors to avoid duplication
APP_MAIN_SELECTOR = '[data-testid="app-main"]'
CONNECTION_TEXT_SELECTOR = '[data-testid="connection-text"]'
GAME_BOARD_SELECTOR = '[data-testid="game-board"]'
GAME_SETUP_SELECTOR = '[data-testid="game-setup"]'
