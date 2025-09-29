"""Debug test to see what's happening with the UI."""

import pytest
from playwright.async_api import Page, expect
from typing import Dict
from tests.e2e.e2e_helpers import handle_settings_interaction


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_debug_game_start(async_page: Page, e2e_urls: Dict[str, str]) -> None:
    """Debug test to see what happens when starting a game."""
    # Navigate to the frontend
    await async_page.goto(e2e_urls["frontend"])
    await async_page.wait_for_load_state("networkidle")

    # Check connection
    connection_text = async_page.locator('[data-testid="connection-text"]')
    if await connection_text.count() > 0:
        await expect(connection_text).to_have_text("Connected", timeout=10000)
        print("✅ Connected to WebSocket")

    # Handle settings interaction
    await handle_settings_interaction(async_page, should_click_start_game=False)

    # Select human vs human mode
    mode_button = async_page.locator('[data-testid="mode-human-vs-human"]')
    if await mode_button.count() > 0:
        await mode_button.click()
        await async_page.wait_for_timeout(500)
        print("✅ Selected human vs human mode")

    # Click start game
    start_button = async_page.locator('[data-testid="start-game-button"]')
    await expect(start_button).to_be_visible(timeout=5000)
    await expect(start_button).to_be_enabled(timeout=5000)

    # Take screenshot before clicking
    await async_page.screenshot(path="/tmp/before_start.png")
    print("📸 Screenshot taken before start")

    await start_button.click()
    await async_page.wait_for_timeout(3000)

    # Take screenshot after clicking
    await async_page.screenshot(path="/tmp/after_start.png")
    print("📸 Screenshot taken after start")

    # Debug: Check what elements exist now
    body_content = await async_page.locator("body").inner_html()
    print(f"Body content length: {len(body_content)}")

    # Check for various game elements
    game_container = async_page.locator('[data-testid="game-container"]')
    game_container_count = await game_container.count()
    print(f"game-container count: {game_container_count}")

    game_board = async_page.locator(".game-board")
    game_board_count = await game_board.count()
    print(f"game-board count: {game_board_count}")

    game_setup = async_page.locator('[data-testid="game-setup"]')
    game_setup_count = await game_setup.count()
    print(f"game-setup count: {game_setup_count}")

    # Check if we're still in settings or if there's an error
    error_elements = async_page.locator(".error, .toast, .warning")
    error_count = await error_elements.count()
    print(f"Error elements count: {error_count}")

    if error_count > 0:
        for i in range(error_count):
            error_text = await error_elements.nth(i).inner_text()
            print(f"Error {i}: {error_text}")

    print("✅ Debug test completed")
