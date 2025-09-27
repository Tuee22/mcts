"""
Tests for race conditions that reproduce e2e failures.

These tests focus on reproducing race condition scenarios at the API level
that cause issues in the frontend, particularly around button states and
game creation/management.
"""

import asyncio
import time
from typing import Any, Dict, List
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
        malformed_requests = [
            {},  # Empty request
            {"invalid_field": "value"},  # Invalid fields
            {"player1_type": "invalid"},  # Invalid enum value
        ]

        for malformed_data in malformed_requests:
            response = test_client.post("/games", json=malformed_data)
            # Should return 422 (validation error) not 500 (server error)
            assert response.status_code == 422

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
