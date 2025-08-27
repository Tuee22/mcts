"""Type stubs for pytest_asyncio library."""
from typing import Callable, TypeVar

F = TypeVar("F")

def fixture(*args: object, **kwargs: object) -> Callable[[F], F]: ...
