"""Type stubs for fastapi.testclient."""

from typing import Callable, ContextManager, Dict, List, Optional, Union

from starlette.responses import Response

class TestClient:
    def __init__(
        self,
        app: object,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: str = "asyncio",
        backend_options: Optional[Dict[str, object]] = None,
        cookies: Optional[object] = None,
        headers: Optional[Dict[str, str]] = None,
        follow_redirects: bool = False,
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
    def put(
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
    def delete(
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
    def patch(
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
    def websocket_connect(
        self,
        url: str,
        subprotocols: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[object] = None,
        auth: Optional[object] = None,
        **kwargs: object,
    ) -> ContextManager[object]: ...
    def __enter__(self) -> "TestClient": ...
    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None: ...
