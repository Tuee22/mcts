"""Type stubs for httpx."""

from typing import (
    Dict,
    List,
    Optional,
    Union,
    Callable,
    ContextManager,
    AsyncContextManager,
    Awaitable,
)

class ASGITransport:
    def __init__(self, app: object, **kwargs: object) -> None: ...

class Response:
    def __init__(
        self,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
        content: Optional[bytes] = None,
        text: Optional[str] = None,
        json: Optional[object] = None,
        **kwargs: object,
    ) -> None: ...

    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    url: str

    def json(self) -> object: ...
    def raise_for_status(self) -> None: ...

class Request:
    def __init__(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        content: Optional[Union[str, bytes]] = None,
        data: Optional[Dict[str, object]] = None,
        json: Optional[object] = None,
        **kwargs: object,
    ) -> None: ...

    method: str
    url: str
    headers: Dict[str, str]
    content: Optional[bytes]

class AsyncClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        auth: Optional[object] = None,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = False,
        limits: Optional[object] = None,
        transport: Optional[object] = None,
        **kwargs: object,
    ) -> None: ...
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        auth: Optional[object] = None,
        follow_redirects: Optional[bool] = None,
        timeout: Optional[float] = None,
        **kwargs: object,
    ) -> Response: ...
    async def post(
        self,
        url: str,
        data: Optional[Union[str, bytes, Dict[str, object]]] = None,
        json: Optional[object] = None,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        files: Optional[Dict[str, object]] = None,
        auth: Optional[object] = None,
        follow_redirects: Optional[bool] = None,
        timeout: Optional[float] = None,
        **kwargs: object,
    ) -> Response: ...
    async def put(
        self,
        url: str,
        data: Optional[Union[str, bytes, Dict[str, object]]] = None,
        json: Optional[object] = None,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        files: Optional[Dict[str, object]] = None,
        auth: Optional[object] = None,
        follow_redirects: Optional[bool] = None,
        timeout: Optional[float] = None,
        **kwargs: object,
    ) -> Response: ...
    async def delete(
        self,
        url: str,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        auth: Optional[object] = None,
        follow_redirects: Optional[bool] = None,
        timeout: Optional[float] = None,
        **kwargs: object,
    ) -> Response: ...
    async def options(
        self,
        url: str,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        auth: Optional[object] = None,
        follow_redirects: Optional[bool] = None,
        timeout: Optional[float] = None,
        **kwargs: object,
    ) -> Response: ...
    async def head(
        self,
        url: str,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        auth: Optional[object] = None,
        follow_redirects: Optional[bool] = None,
        timeout: Optional[float] = None,
        **kwargs: object,
    ) -> Response: ...
    async def patch(
        self,
        url: str,
        data: Optional[Union[str, bytes, Dict[str, object]]] = None,
        json: Optional[object] = None,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        files: Optional[Dict[str, object]] = None,
        auth: Optional[object] = None,
        follow_redirects: Optional[bool] = None,
        timeout: Optional[float] = None,
        **kwargs: object,
    ) -> Response: ...
    async def aclose(self) -> None: ...
    async def __aenter__(self) -> "AsyncClient": ...
    async def __aexit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None: ...

class Client:
    def __init__(
        self,
        base_url: Optional[str] = None,
        auth: Optional[object] = None,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = False,
        limits: Optional[object] = None,
        transport: Optional[object] = None,
        **kwargs: object,
    ) -> None: ...
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        auth: Optional[object] = None,
        follow_redirects: Optional[bool] = None,
        timeout: Optional[float] = None,
        **kwargs: object,
    ) -> Response: ...
    def post(
        self,
        url: str,
        data: Optional[Union[str, bytes, Dict[str, object]]] = None,
        json: Optional[object] = None,
        params: Optional[Dict[str, Union[str, int]]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        files: Optional[Dict[str, object]] = None,
        auth: Optional[object] = None,
        follow_redirects: Optional[bool] = None,
        timeout: Optional[float] = None,
        **kwargs: object,
    ) -> Response: ...
    def close(self) -> None: ...
    def __enter__(self) -> "Client": ...
    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None: ...

# Top-level functions
def get(
    url: str,
    params: Optional[Dict[str, Union[str, int]]] = None,
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[object] = None,
    auth: Optional[object] = None,
    follow_redirects: bool = False,
    timeout: Optional[float] = None,
    **kwargs: object,
) -> Response: ...
def post(
    url: str,
    data: Optional[Union[str, bytes, Dict[str, object]]] = None,
    json: Optional[object] = None,
    params: Optional[Dict[str, Union[str, int]]] = None,
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[object] = None,
    files: Optional[Dict[str, object]] = None,
    auth: Optional[object] = None,
    follow_redirects: bool = False,
    timeout: Optional[float] = None,
    **kwargs: object,
) -> Response: ...
