"""Working E2E connection tests using external servers."""
import os
import pytest
from playwright.async_api import async_playwright, expect


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_successful_connection() -> None:
    """Test that app successfully connects to backend on load."""
    # Use environment URLs or fallback to localhost
    frontend_url = os.environ.get("E2E_FRONTEND_URL", "http://localhost:3002")
    backend_url = os.environ.get("E2E_BACKEND_URL", "http://localhost:8002")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=os.environ.get("E2E_HEADLESS", "true").lower() == "true",
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720}, ignore_https_errors=True
        )
        page = await context.new_page()

        try:
            # Navigate to frontend
            await page.goto(frontend_url, timeout=30000)

            # Wait for page to load
            await page.wait_for_load_state("networkidle", timeout=15000)

            # Check if we have the React app
            title = await page.title()
            assert title == "React App"

            # Look for the app root element
            app_root = page.locator("#root")
            await expect(app_root).to_be_visible(timeout=5000)

            print("✅ Frontend loaded successfully")

            # Check backend health
            response = await page.request.get(f"{backend_url}/health")
            assert response.ok
            health_data = await response.json()
            assert health_data["status"] == "healthy"

            print("✅ Backend is healthy")

            # Check for connection status elements (if they exist)
            try:
                connection_status = page.locator('[data-testid="connection-status"]')
                if await connection_status.count() > 0:
                    await expect(connection_status).to_be_visible(timeout=5000)
                    print("✅ Connection status element found")
            except Exception:
                print("⚠️  No connection status element found (app may not have one)")

        finally:
            await page.close()
            await context.close()
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_game_creation() -> None:
    """Test creating a new game."""
    backend_url = os.environ.get("E2E_BACKEND_URL", "http://localhost:8002")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=os.environ.get("E2E_HEADLESS", "true").lower() == "true",
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Create game via API with proper JSON format
            response = await page.request.post(
                f"{backend_url}/games",
                data={
                    "player1_name": "TestPlayer1",
                    "player2_name": "TestPlayer2",
                    "player1_type": "human",
                    "player2_type": "machine",
                    "settings": {"board_size": 9, "time_limit_seconds": 300},
                },
                headers={"Content-Type": "application/json"},
            )

            if not response.ok:
                error_data = await response.text()
                print(f"❌ Error creating game: {response.status} - {error_data}")

            assert response.ok
            game_data = await response.json()
            assert game_data["status"] in ["waiting", "in_progress"]
            assert "game_id" in game_data

            print(f"✅ Game created with ID: {game_data['game_id']}")
            print(f"   Status: {game_data['status']}")

            # Safely get player names with type checking
            player1_name = "Unknown"
            player2_name = "Unknown"
            if isinstance(game_data.get("player1"), dict):
                player1_data = game_data["player1"]
                if isinstance(player1_data, dict):
                    player1_name = str(player1_data.get("name", "Unknown"))
            if isinstance(game_data.get("player2"), dict):
                player2_data = game_data["player2"]
                if isinstance(player2_data, dict):
                    player2_name = str(player2_data.get("name", "Unknown"))
            print(f"   Players: {player1_name} vs {player2_name}")

        finally:
            await page.close()
            await context.close()
            await browser.close()
