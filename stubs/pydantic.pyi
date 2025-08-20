"""Type stubs for pydantic."""

from typing import (
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    ClassVar,
    Callable,
)

T = TypeVar("T", bound="BaseModel")

class BaseModel:
    def __init__(self, **data: object) -> None: ...
    
    @classmethod
    def model_validate(cls: Type[T], obj: object) -> T: ...
    
    @classmethod 
    def model_validate_json(cls: Type[T], json_data: Union[str, bytes]) -> T: ...
    
    def model_dump(
        self,
        include: Optional[Union[set[str], Dict[str, object]]] = None,
        exclude: Optional[Union[set[str], Dict[str, object]]] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
    ) -> Dict[str, object]: ...
    
    def model_dump_json(
        self,
        include: Optional[Union[set[str], Dict[str, object]]] = None,
        exclude: Optional[Union[set[str], Dict[str, object]]] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
    ) -> str: ...
    
    def dict(self, **kwargs: object) -> Dict[str, object]: ...
    def json(self, **kwargs: object) -> str: ...
    
    @classmethod
    def parse_obj(cls: Type[T], obj: object) -> T: ...
    
    @classmethod
    def parse_raw(cls: Type[T], b: Union[str, bytes], **kwargs: object) -> T: ...
    
    @classmethod
    def model_rebuild(cls) -> None: ...
    
    model_config: ClassVar[Dict[str, object]]

class ValidationError(ValueError):
    def __init__(self, errors: List[Dict[str, object]]) -> None: ...
    errors: List[Dict[str, object]]

# Field function with special typing support
FieldT = TypeVar("FieldT")

class FieldInfo:
    def __init__(
        self,
        default: object = ...,
        alias: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        examples: Optional[List[object]] = None,
        exclude: Optional[bool] = None,
        include: Optional[bool] = None,
        discriminator: Optional[str] = None,
        json_schema_extra: Optional[Union[Dict[str, object], object]] = None,
        frozen: Optional[bool] = None,
        validate_default: Optional[bool] = None,
        repr: bool = True,
        init_var: Optional[bool] = None,
        kw_only: Optional[bool] = None,
        pattern: Optional[str] = None,
        strict: Optional[bool] = None,
        gt: Optional[Union[int, float]] = None,
        ge: Optional[Union[int, float]] = None,
        lt: Optional[Union[int, float]] = None,
        le: Optional[Union[int, float]] = None,
        multiple_of: Optional[Union[int, float]] = None,
        allow_inf_nan: Optional[bool] = None,
        max_digits: Optional[int] = None,
        decimal_places: Optional[int] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        **kwargs: object,
    ) -> None: ...
    
    # Allow FieldInfo to be treated as compatible with various types
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...

def Field(
    default: object = ...,
    default_factory: Optional[object] = None,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    examples: Optional[List[object]] = None,
    exclude: Optional[bool] = None,
    include: Optional[bool] = None,
    discriminator: Optional[str] = None,
    json_schema_extra: Optional[Union[Dict[str, object], object]] = None,
    frozen: Optional[bool] = None,
    validate_default: Optional[bool] = None,
    repr: bool = True,
    init_var: Optional[bool] = None,
    kw_only: Optional[bool] = None,
    pattern: Optional[str] = None,
    strict: Optional[bool] = None,
    gt: Optional[Union[int, float]] = None,
    ge: Optional[Union[int, float]] = None,
    lt: Optional[Union[int, float]] = None,
    le: Optional[Union[int, float]] = None,
    multiple_of: Optional[Union[int, float]] = None,
    allow_inf_nan: Optional[bool] = None,
    max_digits: Optional[int] = None,
    decimal_places: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    **kwargs: object,
) -> object: ...

# Common validators
class validator:
    def __init__(
        self,
        *fields: str,
        pre: bool = False,
        each_item: bool = False,
        always: bool = False,
        check_fields: bool = True,
        whole: Optional[bool] = None,
        allow_reuse: bool = False,
    ) -> None: ...
    
    def __call__(self, func: object) -> object: ...

class root_validator:
    def __init__(
        self,
        pre: bool = False,
        skip_on_failure: bool = False,
        allow_reuse: bool = False,
    ) -> None: ...
    
    def __call__(self, func: object) -> object: ...

# Field validators (Pydantic v2 style)
class field_validator:
    def __init__(
        self,
        *fields: str,
        mode: str = "before",
        check_fields: bool = True,
    ) -> None: ...
    
    def __call__(self, func: object) -> object: ...

# Config class
class ConfigDict(Dict[str, object]):
    pass