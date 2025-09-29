"""Type stubs for pytest-xdist package."""

from typing import Literal, Optional, List, Dict, Protocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

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

# Worker node type for pytest-xdist
class WorkerNode:
    """Represents a worker node in xdist."""

    gateway: object
    workerid: str

# Pytest item type
class PytestItem:
    """Represents a test item in pytest."""

    nodeid: str

# Pytest config type
class PytestConfig:
    """Represents pytest configuration."""

    option: object

# Pytest plugin hooks and utilities
def pytest_cmdline_parse() -> None: ...
def pytest_configure_node(node: WorkerNode) -> None: ...
def pytest_runtest_protocol(
    item: PytestItem, nextitem: Optional[PytestItem]
) -> Optional[bool]: ...

# For distributed testing capabilities
class DistSession(Protocol):
    def pytest_collection_modifyitems(
        self, config: PytestConfig, items: List[PytestItem]
    ) -> None: ...
