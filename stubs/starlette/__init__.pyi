"""Type stubs for Starlette."""
from typing import Dict, List, Optional, Union, Callable, Awaitable
from .responses import Response


class Request:
    def __init__(self, scope: Dict[str, object]) -> None: ...
    
    @property
    def method(self) -> str: ...
    
    @property
    def url(self) -> object: ...
    
    @property
    def headers(self) -> Dict[str, str]: ...


class Middleware:
    def __init__(self, cls: type, **kwargs: object) -> None: ...


__all__ = ["Request", "Middleware", "Response"]