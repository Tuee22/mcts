"""Type stubs for unittest.mock."""
from typing import TypeVar, Union, Optional, Callable, List, Tuple, Dict, ContextManager, Any, overload, Type
from types import TracebackType

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

class _Call:
    """Represents a call to a mock."""
    def __init__(self, name: Optional[str] = None, parent: Optional[Any] = None) -> None: ...
    def __getitem__(self, key: int) -> Tuple[Any, ...]: ...
    def __iter__(self) -> Any: ...

class MagicMock:
    def __init__(
        self, 
        spec: Optional[Any] = None,
        side_effect: Optional[Union[Exception, Callable[..., Any], List[Any]]] = None,
        return_value: Any = ...,
        wraps: Optional[Any] = None,
        name: Optional[str] = None,
        spec_set: Optional[Any] = None,
        **kwargs: Any
    ) -> None: ...
    def __call__(self, *args: Any, **kwargs: Any) -> 'MagicMock': ...
    def __getattr__(self, name: str) -> 'MagicMock': ...
    def __setattr__(self, name: str, value: Any) -> None: ...
    def __delattr__(self, name: str) -> None: ...
    def __getitem__(self, key: Any) -> 'MagicMock': ...
    def __setitem__(self, key: Any, value: Any) -> None: ...
    def __delitem__(self, key: Any) -> None: ...
    def __iter__(self) -> Any: ...
    def __len__(self) -> int: ...
    def __contains__(self, item: Any) -> bool: ...
    def __enter__(self) -> 'MagicMock': ...
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...
    
    # Attributes
    return_value: Any
    side_effect: Optional[Union[Exception, Callable[..., Any], List[Any]]]
    call_count: int
    call_args: Optional[_Call]
    call_args_list: List[_Call]
    method_calls: List[_Call]
    mock_calls: List[_Call]
    
    # Assert methods
    def assert_called(self) -> None: ...
    def assert_called_once(self) -> None: ...
    def assert_called_with(self, *args: Any, **kwargs: Any) -> None: ...
    def assert_called_once_with(self, *args: Any, **kwargs: Any) -> None: ...
    def assert_not_called(self) -> None: ...
    def assert_any_call(self, *args: Any, **kwargs: Any) -> None: ...
    def assert_has_calls(self, calls: List[_Call], any_order: bool = False) -> None: ...
    def reset_mock(self, visited: Optional[Any] = None, return_value: bool = False, side_effect: bool = False) -> None: ...
    def configure_mock(self, **kwargs: Any) -> None: ...
    def _get_child_mock(self, **kwargs: Any) -> 'MagicMock': ...

Mock = MagicMock

class AsyncMock(MagicMock):
    def __init__(self, spec: Optional[Any] = None, **kwargs: Any) -> None: ...
    async def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

class _patch:
    def __init__(
        self,
        getter: Callable[[], Any],
        attribute: str,
        new: Any = ...,
        spec: Optional[Any] = None,
        create: bool = False,
        spec_set: Optional[Any] = None,
        autospec: Optional[Any] = None,
        new_callable: Optional[Callable[[], Any]] = None,
        **kwargs: Any
    ) -> None: ...
    
    def __enter__(self) -> Any: ...
    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException], 
        exc_tb: Optional[TracebackType]
    ) -> None: ...
    
    @overload
    def __call__(self, func: F) -> F: ...
    @overload
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

def patch(
    target: str,
    new: Any = ...,
    spec: Optional[Any] = None,
    create: bool = False,
    spec_set: Optional[Any] = None,
    autospec: Optional[Any] = None,
    new_callable: Optional[Callable[[], Any]] = None,
    **kwargs: Any
) -> _patch: ...

def patch_object(
    target: Any,
    attribute: str,
    new: Any = ...,
    spec: Optional[Any] = None,
    create: bool = False,
    spec_set: Optional[Any] = None,
    autospec: Optional[Any] = None,
    new_callable: Optional[Callable[[], Any]] = None,
    **kwargs: Any
) -> _patch: ...

class PropertyMock(MagicMock):
    """A mock for properties."""
    def __init__(
        self,
        spec: Optional[Any] = None,
        side_effect: Optional[Union[Exception, Callable[..., Any], List[Any]]] = None,
        return_value: Any = ...,
        name: Optional[str] = None,
        **kwargs: Any
    ) -> None: ...
    def __get__(self, obj: Any, obj_type: Optional[Type[Any]] = None) -> Any: ...
    def __set__(self, obj: Any, value: Any) -> None: ...

def call(*args: Any, **kwargs: Any) -> _Call:
    """Create a _Call object for use with assert_has_calls."""
    ...

# Export all main classes and functions
__all__ = [
    'MagicMock', 'Mock', 'AsyncMock', 'PropertyMock', 
    'patch', 'patch_object', 'call', '_Call'
]