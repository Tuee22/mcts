"""Type stubs for Starlette responses."""

from typing import Dict, Iterator, List, Optional, Union

class JsonResponse:
    """Special response type that behaves like a dict but supports common operations."""

    def __getitem__(self, key: str) -> "JsonValue": ...
    def __contains__(self, key: str) -> bool: ...

class JsonValue:
    """A JSON value that can be a list, dict, or primitive."""

    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator["JsonValue"]: ...
    def __getitem__(self, key: Union[str, int]) -> "JsonValue": ...
    def __contains__(self, key: object) -> bool: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...

class Response:
    def __init__(
        self,
        content: Union[str, bytes] = b"",
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ) -> None: ...
    status_code: int
    headers: Dict[str, str]
    media_type: Optional[str]
    def json(self) -> JsonResponse: ...

class JSONResponse(Response):
    def __init__(
        self,
        content: Dict[str, Union[str, int, bool, List[str], None]],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> None: ...

class FileResponse(Response):
    def __init__(
        self,
        path: Union[str, object],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> None: ...
