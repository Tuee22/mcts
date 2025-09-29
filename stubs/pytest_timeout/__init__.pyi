"""Type stubs for pytest-timeout package."""

from typing import Literal, Optional, Callable, TypeVar, Union
from types import TracebackType
import pytest

# Timeout method types
TimeoutMethod = Literal["thread", "signal"]

# Generic type for decorated functions
T = TypeVar("T")

# Main timeout decorator - simplified signature to avoid Any
def timeout(
    seconds: float,
    method: TimeoutMethod = "thread",
    func_only: bool = False,
) -> Callable[[T], T]: ...

# Timeout exception
class TimeoutError(Exception):
    """Exception raised when a test times out."""

    def __init__(self, message: str, timeout: float) -> None:
        self.message: str
        self.timeout: float
        super().__init__(message)

# Timeout configuration
class TimeoutConfig:
    def __init__(
        self,
        timeout: Optional[float] = None,
        method: TimeoutMethod = "thread",
        func_only: bool = False,
        disable_debugger_detection: bool = False,
    ) -> None:
        self.timeout: Optional[float]
        self.method: TimeoutMethod
        self.func_only: bool
        self.disable_debugger_detection: bool

# Pytest hooks for timeout functionality
def pytest_timeout_set_timer(item: pytest.Item, timeout: float) -> None: ...
def pytest_timeout_cancel_timer(item: pytest.Item) -> None: ...
def pytest_configure(config: pytest.Config) -> None: ...
def pytest_unconfigure(config: pytest.Config) -> None: ...

# Session timeout functionality
class SessionTimeout:
    def __init__(self, timeout: Optional[float] = None) -> None:
        self.timeout: Optional[float]
    def check_timeout(self) -> bool: ...
    def cancel(self) -> None: ...
