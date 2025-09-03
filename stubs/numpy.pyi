"""Type stubs for numpy."""

from typing import List, Optional, Sequence, Tuple, Type, TypeVar, Union

DType = TypeVar("DType")
ScalarValue = Union[int, float, bool, complex, str]

class ndarray:
    def __init__(
        self, shape: Tuple[int, ...], dtype: Optional[Type[ScalarValue]] = None
    ) -> None: ...
    @property
    def shape(self) -> Tuple[int, ...]: ...
    @property
    def dtype(self) -> Type[ScalarValue]: ...
    def tolist(self) -> List[ScalarValue]: ...
    def sum(
        self, axis: Optional[Union[int, Tuple[int, ...]]] = None
    ) -> Union["ndarray", ScalarValue]: ...
    def mean(
        self, axis: Optional[Union[int, Tuple[int, ...]]] = None
    ) -> Union["ndarray", ScalarValue]: ...
    def max(
        self, axis: Optional[Union[int, Tuple[int, ...]]] = None
    ) -> Union["ndarray", ScalarValue]: ...
    def min(
        self, axis: Optional[Union[int, Tuple[int, ...]]] = None
    ) -> Union["ndarray", ScalarValue]: ...

def array(
    object: Union[ScalarValue, Sequence[ScalarValue]], dtype: Optional[Type[ScalarValue]] = None
) -> ndarray: ...
def zeros(
    shape: Union[int, Tuple[int, ...]], dtype: Optional[Type[ScalarValue]] = None
) -> ndarray: ...
def ones(
    shape: Union[int, Tuple[int, ...]], dtype: Optional[Type[ScalarValue]] = None
) -> ndarray: ...
def empty(
    shape: Union[int, Tuple[int, ...]], dtype: Optional[Type[ScalarValue]] = None
) -> ndarray: ...
def arange(
    start: Union[int, float],
    stop: Optional[Union[int, float]] = None,
    step: Union[int, float] = 1,
    dtype: Optional[Type[ScalarValue]] = None,
) -> ndarray: ...
def concatenate(arrays: List[ndarray], axis: Optional[int] = None) -> ndarray: ...
def stack(arrays: List[ndarray], axis: int = 0) -> ndarray: ...

# Data types
int32: Type[int]
int64: Type[int]
float32: Type[float]
float64: Type[float]
bool_: Type[bool]

# Common aliases
int_: Type[int]
float_: Type[float]
