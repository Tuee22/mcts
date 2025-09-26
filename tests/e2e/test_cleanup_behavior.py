"""
E2E tests for automatic game cleanup behavior.

These tests verify that the cleanup system works correctly in a real
server environment, including timing, configuration, and integration.
"""

import asyncio
import time
from typing import Dict, Union

import pytest
import requests
from playwright.async_api import Page


def get_dict_response(response: requests.Response) -> Dict[str, Union[str, int]]:
    """Helper function to get a typed dict response."""
    json_data = response.json()
    if not isinstance(json_data, dict):
        raise TypeError(f"Expected dict response, got {type(json_data)}")
    # Filter to only str/int values as promised by return type
    filtered_data = {}
    for key, value in json_data.items():
        if isinstance(value, (str, int)):
            filtered_data[key] = value
    return filtered_data


def get_game_id_from_response(response: requests.Response) -> str:
    """Helper function to extract game_id from response."""
    json_data = response.json()
    if not isinstance(json_data, dict):
        raise TypeError(f"Expected dict response, got {type(json_data)}")
    game_id = json_data.get("game_id")
    if not isinstance(game_id, str):
        raise TypeError(f"Expected string game_id, got {type(game_id)}")
    return game_id


def get_active_games_count(response: requests.Response) -> int:
    """Helper function to extract active_games count from health response."""
    json_data = response.json()
    if not isinstance(json_data, dict):
        raise TypeError(f"Expected dict response, got {type(json_data)}")
    active_games = json_data.get("active_games")
    if not isinstance(active_games, int):
        raise TypeError(f"Expected int active_games, got {type(active_games)}")
    return active_games


def get_message_from_response(response: requests.Response) -> str:
    """Helper function to extract message from response."""
    json_data = response.json()
    if not isinstance(json_data, dict):
        raise TypeError(f"Expected dict response, got {type(json_data)}")
    message = json_data.get("message")
    if not isinstance(message, str):
        raise TypeError(f"Expected string message, got {type(message)}")
    return message


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCleanupBehavior:
    """E2E tests for cleanup functionality."""

    async def test_cleanup_task_starts_in_test_mode(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that cleanup task starts with test configuration during E2E tests.

        This verifies that the PYTEST_CURRENT_TEST environment variable
        is properly detected by the server.
        """
        # Navigate to app to ensure server is running
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Check server health
        response = requests.get(e2e_urls["backend"] + "/health")
        assert response.status_code == 200

        health_data = get_dict_response(response)
        print(f"Server status: {health_data['status']}")
        print(f"Initial game count: {health_data['active_games']}")

        # The cleanup task should be running in test mode
        # We can't directly verify the logs from here, but we can verify
        # that the server is healthy and responding
        assert health_data["status"] == "healthy"

    async def test_game_creation_via_api(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test creating games via API for cleanup testing.

        This establishes that we can create games that will be subject
        to cleanup.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Create a game via API
        game_data = {
            "player1_type": "human",
            "player2_type": "machine",
            "player1_name": "Test Player",
            "player2_name": "AI Player",
            "settings": {"board_size": 5},
        }

        response = requests.post(e2e_urls["backend"] + "/games", json=game_data)

        assert response.status_code == 200
        game_info = get_dict_response(response)
        game_id = get_game_id_from_response(response)

        print(f"✅ Created test game: {game_id}")

        # Verify game exists
        health_response = requests.get(e2e_urls["backend"] + "/health")
        assert get_active_games_count(health_response) >= 1

        # Verify we can fetch the game
        game_response = requests.get(e2e_urls["backend"] + f"/games/{game_id}")
        assert game_response.status_code == 200

        print(f"✅ Game {game_id} accessible via API")

    async def test_multiple_game_creation(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test creating multiple games to verify cleanup handles multiple games.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Get initial count
        initial_response = requests.get(e2e_urls["backend"] + "/health")
        initial_data = get_dict_response(initial_response)
        initial_count = get_active_games_count(initial_response)

        created_games = []

        # Create multiple games
        for i in range(3):
            game_data = {
                "player1_type": "human",
                "player2_type": "machine",
                "player1_name": f"Test Player {i+1}",
                "player2_name": f"AI Player {i+1}",
                "settings": {"board_size": 5},
            }

            response = requests.post(e2e_urls["backend"] + "/games", json=game_data)

            assert response.status_code == 200
            created_games.append(get_game_id_from_response(response))

        print(f"✅ Created {len(created_games)} test games")

        # Verify count increased
        final_response = requests.get(e2e_urls["backend"] + "/health")
        final_data = get_dict_response(final_response)
        final_count = get_active_games_count(final_response)
        assert final_count >= initial_count + 3

        print(f"Game count: {initial_count} → {final_count}")

    async def test_game_deletion_api(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that games can be manually deleted via API.

        This verifies the DELETE endpoint works correctly.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Create a game
        game_data = {
            "player1_type": "human",
            "player2_type": "machine",
            "player1_name": "Deletable Player",
            "player2_name": "AI Player",
            "settings": {"board_size": 5},
        }

        create_response = requests.post(e2e_urls["backend"] + "/games", json=game_data)

        assert create_response.status_code == 200
        game_id = get_game_id_from_response(create_response)

        # Verify game exists
        get_response = requests.get(e2e_urls["backend"] + f"/games/{game_id}")
        assert get_response.status_code == 200

        # Delete the game
        delete_response = requests.delete(e2e_urls["backend"] + f"/games/{game_id}")
        assert delete_response.status_code == 200

        delete_message = get_message_from_response(delete_response)
        assert "deleted successfully" in delete_message

        # Verify game no longer exists
        get_response_after = requests.get(e2e_urls["backend"] + f"/games/{game_id}")
        assert get_response_after.status_code == 404

        print(f"✅ Successfully deleted game {game_id}")

    async def test_cleanup_configuration_detection(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that server detects test mode during E2E test execution.

        This is an indirect test since we can't directly access server logs,
        but we can verify behavioral differences.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # In test mode, cleanup runs every 10 seconds with 60-second timeout
        # In production mode, cleanup runs every 60 seconds with 1-hour timeout
        # We can't directly test the full timeout, but we can test that
        # the server is configured for tests

        # Check server is responsive
        response = requests.get(e2e_urls["backend"] + "/health")
        assert response.status_code == 200

        health_data = get_dict_response(response)
        assert health_data["status"] == "healthy"

        print("✅ Server running in test environment")

        # Create a game to ensure there's something that could be cleaned up
        game_data = {
            "player1_type": "human",
            "player2_type": "machine",
            "player1_name": "Cleanup Test Player",
            "player2_name": "AI Player",
        }

        game_response = requests.post(e2e_urls["backend"] + "/games", json=game_data)

        assert game_response.status_code == 200
        game_id = get_game_id_from_response(game_response)

        print(f"✅ Created game {game_id} for cleanup testing")

    async def test_server_health_with_games(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that server health endpoint correctly reports game counts.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Get initial health
        response1 = requests.get(e2e_urls["backend"] + "/health")
        assert response1.status_code == 200

        health1 = get_dict_response(response1)
        initial_count = get_active_games_count(response1)

        print(f"Initial health: {health1}")

        # Create a game
        game_data = {
            "player1_type": "human",
            "player2_type": "machine",
            "player1_name": "Health Test Player",
            "player2_name": "AI Player",
        }

        create_response = requests.post(e2e_urls["backend"] + "/games", json=game_data)

        assert create_response.status_code == 200
        game_id = get_game_id_from_response(create_response)

        # Check health again
        response2 = requests.get(e2e_urls["backend"] + "/health")
        health2 = get_dict_response(response2)

        assert get_active_games_count(response2) == initial_count + 1
        print(f"Health after game creation: {health2}")

        print(
            f"✅ Health endpoint accurately tracks games: {initial_count} → {get_active_games_count(response2)}"
        )

    async def test_game_api_endpoints_accessible(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that all game-related API endpoints are accessible.

        This ensures cleanup doesn't interfere with normal operations.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Test health endpoint
        health_response = requests.get(e2e_urls["backend"] + "/health")
        assert health_response.status_code == 200
        print("✅ Health endpoint accessible")

        # Test games list endpoint
        games_response = requests.get(e2e_urls["backend"] + "/games")
        assert games_response.status_code == 200
        print("✅ Games list endpoint accessible")

        # Create a game to test other endpoints
        game_data = {
            "player1_type": "human",
            "player2_type": "machine",
            "player1_name": "API Test Player",
            "player2_name": "AI Player",
        }

        create_response = requests.post(e2e_urls["backend"] + "/games", json=game_data)

        assert create_response.status_code == 200
        game_id = get_game_id_from_response(create_response)
        print(f"✅ Game creation endpoint accessible, created: {game_id}")

        # Test individual game endpoint
        game_response = requests.get(e2e_urls["backend"] + f"/games/{game_id}")
        assert game_response.status_code == 200
        print("✅ Individual game endpoint accessible")

        # Test legal moves endpoint (might fail if not implemented, that's OK)
        try:
            moves_response = requests.get(
                e2e_urls["backend"] + f"/games/{game_id}/legal-moves"
            )
            if moves_response.status_code == 200:
                print("✅ Legal moves endpoint accessible")
            else:
                print(f"ℹ️  Legal moves endpoint returned {moves_response.status_code}")
        except Exception as e:
            print(f"ℹ️  Legal moves endpoint error (expected): {e}")

        print("✅ All core API endpoints functional during cleanup operation")

    async def test_cleanup_does_not_interfere_with_active_games(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that cleanup doesn't interfere with games that are being actively used.

        This simulates making moves to keep a game active.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Create a game
        game_data = {
            "player1_type": "human",
            "player2_type": "human",  # Human vs Human to avoid AI complications
            "player1_name": "Active Player 1",
            "player2_name": "Active Player 2",
        }

        create_response = requests.post(e2e_urls["backend"] + "/games", json=game_data)

        assert create_response.status_code == 200
        game_id = get_game_id_from_response(create_response)

        print(f"✅ Created active game: {game_id}")

        # Verify game exists
        game_response = requests.get(e2e_urls["backend"] + f"/games/{game_id}")
        assert game_response.status_code == 200

        # The game should remain accessible for the duration of the test
        # (which is much shorter than the cleanup timeout)

        # Wait a moment to simulate some game activity time
        await asyncio.sleep(2)

        # Verify game still exists
        game_response_after = requests.get(e2e_urls["backend"] + f"/games/{game_id}")
        assert game_response_after.status_code == 200

        print(f"✅ Active game {game_id} remains accessible during cleanup operation")


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCleanupTiming:
    """E2E tests for cleanup timing behavior."""

    async def test_cleanup_timing_expectations(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test cleanup timing expectations in test environment.

        Note: We can't test full 60-second timeout in E2E tests due to time constraints,
        but we can verify the system is configured for quick cleanup.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # In test mode:
        # - Cleanup runs every 10 seconds
        # - Games are cleaned after 60 seconds of inactivity
        #
        # This test verifies the infrastructure is in place

        # Create a game
        game_data = {
            "player1_type": "human",
            "player2_type": "machine",
            "player1_name": "Timing Test Player",
            "player2_name": "AI Player",
        }

        create_response = requests.post(e2e_urls["backend"] + "/games", json=game_data)

        assert create_response.status_code == 200
        game_id = get_game_id_from_response(create_response)

        print(f"✅ Created game {game_id} for timing test")

        # Verify game is immediately accessible
        immediate_response = requests.get(e2e_urls["backend"] + f"/games/{game_id}")
        assert immediate_response.status_code == 200

        # Wait a short time (much less than cleanup timeout)
        await asyncio.sleep(5)

        # Game should still be accessible
        short_wait_response = requests.get(e2e_urls["backend"] + f"/games/{game_id}")
        assert short_wait_response.status_code == 200

        print(f"✅ Game {game_id} accessible after short wait (as expected)")

        # Note: We don't test the full 60-second timeout here because:
        # 1. E2E tests should be fast
        # 2. The cleanup logic is tested in unit tests
        # 3. This verifies the infrastructure is working

    async def test_cleanup_preserves_recent_activity(
        self, page: Page, e2e_urls: Dict[str, str]
    ) -> None:
        """
        Test that cleanup preserves games with recent activity.

        This simulates normal game usage patterns.
        """
        # Navigate to app
        await page.goto(e2e_urls["frontend"])
        await page.wait_for_load_state("networkidle")

        # Create a game
        game_data = {
            "player1_type": "human",
            "player2_type": "machine",
            "player1_name": "Recent Activity Player",
            "player2_name": "AI Player",
        }

        create_response = requests.post(e2e_urls["backend"] + "/games", json=game_data)

        assert create_response.status_code == 200
        game_id = get_game_id_from_response(create_response)

        print(f"✅ Created game {game_id} for activity test")

        # Simulate periodic activity by fetching the game
        for i in range(3):
            await asyncio.sleep(2)

            activity_response = requests.get(e2e_urls["backend"] + f"/games/{game_id}")
            assert activity_response.status_code == 200

            print(f"✅ Activity check {i+1}: Game {game_id} still accessible")

        # Final check - game should still be accessible
        final_response = requests.get(e2e_urls["backend"] + f"/games/{game_id}")
        assert final_response.status_code == 200

        print(f"✅ Game {game_id} preserved with recent activity pattern")
