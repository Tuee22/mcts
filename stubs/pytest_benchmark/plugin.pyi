"""Type stubs for pytest-benchmark.plugin."""

from typing import Callable, Optional, TypeVar, Any
from _pytest.config import Config

T = TypeVar("T")

class BenchmarkFixture:
    """Type definition for the benchmark fixture from pytest-benchmark."""

    def __call__(self, func: Callable[[], T]) -> T:
        """Execute a function under benchmark timing."""
        ...
    def pedantic(
        self,
        func: Callable[[], T],
        *,
        rounds: int = ...,
        iterations: int = ...,
        warmup_rounds: int = ...,
    ) -> T:
        """Execute with precise timing control."""
        ...
