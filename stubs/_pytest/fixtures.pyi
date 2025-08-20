"""Type stubs for _pytest.fixtures."""

from typing import Dict, List, Optional, Union

class FixtureRequest:
    def __init__(self) -> None: ...

class SubRequest:
    def __init__(self) -> None: ...
    param: Union[str, int, bool, Dict[str, Union[str, int, bool]], None]
