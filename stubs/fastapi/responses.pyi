"""Type stubs for FastAPI responses."""

from typing import Optional, Dict

class FileResponse:
    def __init__(
        self,
        path: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> None: ...
