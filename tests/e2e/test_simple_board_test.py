"""Simple test to debug e2e issues."""

import pytest
from playwright.async_api import Page, expect
from typing import Dict


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_simple_board_load(async_page: Page, e2e_urls: Dict[str, str]) -> None:
    """Test that we can load the page and see basic elements."""
    # Navigate to the frontend
    await async_page.goto(e2e_urls["frontend"])
    await async_page.wait_for_load_state("networkidle")

    # Check that the page loaded
    title = await async_page.title()
    assert title == "React App"
    print(f"✅ Page title: {title}")

    # Check for connection status
    connection_text = async_page.locator('[data-testid="connection-text"]')
    if await connection_text.count() > 0:
        await expect(connection_text).to_have_text("Connected", timeout=10000)
        print("✅ Connected to WebSocket")

    # Look for settings button
    settings_button = async_page.locator('button:has-text("⚙️ Game Settings")')
    await expect(settings_button).to_be_visible(timeout=5000)
    print("✅ Settings button found")

    # Click settings
    await settings_button.click()
    await async_page.wait_for_timeout(1000)

    # Look for start game button
    start_button = async_page.locator('[data-testid="start-game-button"]')
    await expect(start_button).to_be_visible(timeout=5000)
    print("✅ Start Game button found")

    # Click start game
    await start_button.click()
    await async_page.wait_for_timeout(3000)

    # Look for game board
    game_board = async_page.locator(".game-board")
    await expect(game_board).to_be_visible(timeout=10000)
    print("✅ Game board is visible")

    print("✅ Simple board test completed successfully")
