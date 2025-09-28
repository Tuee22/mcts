"""Type stubs for _pytest.hookspec."""

from typing import Callable, Generator, Optional

from _pytest.reports import TestReport

class CallOutcome:
    """Pytest call outcome."""

    def get_result(self) -> Optional[TestReport]: ...

def pytest_runtest_makereport(
    item: object, call: object
) -> Generator[None, None, None]: ...
