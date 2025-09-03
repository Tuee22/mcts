"""Type stubs for _pytest.python."""

from typing import Optional

from _pytest.config import Config

class Function:
    """Pytest function item."""

    config: Config
    name: str
    nodeid: str

    def __init__(self, **kwargs: object) -> None: ...
