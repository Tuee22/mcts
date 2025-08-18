"""Type stubs for CORS middleware."""
from typing import List, Optional, Union

class CORSMiddleware:
    def __init__(
        self,
        app: object,
        allow_origins: Union[List[str], bool] = False,
        allow_methods: Union[List[str], bool] = False, 
        allow_headers: Union[List[str], bool] = False,
        allow_credentials: bool = False,
        allow_origin_regex: Optional[str] = None,
        expose_headers: Union[List[str], bool] = False,
        max_age: int = 600,
    ) -> None: ...