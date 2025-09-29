"""Type stubs for test infrastructure utilities."""

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

T = TypeVar("T")

# Test result types
TestStatus = Literal["passed", "failed", "timeout", "skipped"]
BrowserType = Literal["chromium", "firefox", "webkit"]

class TestResult(NamedTuple):
    """Structured test result with no Any types."""

    name: str
    status: TestStatus
    duration_ms: float
    error_message: Optional[str]
    browser: BrowserType
    timestamp: datetime

class TestMetrics:
    """Test metrics collector - for observability, not skip decisions."""

    def __init__(self, metrics_file: Path) -> None:
        self.metrics_file: Path
        self.results: List[TestResult]
    def record(self, result: TestResult) -> None:
        """Record test result for analysis."""
        ...
    def _persist(self) -> None:
        """Save metrics to JSON file."""
        ...
    def get_slowest_tests(self, count: int = 10) -> List[TestResult]:
        """Get slowest tests for optimization analysis."""
        ...

class TestInfrastructureError(Exception):
    """Infrastructure failures are not test failures."""

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        self.message: str
        self.cause: Optional[Exception]
        super().__init__(message)

# Async timeout wrapper
async def with_timeout(coro: Awaitable[T], timeout: float, operation_name: str) -> T:
    """Wrap async operation with timeout and clear error."""
    ...

# Test timeout helper
def create_timeout_wrapper(
    func: Callable[[object], Awaitable[T]], timeout_seconds: float
) -> Callable[[object], Awaitable[T]]:
    """Create a timeout wrapper for async functions."""
    ...
