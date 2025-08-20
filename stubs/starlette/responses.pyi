"""Type stubs for Starlette responses."""

from typing import Dict, Union, Optional, List

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
