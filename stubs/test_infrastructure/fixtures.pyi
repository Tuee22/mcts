"""Type stubs for test fixtures."""

from typing import AsyncIterator, Generator, Protocol, Dict, Union
from playwright.async_api import Page, Browser, BrowserContext
from pathlib import Path

# Fixture protocols
class IsolatedPageFixture(Protocol):
    async def __call__(self) -> AsyncIterator[Page]: ...

class TestMetricsFixture(Protocol):
    def record(self, test_name: str, duration: float) -> None: ...
    def get_metrics(self) -> Dict[str, Union[str, float, int]]: ...

class E2EConfigFixture(Protocol):
    backend_url: str
    frontend_url: str
    ws_url: str
    headless: bool

# Browser context protocols
class BrowserContextConfig(Protocol):
    def create_context(self, browser: Browser) -> BrowserContext: ...
    def configure_viewport(
        self, width: int, height: int
    ) -> Dict[str, Union[str, int]]: ...

# Test data protocols
class TestDataProvider(Protocol):
    def get_test_data(self, test_name: str) -> Dict[str, Union[str, float, int]]: ...
    def cleanup_test_data(self) -> None: ...
