"""Type stubs for pytest."""

from typing import (
    TypeVar,
    Callable,
    Union,
    Generator,
    Iterator,
    Optional,
    Dict,
    List,
    Any,
    overload,
    Type,
    NoReturn,
)

T = TypeVar("T")
F = TypeVar("F")
C = TypeVar("C")

class FixtureFunction:
    def __call__(self, func: F) -> F: ...

@overload
def fixture(func: F) -> F: ...
@overload
def fixture(
    func: None = None,
    *,
    scope: str = "function",
    params: Optional[List[object]] = None,
    autouse: bool = False,
    ids: Optional[List[str]] = None,
    name: Optional[str] = None,
) -> Callable[[F], F]: ...

class MarkDecorator:
    def __call__(self, target: object) -> object: ...
    def parametrize(
        self,
        argnames: Union[str, List[str]],
        argvalues: Union[List[object], List[tuple[object, ...]]],
        indirect: Union[bool, List[str]] = False,
        ids: Optional[Union[List[str], Callable[[object], str]]] = None,
        scope: Optional[str] = None,
    ) -> "MarkDecorator": ...

    # Allow chaining with other marks
    def __getattr__(self, name: str) -> "MarkDecorator": ...

class _MarkRegistry:
    def __getattr__(self, name: str) -> MarkDecorator: ...
    def parametrize(
        self,
        argnames: str,
        argvalues: List[object],
        indirect: bool = False,
        ids: Optional[List[str]] = None,
        scope: Optional[str] = None,
    ) -> MarkDecorator: ...

    # Standard marks
    parametrize: MarkDecorator
    skip: MarkDecorator
    skipif: MarkDecorator
    xfail: MarkDecorator
    filterwarnings: MarkDecorator

    # Custom marks - all return MarkDecorator
    performance: MarkDecorator
    slow: MarkDecorator
    asyncio: MarkDecorator
    benchmark: MarkDecorator
    stress: MarkDecorator
    edge_cases: MarkDecorator
    unit: MarkDecorator
    integration: MarkDecorator
    cpp: MarkDecorator
    python: MarkDecorator
    display: MarkDecorator
    mcts: MarkDecorator
    board: MarkDecorator
    api: MarkDecorator
    websocket: MarkDecorator
    game_manager: MarkDecorator
    models: MarkDecorator
    endpoints: MarkDecorator

mark: _MarkRegistry = ...

class MonkeyPatch:
    def setattr(
        self,
        target: Union[str, object],
        name: Union[str, object],
        value: object = ...,
        raising: bool = True,
    ) -> None: ...
    def delattr(
        self,
        target: Union[str, object],
        name: Union[str, object] = ...,
        raising: bool = True,
    ) -> None: ...

def approx(
    expected: Union[float, int],
    rel: Optional[float] = None,
    abs: Optional[float] = None,
) -> float: ...

class RaisesContext:
    def __enter__(self) -> "ExceptionInfo[Exception]": ...
    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> bool: ...

def raises(
    expected_exception: Type[Exception], *, match: Optional[str] = None
) -> RaisesContext: ...

class ExceptionInfo(Generator[None, None, None]):
    def __init__(self, excinfo: tuple[type, Exception, object]) -> None: ...
    def __enter__(self) -> "ExceptionInfo[Exception]": ...
    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> bool: ...

def fail(msg: str = "", pytrace: bool = True) -> NoReturn: ...
def skip(msg: str = "") -> NoReturn: ...

# Export key items
__all__ = [
    "fixture",
    "mark",
    "raises",
    "approx",
    "fail",
    "skip",
    "MonkeyPatch",
    "MarkDecorator",
]
