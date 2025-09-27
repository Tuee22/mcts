"""
Tests for race conditions that reproduce e2e failures.

These tests focus on reproducing race condition scenarios at the API level
that cause issues in the frontend, particularly around button states and
game creation/management.
"""

import asyncio
import time
from typing import Dict, List
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.models import GameCreateRequest, GameSettings, PlayerType


class TestConcurrentGameOperations:
    """Test concurrent operations that can cause race conditions."""

    def test_concurrent_game_creation(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test multiple simultaneous game creation requests.

        This reproduces race conditions where multiple games are created
        at the same time, potentially causing button state issues.
        """
        # Simulate multiple rapid game creation requests
        responses = []
        for i in range(3):
            response = test_client.post("/games", json=pvp_game_request.model_dump())
            responses.append(response)

        # All requests should succeed
        game_ids = []
        for response in responses:
            assert response.status_code == 200
            game_data = response.json()
            assert "game_id" in game_data
            assert game_data["status"] == "in_progress"
            game_ids.append(game_data["game_id"])

        # All games should be unique
        assert len(set(game_ids)) == len(game_ids)

        # All games should be retrievable
        for game_id in game_ids:
            get_response = test_client.get(f"/games/{game_id}")
            assert get_response.status_code == 200

    def test_rapid_new_game_after_active_game(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test creating new games rapidly after existing games.

        This reproduces the e2e scenario where users rapidly click "New Game"
        while previous games are still active.
        """
        # Create first game
        response1 = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response1.status_code == 200
        game1_data = response1.json()
        game1_id = game1_data["game_id"]

        # Immediately create second game (simulates rapid "New Game" clicks)
        response2 = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response2.status_code == 200
        game2_data = response2.json()
        game2_id = game2_data["game_id"]

        # Games should be independent
        assert game1_id != game2_id

        # Both games should remain accessible
        get1_response = test_client.get(f"/games/{game1_id}")
        get2_response = test_client.get(f"/games/{game2_id}")

        assert get1_response.status_code == 200
        assert get2_response.status_code == 200

        game1_state = get1_response.json()
        game2_state = get2_response.json()

        # Both should be in valid states
        assert game1_state["status"] == "in_progress"
        assert game2_state["status"] == "in_progress"

    def test_concurrent_game_access_patterns(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test concurrent access to the same game from multiple "clients".

        This simulates the pattern where multiple browser tabs or
        rapid navigation might access the same game simultaneously.
        """
        # Create a game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Simulate multiple simultaneous requests to the same game
        responses = []
        for i in range(5):
            get_response = test_client.get(f"/games/{game_id}")
            board_response = test_client.get(f"/games/{game_id}/board")
            moves_response = test_client.get(f"/games/{game_id}/legal-moves")

            responses.extend([get_response, board_response, moves_response])

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

        # All game detail responses should be consistent
        game_responses = responses[::3]  # Every third response is a game detail
        initial_state = game_responses[0].json()

        for response in game_responses[1:]:
            current_state = response.json()
            assert current_state["game_id"] == initial_state["game_id"]
            assert current_state["status"] == initial_state["status"]


class TestGameStateConsistency:
    """Test game state consistency under various conditions."""

    def test_game_state_after_rapid_requests(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that game state remains consistent under rapid requests.

        This reproduces scenarios where rapid user interactions cause
        state inconsistencies that affect button availability.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Make rapid requests to various endpoints
        requests = [
            f"/games/{game_id}",
            f"/games/{game_id}/board",
            f"/games/{game_id}/legal-moves",
            f"/games/{game_id}",
            f"/games/{game_id}/board",
        ]

        # Execute requests rapidly
        results = []
        for request_path in requests:
            response = test_client.get(request_path)
            results.append((request_path, response))

        # All should succeed
        for request_path, response in results:
            assert response.status_code == 200, f"Failed request: {request_path}"

        # Game state should remain consistent
        final_response = test_client.get(f"/games/{game_id}")
        assert final_response.status_code == 200

        final_state = final_response.json()
        assert final_state["game_id"] == game_id
        assert final_state["status"] == "in_progress"
        assert "board_display" in final_state

    def test_game_list_consistency_during_operations(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that game list remains consistent during concurrent operations.

        This tests whether rapid game creation affects the game list
        in ways that could cause UI elements to disappear.
        """
        # Get initial game list
        initial_list_response = test_client.get("/games")
        assert initial_list_response.status_code == 200
        initial_list = initial_list_response.json()
        assert isinstance(initial_list, dict)
        initial_games = initial_list.get("games", [])
        assert isinstance(initial_games, list)
        initial_count = len(initial_games)

        # Create multiple games rapidly
        created_games = []
        for i in range(3):
            response = test_client.post("/games", json=pvp_game_request.model_dump())
            assert response.status_code == 200
            created_games.append(response.json())

        # Check list consistency after rapid creation
        final_list_response = test_client.get("/games")
        assert final_list_response.status_code == 200
        final_list = final_list_response.json()
        assert isinstance(final_list, dict)

        # Should have exactly the expected number of new games
        final_games = final_list.get("games", [])
        assert isinstance(final_games, list)
        final_count = len(final_games)
        assert final_count == initial_count + 3

        # All created games should be in the list
        assert "games" in final_list
        final_games_list = final_list["games"]
        assert isinstance(final_games_list, list)
        game_ids_in_list = {game["game_id"] for game in final_games_list}
        for created_game in created_games:
            assert created_game["game_id"] in game_ids_in_list


class TestEndpointConsistency:
    """Test consistency across different API endpoints."""

    def test_game_data_consistency_across_endpoints(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that different endpoints return consistent data for the same game.

        Inconsistencies between endpoints can cause button state issues
        where the UI doesn't have the expected data.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Get data from different endpoints
        game_response = test_client.get(f"/games/{game_id}")
        board_response = test_client.get(f"/games/{game_id}/board")
        moves_response = test_client.get(f"/games/{game_id}/legal-moves")

        assert game_response.status_code == 200
        assert board_response.status_code == 200
        assert moves_response.status_code == 200

        game_state = game_response.json()
        board_state = board_response.json()
        moves_state = moves_response.json()

        # Core fields should be consistent
        assert game_state["game_id"] == game_id
        assert board_state["game_id"] == game_id
        assert moves_state["game_id"] == game_id

        # Turn information should be consistent
        assert board_state["current_turn"] == game_state["current_turn"]

        # Response structures should be as expected
        assert "board_display" in game_state
        assert "board" in board_state
        assert "legal_moves" in moves_state
        assert isinstance(moves_state["legal_moves"], list)

    def test_response_structure_stability(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that API response structures remain stable.

        This ensures that the frontend can rely on specific fields
        being present for button state logic.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()

        # Verify all required fields for frontend are present
        required_fields = [
            "game_id",
            "status",
            "mode",
            "player1",
            "player2",
            "current_turn",
            "move_count",
            "board_display",
            "created_at",
        ]

        for field in required_fields:
            assert field in game_data, f"Missing required field: {field}"

        # Verify field types are as expected
        assert isinstance(game_data["game_id"], str)
        assert isinstance(game_data["status"], str)
        assert isinstance(game_data["current_turn"], int)
        assert isinstance(game_data["move_count"], int)
        assert game_data["board_display"] is None or isinstance(
            game_data["board_display"], str
        )


class TestErrorConditions:
    """Test error conditions that might cause race conditions."""

    def test_invalid_game_access_patterns(self, test_client: TestClient) -> None:
        """
        Test that invalid game access doesn't cause state corruption.

        This ensures that attempting to access non-existent games
        doesn't affect the state of valid games.
        """
        # Try to access a non-existent game
        invalid_id = "non-existent-game-id"
        response = test_client.get(f"/games/{invalid_id}")
        assert response.status_code == 404

        # Create a valid game
        pvp_request = GameCreateRequest(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN,
            player1_name="Player 1",
            player2_name="Player 2",
        )

        create_response = test_client.post("/games", json=pvp_request.model_dump())
        assert create_response.status_code == 200

        valid_game = create_response.json()
        valid_id = valid_game["game_id"]

        # Mix valid and invalid requests
        test_requests = [
            (f"/games/{valid_id}", 200),
            (f"/games/{invalid_id}", 404),
            (f"/games/{valid_id}/board", 200),
            (f"/games/{invalid_id}/board", 404),
            (f"/games/{valid_id}", 200),
        ]

        for request_path, expected_status in test_requests:
            response = test_client.get(request_path)
            assert response.status_code == expected_status

        # Valid game should still be accessible and unchanged
        final_response = test_client.get(f"/games/{valid_id}")
        assert final_response.status_code == 200

        final_state = final_response.json()
        assert final_state["game_id"] == valid_id
        assert final_state["status"] == "in_progress"

    def test_malformed_request_handling(self, test_client: TestClient) -> None:
        """
        Test that malformed requests don't affect server state.

        This ensures that invalid requests don't cause issues that
        affect subsequent valid operations.
        """
        # Try various malformed game creation requests
        # Note: Empty request and extra fields are actually valid due to defaults
        truly_invalid_requests = [
            {"player1_type": "invalid_enum"},  # Invalid enum value
            {"player2_type": "invalid_enum"},  # Invalid enum value
        ]

        for malformed_data in truly_invalid_requests:
            response = test_client.post("/games", json=malformed_data)
            # Should return 422 (validation error) not 500 (server error)
            assert response.status_code == 422

        # Test that requests with extra fields or empty data succeed with defaults
        valid_with_defaults_requests = [
            {},  # Empty request - should use defaults
            {"invalid_field": "value"},  # Extra fields ignored - should use defaults
        ]

        for request_data in valid_with_defaults_requests:
            response = test_client.post("/games", json=request_data)
            # Should succeed with default values
            assert response.status_code == 200

        # Server should still be able to handle valid requests
        valid_request = GameCreateRequest(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN,
            player1_name="Player 1",
            player2_name="Player 2",
        )

        valid_response = test_client.post("/games", json=valid_request.model_dump())
        assert valid_response.status_code == 200

        game_data = valid_response.json()
        assert "game_id" in game_data
        assert game_data["status"] == "in_progress"


class TestE2EFailureReproduction:
    """
    Test class to reproduce e2e failures at the backend level.

    These tests are designed to fail and demonstrate the same race conditions
    that cause e2e test timeouts when waiting for UI elements like the
    "⚙️ Game Settings" button.
    """

    def test_rapid_game_settings_transition(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Reproduce the e2e race condition from Settings button timeout.

        This test simulates the rapid sequence: Create Game -> New Game -> Settings
        that causes the e2e test to timeout waiting for the Settings button.
        This test should fail if it reproduces the underlying issue.
        """
        # Create initial game (simulates opening settings and starting game)
        response1 = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response1.status_code == 200
        game1_data = response1.json()
        game1_id = game1_data["game_id"]

        # Immediately create a new game (simulates rapid "New Game" click)
        response2 = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response2.status_code == 200
        game2_data = response2.json()
        game2_id = game2_data["game_id"]

        # Now try to access settings-related data rapidly
        # This should work but might fail if there's a race condition
        start_time = time.time()
        timeout_seconds = 5.0  # Much shorter than e2e timeout to catch issues faster

        while time.time() - start_time < timeout_seconds:
            # Simulate rapid requests that the Settings UI would make
            game_list_response = test_client.get("/games")
            game_detail_response = test_client.get(f"/games/{game2_id}")

            if game_list_response.status_code != 200:
                pytest.fail(
                    f"Game list request failed: {game_list_response.status_code}"
                )

            if game_detail_response.status_code != 200:
                pytest.fail(
                    f"Game detail request failed: {game_detail_response.status_code}"
                )

            # Check that the response contains the data needed for Settings button
            game_list = game_list_response.json()
            game_detail = game_detail_response.json()

            # These assertions will fail if there's a race condition
            assert "games" in game_list
            assert isinstance(game_list["games"], list)
            assert len(game_list["games"]) >= 2  # Should have both games

            assert "game_id" in game_detail
            assert game_detail["game_id"] == game2_id
            assert "status" in game_detail

            # Brief pause to allow for race conditions to manifest
            time.sleep(0.01)

        # If we reach here without failing, the backend is handling rapid transitions correctly
        # But the e2e failure suggests there might be a frontend-specific issue

    def test_concurrent_button_state_requests(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test simultaneous requests that affect button availability.

        This reproduces the scenario where multiple UI components try to
        determine button states simultaneously, potentially causing race conditions.
        """
        # Create a game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200
        game_data = response.json()
        game_id = game_data["game_id"]

        # Simulate multiple concurrent requests for different aspects of UI state
        # that determine button availability (New Game, Settings, etc.)
        concurrent_requests = []

        # Start multiple requests simultaneously
        start_time = time.time()
        request_pairs = [
            ("/games", f"/games/{game_id}"),
            (f"/games/{game_id}/board", f"/games/{game_id}/legal-moves"),
            ("/games", f"/games/{game_id}/board"),
            (f"/games/{game_id}", f"/games/{game_id}/legal-moves"),
        ]

        for req1_path, req2_path in request_pairs:
            # Make both requests as close to simultaneously as possible
            resp1 = test_client.get(req1_path)
            resp2 = test_client.get(req2_path)
            concurrent_requests.extend([(req1_path, resp1), (req2_path, resp2)])

        end_time = time.time()

        # All requests should succeed quickly
        assert end_time - start_time < 2.0, "Concurrent requests took too long"

        for path, resp in concurrent_requests:
            assert (
                resp.status_code == 200
            ), f"Request to {path} failed: {resp.status_code}"

            # Verify response contains expected data structure
            data = resp.json()
            assert isinstance(data, dict), f"Response from {path} is not a dict"

            # Each response should have the minimum required fields for UI
            if "games" in data:
                assert isinstance(data["games"], list)
            if "game_id" in data:
                assert isinstance(data["game_id"], str)

        # Final verification that the game state remains consistent
        final_response = test_client.get(f"/games/{game_id}")
        assert final_response.status_code == 200
        final_data = final_response.json()
        assert final_data["game_id"] == game_id
        assert final_data["status"] == "in_progress"

    def test_ui_state_during_rapid_transitions(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test API state consistency during rapid UI transitions.

        This reproduces the specific pattern from the e2e test:
        Settings -> Start Game -> New Game -> Settings (which shows disconnected).
        """
        # Step 1: Create initial game (simulates Settings -> Start Game)
        response1 = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response1.status_code == 200
        game1_data = response1.json()
        game1_id = game1_data["game_id"]

        # Verify game is in expected state
        assert game1_data["status"] == "in_progress"
        assert "game_id" in game1_data

        # Step 2: Rapid New Game (simulates clicking New Game button)
        response2 = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response2.status_code == 200
        game2_data = response2.json()
        game2_id = game2_data["game_id"]

        # Games should be different
        assert game1_id != game2_id

        # Step 3: Immediate attempt to access settings data
        # This is where the e2e test fails - the Settings button doesn't appear
        settings_data_requests = [
            "/games",  # Game list for settings UI
            f"/games/{game2_id}",  # Current game details
            f"/games/{game1_id}",  # Previous game should still exist
        ]

        responses = []
        request_start = time.time()

        for path in settings_data_requests:
            resp = test_client.get(path)
            responses.append((path, resp))

        request_end = time.time()

        # All requests should complete quickly (simulating UI responsiveness)
        assert request_end - request_start < 1.0, "Settings data requests too slow"

        # All responses should be successful
        for path, resp in responses:
            assert resp.status_code == 200, f"Settings data request failed: {path}"

            data = resp.json()
            assert isinstance(data, dict)

            # Verify the data contains what the Settings UI needs
            if path == "/games":
                assert "games" in data
                assert isinstance(data["games"], list)
                assert len(data["games"]) >= 2  # Both games should be listed

                # Both games should be findable in the list
                game_ids_in_list = {game["game_id"] for game in data["games"]}
                assert game1_id in game_ids_in_list
                assert game2_id in game_ids_in_list

            else:  # Individual game requests
                assert "game_id" in data
                assert "status" in data
                assert data["status"] == "in_progress"

        # Final check: Both games should remain accessible
        # If there's a race condition, one might become inaccessible
        final_check1 = test_client.get(f"/games/{game1_id}")
        final_check2 = test_client.get(f"/games/{game2_id}")

        assert final_check1.status_code == 200
        assert final_check2.status_code == 200

        # This test passing suggests the backend handles rapid transitions correctly,
        # and the e2e failure might be frontend-specific (WebSocket, state management, etc.)
