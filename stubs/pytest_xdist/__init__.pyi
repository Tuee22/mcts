"""Type stubs for pytest-xdist package."""

from typing import Literal, Optional, List, Any, Dict, Protocol

# Distribution modes for pytest-xdist
DistMode = Literal["each", "load", "loadscope", "loadfile", "loadgroup"]

# Main configuration for xdist
class XDistConfig:
    def __init__(
        self,
        numprocesses: Optional[int] = None,
        dist: Optional[DistMode] = None,
        tx: Optional[List[str]] = None,
        maxprocesses: Optional[int] = None,
    ) -> None: ...

# Worker restart configuration
class WorkerRestartConfig:
    def __init__(self, maxworkerrestart: int = 1) -> None: ...

# Pytest plugin hooks and utilities
def pytest_cmdline_parse() -> None: ...
def pytest_configure_node(node: Any) -> None: ...
def pytest_runtest_protocol(item: Any, nextitem: Any) -> Optional[bool]: ...

# For distributed testing capabilities
class DistSession(Protocol):
    def pytest_collection_modifyitems(self, config: Any, items: List[Any]) -> None: ...
