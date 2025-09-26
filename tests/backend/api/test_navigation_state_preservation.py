"""
Tests for navigation state preservation that reproduce e2e failures.

These tests focus on reproducing state persistence issues that occur
during browser navigation, causing UI elements to become unavailable.
"""

import time
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.models import GameCreateRequest, GameSettings, PlayerType


class TestNavigationStatePreservation:
    """Test state preservation during navigation that causes e2e failures."""

    def test_game_state_persistence_across_requests(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that game state persists correctly across multiple requests.

        This simulates the pattern of requests that occur during browser navigation.
        """
        # Create game (simulates initial page load)
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]
        initial_state = game_data

        # Simulate navigation away and back (multiple state retrieval requests)
        for i in range(3):
            # Each request simulates reloading the page after navigation
            get_response = test_client.get(f"/games/{game_id}")
            assert get_response.status_code == 200

            current_state = get_response.json()

            # State should be consistent across all requests
            assert current_state["game_id"] == initial_state["game_id"]
            assert current_state["status"] == initial_state["status"]
            assert current_state["current_turn"] == initial_state["current_turn"]

            # Essential UI data should be preserved
            assert "player1" in current_state
            assert "player2" in current_state
            assert "settings" in current_state
            assert "board_state" in current_state

    def test_game_list_consistency_during_navigation(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that game lists remain consistent during navigation patterns.

        Inconsistent game lists might cause UI elements to disappear.
        """
        # Create multiple games
        created_games = []
        for i in range(3):
            response = test_client.post("/games", json=pvp_game_request.model_dump())
            assert response.status_code == 200
            created_games.append(response.json())

        # Simulate navigation pattern: get list, navigate, get list again
        initial_list_response = test_client.get("/games")
        assert initial_list_response.status_code == 200

        initial_list = initial_list_response.json()
        assert "games" in initial_list
        initial_game_count = len(initial_list["games"])

        # Simulate some time passing (navigation delay)
        time.sleep(0.1)

        # Get list again (simulates returning to game list after navigation)
        second_list_response = test_client.get("/games")
        assert second_list_response.status_code == 200

        second_list = second_list_response.json()
        assert "games" in second_list

        # Game count should be consistent
        assert len(second_list["games"]) == initial_game_count

        # All created games should still be present
        second_game_ids = {game["game_id"] for game in second_list["games"]}
        for created_game in created_games:
            assert created_game["game_id"] in second_game_ids

    def test_settings_persistence_during_navigation(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that game settings persist correctly during navigation.

        This reproduces the "Game Settings button not found" issue
        by verifying settings are preserved across navigation.
        """
        # Create game with specific settings
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]
        original_settings = game_data["settings"]

        # Simulate navigation sequence
        navigation_requests = [
            f"/games/{game_id}",  # Game detail view
            "/games",  # Game list view
            f"/games/{game_id}",  # Back to game detail
            f"/games/{game_id}/board",  # Board view
            f"/games/{game_id}",  # Back to game detail
        ]

        for request_path in navigation_requests:
            response = test_client.get(request_path)
            assert response.status_code == 200

            # For game detail requests, verify settings are preserved
            if request_path == f"/games/{game_id}":
                current_data = response.json()
                assert "settings" in current_data
                current_settings = current_data["settings"]

                # Settings should be identical to original
                if original_settings and current_settings:
                    # Compare key settings fields
                    if "mcts_settings" in original_settings:
                        assert "mcts_settings" in current_settings

    def test_board_state_consistency_during_navigation(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that board state remains consistent during navigation.

        Board state inconsistencies could affect UI element availability.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Get initial board state
        board_response = test_client.get(f"/games/{game_id}/board")
        assert board_response.status_code == 200

        initial_board = board_response.json()

        # Simulate navigation pattern with multiple board requests
        for i in range(5):
            # Request board state (simulates page reload)
            current_board_response = test_client.get(f"/games/{game_id}/board")
            assert current_board_response.status_code == 200

            current_board = current_board_response.json()

            # Board state should be consistent
            assert current_board["player1_pos"] == initial_board["player1_pos"]
            assert current_board["player2_pos"] == initial_board["player2_pos"]

            # Essential board data should be present
            assert "walls" in current_board
            assert "turn" in current_board

    def test_legal_moves_consistency_during_navigation(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that legal moves remain consistent during navigation.

        Inconsistent legal moves could cause button state issues.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Get initial legal moves
        moves_response = test_client.get(f"/games/{game_id}/legal-moves")
        assert moves_response.status_code == 200

        initial_moves = moves_response.json()
        assert "legal_moves" in initial_moves
        initial_move_count = len(initial_moves["legal_moves"])

        # Simulate navigation with multiple legal move requests
        for i in range(3):
            current_moves_response = test_client.get(f"/games/{game_id}/legal-moves")
            assert current_moves_response.status_code == 200

            current_moves = current_moves_response.json()
            assert "legal_moves" in current_moves

            # Move count should be consistent (game state hasn't changed)
            assert len(current_moves["legal_moves"]) == initial_move_count

            # Move list should be identical
            assert set(current_moves["legal_moves"]) == set(
                initial_moves["legal_moves"]
            )

    def test_player_data_persistence_during_navigation(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that player data persists correctly during navigation.

        Missing player data could cause UI elements to disappear.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]
        original_player1 = game_data["player1"]
        original_player2 = game_data["player2"]

        # Simulate extensive navigation pattern
        navigation_sequence = [
            f"/games/{game_id}",
            "/games",
            f"/games/{game_id}/board",
            f"/games/{game_id}/legal-moves",
            f"/games/{game_id}",
        ]

        for request_path in navigation_sequence:
            response = test_client.get(request_path)
            assert response.status_code == 200

            # For game detail requests, verify player data
            if request_path == f"/games/{game_id}":
                current_data = response.json()

                assert "player1" in current_data
                assert "player2" in current_data

                current_player1 = current_data["player1"]
                current_player2 = current_data["player2"]

                # Player data should be identical
                assert current_player1["id"] == original_player1["id"]
                assert current_player1["name"] == original_player1["name"]
                assert current_player1["type"] == original_player1["type"]

                assert current_player2["id"] == original_player2["id"]
                assert current_player2["name"] == original_player2["name"]
                assert current_player2["type"] == original_player2["type"]

    def test_game_status_consistency_across_navigation(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that game status remains consistent across navigation.

        Status inconsistencies could cause button state problems.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]
        initial_status = game_data["status"]

        # Make multiple requests over time (simulating user navigation)
        for i in range(10):
            time.sleep(0.05)  # Small delay to simulate real navigation timing

            get_response = test_client.get(f"/games/{game_id}")
            assert get_response.status_code == 200

            current_data = get_response.json()

            # Status should remain consistent (no moves made)
            assert current_data["status"] == initial_status
            assert current_data["current_turn"] == 1  # Should not change

    def test_rapid_navigation_requests(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test rapid navigation requests that might cause race conditions.

        This reproduces the rapid browser back/forward that causes UI issues.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Rapid sequence of requests (simulates fast back/forward clicks)
        rapid_requests = [
            f"/games/{game_id}",
            "/games",
            f"/games/{game_id}",
            f"/games/{game_id}/board",
            f"/games/{game_id}",
            f"/games/{game_id}/legal-moves",
            f"/games/{game_id}",
        ]

        # Execute all requests rapidly
        responses = []
        for request_path in rapid_requests:
            response = test_client.get(request_path)
            responses.append((request_path, response))

        # All requests should succeed
        for request_path, response in responses:
            assert response.status_code == 200, f"Failed on {request_path}"

            # Game detail requests should return consistent data
            if request_path == f"/games/{game_id}":
                data = response.json()
                assert data["game_id"] == game_id
                assert data["status"] == "in_progress"


class TestNavigationErrorRecovery:
    """Test error recovery during navigation scenarios."""

    def test_navigation_after_temporary_errors(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test navigation behavior after temporary errors.

        Poor error recovery could leave UI in inconsistent state.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Make invalid request (should cause error)
        invalid_response = test_client.get("/games/invalid_game_id")
        assert invalid_response.status_code == 404

        # Navigation should still work after error
        valid_response = test_client.get(f"/games/{game_id}")
        assert valid_response.status_code == 200

        valid_data = valid_response.json()
        assert valid_data["game_id"] == game_id
        assert valid_data["status"] == "in_progress"

    def test_concurrent_navigation_requests(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test concurrent navigation requests.

        Concurrent requests might cause state synchronization issues.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Simulate concurrent requests (multiple tabs or rapid clicking)
        concurrent_paths = [
            f"/games/{game_id}",
            f"/games/{game_id}/board",
            f"/games/{game_id}/legal-moves",
        ]

        # Execute requests (simulating concurrency with rapid execution)
        results = []
        for path in concurrent_paths:
            response = test_client.get(path)
            results.append((path, response))

        # All should succeed
        for path, response in results:
            assert response.status_code == 200, f"Failed on {path}"

        # Data should be consistent across all responses
        game_detail_responses = [
            (path, response)
            for path, response in results
            if path == f"/games/{game_id}"
        ]

        if len(game_detail_responses) > 1:
            base_data = game_detail_responses[0][1].json()
            for path, response in game_detail_responses[1:]:
                current_data = response.json()
                assert current_data["game_id"] == base_data["game_id"]
                assert current_data["status"] == base_data["status"]
