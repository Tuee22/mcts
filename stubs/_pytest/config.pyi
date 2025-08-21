"""Type stubs for _pytest.config module."""

from typing import Optional

class Config:
    """Pytest configuration object."""

    def getvalue(self, name: str) -> object:
        """Get configuration value."""
        ...
    def getoption(self, name: str, default: Optional[object] = None) -> object:
        """Get option value."""
        ...
    def addinivalue_line(self, section: str, line: str) -> None:
        """Add a line to an ini value."""
        ...
