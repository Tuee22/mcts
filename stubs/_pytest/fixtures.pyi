"""Type stubs for _pytest.fixtures."""

from typing import Callable, Dict, Iterator, List, Optional, TypeVar, Union

_T = TypeVar("_T")

class FixtureRequest:
    """Pytest fixture request."""

    function: object
    cls: Optional[type]
    instance: Optional[object]
    module: object
    session: object
    config: object
    param: object

    def getfixturevalue(self, argname: str) -> object: ...
    def applymarker(self, marker: object) -> None: ...

class FixtureDef:
    """Fixture definition."""

    argname: str
    scope: str
    params: Optional[List[object]]

class SubRequest(FixtureRequest):
    """Sub-request for parameterized fixtures."""

    pass
