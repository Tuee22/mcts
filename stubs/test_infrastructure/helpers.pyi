"""Type stubs for test helper functions."""

from typing import Awaitable, TypeVar, Optional, Dict, Any, Union
from playwright.async_api import Page, Locator

T = TypeVar("T")

# Selector constants
SETTINGS_BUTTON_SELECTOR: str
APP_MAIN_SELECTOR: str
CONNECTION_TEXT_SELECTOR: str
GAME_BOARD_SELECTOR: str

# Wait helpers
async def wait_for_element(
    page: Page, selector: str, timeout: float = 5000
) -> Locator: ...
async def wait_for_connection(page: Page, timeout: float = 10000) -> bool: ...
async def wait_for_app_ready(page: Page, timeout: float = 10000) -> bool: ...

# Navigation helpers
async def safe_navigation(
    page: Page,
    url: str,
    wait_for_selector: Optional[str] = None,
    timeout: float = 10000,
) -> bool: ...
async def go_back_safely(
    page: Page, wait_for_selector: Optional[str] = None, timeout: float = 10000
) -> bool: ...

# Assertion helpers
async def assert_within_timeout(
    check_func: Awaitable[bool], timeout: float, error_message: str
) -> None: ...

# Element interaction helpers
async def click_when_ready(
    page: Page, selector: str, timeout: float = 5000
) -> bool: ...
async def type_when_ready(
    page: Page, selector: str, text: str, timeout: float = 5000
) -> bool: ...
