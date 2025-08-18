"""Type stubs for starlette.staticfiles."""
from typing import Union

class StaticFiles:
    def __init__(self, directory: Union[str, object], **kwargs: object) -> None: ...