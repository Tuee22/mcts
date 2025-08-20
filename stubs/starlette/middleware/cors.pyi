"""Type stubs for starlette.middleware.cors."""

from typing import List, Optional, Union

class CORSMiddleware:
    def __init__(
        self,
        app: object,
        allow_origins: Optional[List[str]] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        allow_credentials: bool = False,
        **kwargs: object,
    ) -> None: ...
