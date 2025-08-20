"""Type stubs for unittest.mock."""

from types import TracebackType
from typing import (
    Callable,
    ContextManager,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

T = TypeVar("T")
F = TypeVar("F")

class _CallableProtocol(Protocol):
    def __call__(self, *args: object, **kwargs: object) -> object: ...

class _ZeroArgCallableProtocol(Protocol):
    def __call__(self) -> object: ...

class _Call:
    """Represents a call to a mock."""

    def __init__(
        self, name: Optional[str] = None, parent: Optional[object] = None
    ) -> None: ...
    def __getitem__(self, key: int) -> Tuple[object, ...]: ...
    def __iter__(self) -> object: ...

class MagicMock:
    def __init__(
        self,
        spec: Optional[object] = None,
        side_effect: Optional[Union[Exception, _CallableProtocol, List[object]]] = None,
        return_value: object = ...,
        wraps: Optional[object] = None,
        name: Optional[str] = None,
        spec_set: Optional[object] = None,
        **kwargs: object,
    ) -> None: ...
    def __call__(self, *args: object, **kwargs: object) -> "MagicMock": ...
    def __getattr__(self, name: str) -> "MagicMock": ...
    def __setattr__(self, name: str, value: object) -> None: ...
    def __delattr__(self, name: str) -> None: ...
    def __getitem__(self, key: object) -> "MagicMock": ...
    def __setitem__(self, key: object, value: object) -> None: ...
    def __delitem__(self, key: object) -> None: ...
    def __iter__(self) -> object: ...
    def __len__(self) -> int: ...
    def __contains__(self, item: object) -> bool: ...
    def __enter__(self) -> "MagicMock": ...
    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None: ...

    # Attributes
    return_value: object
    side_effect: Optional[Union[Exception, _CallableProtocol, List[object]]]
    call_count: int
    call_args: Optional[_Call]
    call_args_list: List[_Call]
    method_calls: List[_Call]
    mock_calls: List[_Call]

    # Assert methods
    def assert_called(self) -> None: ...
    def assert_called_once(self) -> None: ...
    def assert_called_with(self, *args: object, **kwargs: object) -> None: ...
    def assert_called_once_with(self, *args: object, **kwargs: object) -> None: ...
    def assert_not_called(self) -> None: ...
    def assert_any_call(self, *args: object, **kwargs: object) -> None: ...
    def assert_has_calls(self, calls: List[_Call], any_order: bool = False) -> None: ...
    def reset_mock(
        self,
        visited: Optional[object] = None,
        return_value: bool = False,
        side_effect: bool = False,
    ) -> None: ...
    def configure_mock(self, **kwargs: object) -> None: ...
    def _get_child_mock(self, **kwargs: object) -> "MagicMock": ...

Mock = MagicMock

class AsyncMock(MagicMock):
    def __init__(self, spec: Optional[object] = None, **kwargs: object) -> None: ...
    def __call__(self, *args: object, **kwargs: object) -> "AsyncMock": ...

class _patch:
    def __init__(
        self,
        getter: _ZeroArgCallableProtocol,
        attribute: str,
        new: object = ...,
        spec: Optional[object] = None,
        create: bool = False,
        spec_set: Optional[object] = None,
        autospec: Optional[object] = None,
        new_callable: Optional[_ZeroArgCallableProtocol] = None,
        **kwargs: object,
    ) -> None: ...
    def __enter__(self) -> object: ...
    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None: ...
    @overload
    def __call__(self, func: F) -> F: ...
    @overload
    def __call__(self, *args: object, **kwargs: object) -> object: ...

def patch(
    target: str,
    new: object = ...,
    spec: Optional[object] = None,
    create: bool = False,
    spec_set: Optional[object] = None,
    autospec: Optional[object] = None,
    new_callable: Optional[_ZeroArgCallableProtocol] = None,
    **kwargs: object,
) -> _patch: ...
def patch_object(
    target: object,
    attribute: str,
    new: object = ...,
    spec: Optional[object] = None,
    create: bool = False,
    spec_set: Optional[object] = None,
    autospec: Optional[object] = None,
    new_callable: Optional[_ZeroArgCallableProtocol] = None,
    **kwargs: object,
) -> _patch: ...

class PropertyMock(MagicMock):
    """A mock for properties."""

    def __init__(
        self,
        spec: Optional[object] = None,
        side_effect: Optional[Union[Exception, _CallableProtocol, List[object]]] = None,
        return_value: object = ...,
        name: Optional[str] = None,
        **kwargs: object,
    ) -> None: ...
    def __get__(self, obj: object, obj_type: Optional[Type[object]] = None) -> object: ...
    def __set__(self, obj: object, value: object) -> None: ...

def call(*args: object, **kwargs: object) -> _Call:
    """Create a _Call object for use with assert_has_calls."""
    ...

# Export all main classes and functions
__all__ = [
    "MagicMock",
    "Mock",
    "AsyncMock",
    "PropertyMock",
    "patch",
    "patch_object",
    "call",
    "_Call",
]
