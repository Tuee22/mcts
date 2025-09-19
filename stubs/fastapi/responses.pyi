"""Type stubs for FastAPI responses."""

from typing import Dict, List, Optional, Union

class FileResponse:
    def __init__(
        self,
        path: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> None: ...

class JSONResponse:
    def __init__(
        self,
        content: Union[Dict[str, object], List[object], str, int, float, bool, None],
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ) -> None: ...
