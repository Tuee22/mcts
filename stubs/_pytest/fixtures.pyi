"""Type stubs for _pytest.fixtures."""

from typing import Dict, List, Optional, Union

class Item:
    name: str
    rep_call: CallInfo

class CallInfo:
    def __init__(self, result: object = None) -> None: ...
    @property
    def failed(self) -> bool: ...

class FixtureRequest:
    def __init__(self) -> None: ...
    @property
    def node(self) -> Item: ...

class SubRequest:
    def __init__(self) -> None: ...
    param: Union[str, int, bool, Dict[str, Union[str, int, bool]], None]
