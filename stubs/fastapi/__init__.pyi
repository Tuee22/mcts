"""Type stubs for FastAPI core functionality."""

from typing import Callable, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")

class WebSocket:
    """Type definition for FastAPI WebSocket."""

    async def accept(self) -> None:
        """Accept the WebSocket connection."""
        ...
    async def close(self, code: int = 1000) -> None:
        """Close the WebSocket connection."""
        ...
    async def send_text(self, data: str) -> None:
        """Send text data through the WebSocket."""
        ...
    async def send_json(self, data: object) -> None:
        """Send JSON data through the WebSocket."""
        ...
    async def receive_text(self) -> str:
        """Receive text data from the WebSocket."""
        ...
    async def receive_json(self) -> object:
        """Receive JSON data from the WebSocket."""
        ...

class FastAPI:
    """FastAPI application instance."""

    def __init__(
        self,
        debug: bool = False,
        routes: Optional[List[object]] = None,
        title: str = "FastAPI",
        description: str = "",
        version: str = "0.1.0",
        openapi_url: Optional[str] = "/openapi.json",
        docs_url: Optional[str] = "/docs",
        redoc_url: Optional[str] = "/redoc",
        **kwargs: object,
    ) -> None: ...
    def get(self, path: str, **kwargs: object) -> Callable[[T], T]: ...
    def post(self, path: str, **kwargs: object) -> Callable[[T], T]: ...
    def put(self, path: str, **kwargs: object) -> Callable[[T], T]: ...
    def delete(self, path: str, **kwargs: object) -> Callable[[T], T]: ...
    def patch(self, path: str, **kwargs: object) -> Callable[[T], T]: ...
    def websocket(self, path: str, **kwargs: object) -> Callable[[T], T]: ...
    def middleware(self, middleware_type: str) -> Callable[[T], T]: ...
    def mount(self, path: str, app: object, name: Optional[str] = None) -> None: ...
    def add_middleware(
        self, middleware_class: type[object], **kwargs: object
    ) -> None: ...

class BackgroundTasks:
    """Background task handler."""

    def add_task(
        self, func: Callable[[str], object], *args: object, **kwargs: object
    ) -> None: ...

class Request:
    """HTTP Request object."""

    @property
    def headers(self) -> Dict[str, str]: ...
    @property
    def query_params(self) -> Dict[str, str]: ...
    async def json(self) -> object: ...
    async def body(self) -> bytes: ...

class HTTPException(Exception):
    """HTTP exception for error responses."""

    def __init__(
        self,
        status_code: int,
        detail: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None: ...

class WebSocketDisconnect(Exception):
    """WebSocket disconnection exception."""

    def __init__(self, code: int = 1000) -> None: ...

def Depends(dependency: Optional[Callable[[], object]] = None) -> object:
    """Dependency injection."""
    ...
