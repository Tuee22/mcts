"""Type stubs for uvicorn."""

from typing import Union

def run(app: object, **kwargs: Union[str, int, bool]) -> None: ...
