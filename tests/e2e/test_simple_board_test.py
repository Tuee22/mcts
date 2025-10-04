"""Simple test to debug e2e issues."""

import pytest
from playwright.async_api import Page, expect
from typing import Dict
from tests.e2e.e2e_helpers import handle_settings_interaction


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_simple_board_load(page: Page, e2e_urls: Dict[str, str]) -> None:
    """Test that we can load the page and see basic elements."""
    # Navigate to the frontend
    await page.goto(e2e_urls["frontend"])
    await page.wait_for_load_state("networkidle")

    # Check that the page loaded
    title = await page.title()
    assert title == "React App"
    print(f"✅ Page title: {title}")

    # Check for connection status
    connection_text = page.locator('[data-testid="connection-text"]')
    if await connection_text.count() > 0:
        await expect(connection_text).to_have_text("Connected", timeout=10000)
        print("✅ Connected to WebSocket")

    # Use helper function to handle settings interaction
    await handle_settings_interaction(page, should_click_start_game=True)

    # Look for game board
    game_board = page.locator(".game-board")
    await expect(game_board).to_be_visible(timeout=10000)
    print("✅ Game board is visible")

    print("✅ Simple board test completed successfully")
