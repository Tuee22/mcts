"""Type stubs for FastAPI."""

from contextlib import AbstractAsyncContextManager
from typing import (
    Awaitable,
    Callable,
    ContextManager,
    Dict,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
)

from pydantic import BaseModel
from starlette.responses import Response

F = TypeVar("F")
AsyncF = TypeVar("AsyncF")
AppType = TypeVar("AppType")

class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str = ...,
        headers: Optional[Dict[str, str]] = ...,
    ) -> None: ...
    status_code: int
    detail: str
    headers: Optional[Dict[str, str]]

class WebSocket:
    def __init__(
        self,
        scope: Dict[str, str],
        receive: Callable[[], Awaitable[Dict[str, Union[str, bytes]]]],
        send: Callable[[Dict[str, Union[str, bytes]]], Awaitable[None]],
    ) -> None: ...
    async def accept(self) -> None: ...
    async def close(self, code: int = 1000) -> None: ...
    async def receive_text(self) -> str: ...
    async def receive_json(self) -> Dict[str, object]: ...
    async def send_text(self, data: str) -> None: ...
    async def send_json(self, data: object) -> None: ...

class WebSocketDisconnect(Exception):
    def __init__(self, code: int = 1000) -> None: ...
    code: int

class FastAPI:
    def __init__(
        self,
        *,
        debug: bool = False,
        routes: Optional[List[object]] = None,
        title: str = "FastAPI",
        summary: Optional[str] = None,
        description: str = "",
        version: str = "0.1.0",
        openapi_url: Optional[str] = "/openapi.json",
        openapi_tags: Optional[List[Dict[str, object]]] = None,
        servers: Optional[List[Dict[str, Union[object, str]]]] = None,
        dependencies: Optional[List[object]] = None,
        default_response_class: Type[Response] = Response,
        redirect_slashes: bool = True,
        docs_url: Optional[str] = "/docs",
        redoc_url: Optional[str] = "/redoc",
        swagger_ui_oauth2_redirect_url: Optional[str] = "/docs/oauth2-redirect",
        swagger_ui_init_oauth: Optional[Dict[str, object]] = None,
        middleware: Optional[List[object]] = None,
        exception_handlers: Optional[
            Dict[
                Union[int, Type[Exception]],
                Callable[[object, object], Awaitable[Response]],
            ]
        ] = None,
        on_startup: Optional[List[Callable[[], object]]] = None,
        on_shutdown: Optional[List[Callable[[], object]]] = None,
        lifespan: Optional[object] = None,
        terms_of_service: Optional[str] = None,
        contact: Optional[Dict[str, Union[object, str]]] = None,
        license_info: Optional[Dict[str, Union[object, str]]] = None,
        openapi_prefix: str = "",
        root_path: str = "",
        root_path_in_servers: bool = True,
        responses: Optional[Dict[Union[int, str], Dict[str, object]]] = None,
        callbacks: Optional[List[object]] = None,
        webhooks: Optional[object] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        swagger_ui_parameters: Optional[Dict[str, object]] = None,
        generate_unique_id_function: Callable[[object], str] = lambda x: str(id(x)),
        separate_input_output_schemas: bool = True,
        **extra: object,
    ) -> None: ...
    def get(
        self,
        path: str,
        response_model: Optional[Type[BaseModel]] = None,
        **kwargs: object,
    ) -> Callable[[F], F]: ...
    def post(
        self,
        path: str,
        response_model: Optional[Type[BaseModel]] = None,
        **kwargs: object,
    ) -> Callable[[F], F]: ...
    def put(
        self,
        path: str,
        response_model: Optional[Type[BaseModel]] = None,
        **kwargs: object,
    ) -> Callable[[F], F]: ...
    def delete(
        self,
        path: str,
        response_model: Optional[Type[BaseModel]] = None,
        **kwargs: object,
    ) -> Callable[[F], F]: ...
    def websocket(self, path: str, **kwargs: object) -> Callable[[AsyncF], AsyncF]: ...
    def mount(self, path: str, app: object, name: Optional[str] = None) -> None: ...
    def add_middleware(self, middleware_class: object, **kwargs: object) -> None: ...

class Request:
    def __init__(
        self,
        scope: Dict[str, str],
        receive: Callable[[], Awaitable[Dict[str, Union[str, bytes]]]],
        send: Callable[[Dict[str, Union[str, bytes]]], Awaitable[None]],
    ) -> None: ...

class BackgroundTasks:
    def add_task(
        self,
        func: object,
        *args: object,
        **kwargs: object,
    ) -> None: ...

def Depends(
    dependency: Optional[object] = None,
) -> object: ...
