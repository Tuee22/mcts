"""Type stubs for _pytest.reports."""

from typing import Optional

class TestReport:
    """Pytest test report."""

    when: str
    outcome: str
    nodeid: str

    def __init__(self, **kwargs: object) -> None: ...

class CollectReport:
    """Pytest collect report."""

    outcome: str
    nodeid: str

    def __init__(self, **kwargs: object) -> None: ...
