"""Type stubs for pytest to eliminate Any types."""

from typing import (
    Callable,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    TypeVar,
    Union,
)

from _pytest.config import Config
from _pytest.fixtures import FixtureRequest
from _pytest.python import Function

# Type variables
_T = TypeVar("_T")

class MarkDecorator:
    """Pytest mark decorator."""

    def __call__(self, *args: object, **kwargs: object) -> object: ...

class MarkGenerator:
    """Pytest mark generator."""

    def __getattr__(self, name: str) -> MarkDecorator: ...

mark: MarkGenerator

# Fixture decorators
def fixture(
    scope: str = ...,
    params: Optional[List[object]] = ...,
    autouse: bool = ...,
    ids: Optional[Union[List[str], Callable[[object], str]]] = ...,
    name: Optional[str] = ...,
) -> Callable[[Callable[..., _T]], Callable[..., _T]]: ...

# Parametrize decorator
def param(
    *values: object,
    marks: Union[MarkDecorator, List[MarkDecorator]] = ...,
    id: Optional[str] = ...,
) -> object: ...

class Metafunc:
    """Parametrization helper."""

    function: Function
    config: Config

    def parametrize(
        self,
        argnames: Union[str, List[str]],
        argvalues: List[object],
        indirect: bool = ...,
        ids: Optional[List[str]] = ...,
        scope: Optional[str] = ...,
    ) -> None: ...

# Exception types
class Failed(Exception): ...
class Skipped(Exception): ...

def raises(
    expected_exception: Union[type, tuple], *, match: Optional[str] = ...
) -> object: ...
def skip(reason: str = ...) -> None: ...
def fail(reason: str = ..., pytrace: bool = ...) -> None: ...

# Pytest configuration
class Item:
    """Test item."""

    name: str
    config: Config

class Session:
    """Test session."""

    config: Config

def pytest_configure(config: Config) -> None: ...
def pytest_collection_modifyitems(config: Config, items: List[Item]) -> None: ...
def pytest_runtest_setup(item: Item) -> None: ...
