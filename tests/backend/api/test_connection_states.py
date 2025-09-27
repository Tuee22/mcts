"""
Tests for connection state handling that reproduce e2e failures.

These tests focus on reproducing connection-related scenarios at the API level
that cause issues in the frontend, particularly around WebSocket connectivity
and API response consistency.
"""

import time
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.models import GameCreateRequest, GameSettings, PlayerType


class TestAPIResponseConsistency:
    """Test API response consistency under various conditions."""

    def test_game_creation_returns_complete_data(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that game creation returns all data needed by frontend.

        This reproduces scenarios where missing fields cause button states
        to be incorrect (e.g., "Start Game button stuck as disabled").
        """
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()

        # Verify all essential fields for UI state management
        essential_fields = {
            "game_id": str,
            "status": str,
            "mode": str,
            "player1": dict,
            "player2": dict,
            "current_turn": int,
            "move_count": int,
            "board_display": (str, type(None)),
            "winner": (int, type(None)),
            "created_at": str,
        }

        for field_name, expected_type in essential_fields.items():
            assert field_name in game_data, f"Missing essential field: {field_name}"

            actual_value = game_data[field_name]
            if isinstance(expected_type, tuple):
                # Field can be one of multiple types (e.g., str or None)
                assert (
                    type(actual_value) in expected_type
                ), f"Field {field_name} has type {type(actual_value)}, expected one of {expected_type}"
            else:
                # Use type() for single types to avoid mypy issues
                assert (
                    type(actual_value) == expected_type
                ), f"Field {field_name} has type {type(actual_value)}, expected {expected_type}"

        # Verify player objects have required structure
        for player_key in ["player1", "player2"]:
            player = game_data[player_key]
            assert isinstance(player, dict)
            assert "id" in player
            assert "name" in player
            assert "type" in player
            assert isinstance(player["id"], str)
            assert isinstance(player["name"], str)
            assert isinstance(player["type"], str)

        # Verify status is a valid game state
        assert game_data["status"] in ["waiting", "in_progress", "completed"]

        # Verify current_turn is valid
        assert game_data["current_turn"] in [1, 2]

    def test_game_retrieval_consistency(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that retrieving a game returns consistent data.

        This ensures that GET /games/{id} returns the same structure
        as POST /games, preventing frontend state inconsistencies.
        """
        # Create game
        create_response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert create_response.status_code == 200

        created_data = create_response.json()
        game_id = created_data["game_id"]

        # Retrieve game
        get_response = test_client.get(f"/games/{game_id}")
        assert get_response.status_code == 200

        retrieved_data = get_response.json()

        # Both responses should have the same structure
        assert set(created_data.keys()) == set(retrieved_data.keys())

        # Core fields should be identical
        consistent_fields = [
            "game_id",
            "status",
            "mode",
            "current_turn",
            "move_count",
            "created_at",
        ]

        for field in consistent_fields:
            assert (
                created_data[field] == retrieved_data[field]
            ), f"Field {field} differs: {created_data[field]} vs {retrieved_data[field]}"

        # Player data should be consistent
        created_player1 = created_data["player1"]
        created_player2 = created_data["player2"]
        retrieved_player1 = retrieved_data["player1"]
        retrieved_player2 = retrieved_data["player2"]
        assert isinstance(created_player1, dict)
        assert isinstance(created_player2, dict)
        assert isinstance(retrieved_player1, dict)
        assert isinstance(retrieved_player2, dict)
        assert created_player1["id"] == retrieved_player1["id"]
        assert created_player2["id"] == retrieved_player2["id"]

    def test_board_endpoint_structure(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that board endpoint returns expected structure.

        This ensures the frontend can rely on specific fields for
        rendering and button state management.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Get board state
        board_response = test_client.get(f"/games/{game_id}/board")
        assert board_response.status_code == 200

        board_data = board_response.json()

        # Verify expected board structure
        expected_board_fields = {
            "game_id": str,
            "board": str,
            "current_turn": int,
            "move_count": int,
        }

        for field_name, expected_type in expected_board_fields.items():
            assert field_name in board_data, f"Missing board field: {field_name}"
            assert isinstance(
                board_data[field_name], expected_type
            ), f"Board field {field_name} has type {type(board_data[field_name])}, expected {expected_type}"

        # Board data should be consistent with game data
        assert board_data["game_id"] == game_id
        assert board_data["current_turn"] == game_data["current_turn"]
        assert board_data["move_count"] == game_data["move_count"]

    def test_legal_moves_endpoint_structure(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that legal moves endpoint returns expected structure.

        This ensures move validation and UI state work correctly.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Get legal moves
        moves_response = test_client.get(f"/games/{game_id}/legal-moves")
        assert moves_response.status_code == 200

        moves_data = moves_response.json()

        # Verify expected moves structure
        expected_moves_fields = {
            "game_id": str,
            "current_player": int,
            "legal_moves": list,
        }

        for field_name, expected_type in expected_moves_fields.items():
            assert field_name in moves_data, f"Missing moves field: {field_name}"
            assert isinstance(
                moves_data[field_name], expected_type
            ), f"Moves field {field_name} has type {type(moves_data[field_name])}, expected {expected_type}"

        # Moves data should be consistent with game data
        assert moves_data["game_id"] == game_id

        # Legal moves should be a list of strings (even if empty)
        legal_moves = moves_data["legal_moves"]
        assert isinstance(legal_moves, list)
        for move in legal_moves:
            assert isinstance(
                move, str
            ), f"Legal move should be string, got {type(move)}"


class TestGameStateValidation:
    """Test game state validation that affects UI behavior."""

    def test_game_has_valid_initial_state(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that newly created games have valid initial state.

        Invalid initial state can cause buttons to be disabled when
        they should be enabled.
        """
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()

        # New games should be in progress
        assert game_data["status"] == "in_progress"

        # Should start at turn 1
        assert game_data["current_turn"] == 1

        # Should have 0 moves initially
        assert game_data["move_count"] == 0

        # Should have no winner yet
        assert game_data["winner"] is None

        # Board display should be present (even if None initially)
        assert "board_display" in game_data

        # Players should be properly initialized
        player1 = game_data["player1"]
        player2 = game_data["player2"]
        assert isinstance(player1, dict)
        assert isinstance(player2, dict)
        assert player1["id"] is not None
        assert player2["id"] is not None
        assert player1["name"] == pvp_game_request.player1_name
        assert player2["name"] == pvp_game_request.player2_name

    def test_game_accessibility_after_creation(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that games remain accessible after creation.

        This reproduces scenarios where games become inaccessible,
        causing UI elements to show error states.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Game should be immediately accessible via all endpoints
        endpoints_to_test = [
            f"/games/{game_id}",
            f"/games/{game_id}/board",
            f"/games/{game_id}/legal-moves",
        ]

        for endpoint in endpoints_to_test:
            endpoint_response = test_client.get(endpoint)
            assert (
                endpoint_response.status_code == 200
            ), f"Endpoint {endpoint} should be accessible immediately after game creation"

        # Game should appear in game list
        list_response = test_client.get("/games")
        assert list_response.status_code == 200

        games_list = list_response.json()
        assert "games" in games_list
        assert isinstance(games_list["games"], list)

        games_array = games_list["games"]
        game_ids_in_list = {game["game_id"] for game in games_array}
        assert game_id in game_ids_in_list, "Created game should appear in game list"

    def test_multiple_games_independence(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that multiple games don't interfere with each other.

        This reproduces scenarios where creating new games affects
        the state or accessibility of existing games.
        """
        # Create first game
        response1 = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response1.status_code == 200
        game1_data = response1.json()
        game1_id = game1_data["game_id"]

        # Create second game
        response2 = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response2.status_code == 200
        game2_data = response2.json()
        game2_id = game2_data["game_id"]

        # Games should have different IDs
        assert game1_id != game2_id

        # Both games should remain independently accessible
        get1_response = test_client.get(f"/games/{game1_id}")
        get2_response = test_client.get(f"/games/{game2_id}")

        assert get1_response.status_code == 200
        assert get2_response.status_code == 200

        retrieved1 = get1_response.json()
        retrieved2 = get2_response.json()

        # Each game should maintain its own state
        assert retrieved1["game_id"] == game1_id
        assert retrieved2["game_id"] == game2_id
        assert retrieved1["current_turn"] == 1
        assert retrieved2["current_turn"] == 1

        # Both should appear in game list
        list_response = test_client.get("/games")
        assert list_response.status_code == 200

        response_data = list_response.json()
        assert isinstance(response_data, dict)
        assert "games" in response_data
        games_list = response_data["games"]
        assert isinstance(games_list, list)
        game_ids_in_list = {game["game_id"] for game in games_list}

        assert game1_id in game_ids_in_list
        assert game2_id in game_ids_in_list


class TestErrorRecovery:
    """Test error recovery scenarios that affect connection states."""

    def test_invalid_game_requests_dont_affect_valid_games(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that invalid requests don't corrupt valid game states.

        This ensures that network errors or invalid requests don't
        cause existing games to become inaccessible.
        """
        # Create a valid game first
        valid_response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert valid_response.status_code == 200

        valid_game = valid_response.json()
        valid_id = valid_game["game_id"]

        # Make various invalid requests
        invalid_requests = [
            ("GET", f"/games/invalid-game-id", None),
            ("GET", f"/games/{valid_id}/invalid-endpoint", None),
            ("POST", "/games", {"invalid": "data"}),
        ]

        for method, path, data in invalid_requests:
            if method == "GET":
                response = test_client.get(path)
            elif method == "POST":
                response = test_client.post(path, json=data if data else {})

            # Should get appropriate error codes, not server errors
            assert response.status_code in [
                404,
                422,
            ], f"Request {method} {path} should return client error, got {response.status_code}"

        # Valid game should still be accessible and unchanged
        check_response = test_client.get(f"/games/{valid_id}")
        assert check_response.status_code == 200

        current_state = check_response.json()
        assert current_state["game_id"] == valid_id
        assert current_state["status"] == "in_progress"
        assert current_state["current_turn"] == valid_game["current_turn"]

    def test_server_state_consistency_after_errors(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that server state remains consistent after handling errors.

        This ensures that error conditions don't leave the server in
        a state that affects subsequent valid operations.
        """
        # Try to create games with invalid data
        invalid_data_sets = [
            {},  # Empty
            {"player1_type": "invalid"},  # Invalid enum
            {"player1_type": "human", "player2_type": "invalid"},  # Partial invalid
        ]

        for invalid_data in invalid_data_sets:
            response = test_client.post("/games", json=invalid_data)
            assert response.status_code == 422  # Validation error

        # Server should still be able to handle valid requests
        valid_response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert valid_response.status_code == 200

        game_data = valid_response.json()
        assert "game_id" in game_data
        assert game_data["status"] == "in_progress"

        # All endpoints should work normally
        game_id = game_data["game_id"]
        endpoints = [
            f"/games/{game_id}",
            f"/games/{game_id}/board",
            f"/games/{game_id}/legal-moves",
            "/games",
        ]

        for endpoint in endpoints:
            response = test_client.get(endpoint)
            assert (
                response.status_code == 200
            ), f"Endpoint {endpoint} should work after error recovery"

    def test_concurrent_valid_and_invalid_requests(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test handling of mixed valid and invalid requests.

        This simulates real-world scenarios where some requests succeed
        and others fail, ensuring server stability.
        """
        # Create a valid game for testing
        create_response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert create_response.status_code == 200

        valid_game = create_response.json()
        valid_id = valid_game["game_id"]

        # Mix of valid and invalid requests
        mixed_requests = [
            ("GET", f"/games/{valid_id}", 200),  # Valid
            ("GET", "/games/invalid-id", 404),  # Invalid
            ("GET", f"/games/{valid_id}/board", 200),  # Valid
            ("GET", "/games/invalid-id/board", 404),  # Invalid
            ("GET", f"/games/{valid_id}/legal-moves", 200),  # Valid
            ("GET", "/games", 200),  # Valid
        ]

        results = []
        for method, path, expected_status in mixed_requests:
            response = test_client.get(path)
            results.append((path, response.status_code, expected_status))
            assert (
                response.status_code == expected_status
            ), f"Request {path} returned {response.status_code}, expected {expected_status}"

        # Verify that valid game state wasn't affected by invalid requests
        final_response = test_client.get(f"/games/{valid_id}")
        assert final_response.status_code == 200

        final_state = final_response.json()
        assert final_state["game_id"] == valid_id
        assert final_state["status"] == valid_game["status"]
        assert final_state["current_turn"] == valid_game["current_turn"]


class TestPerformanceUnderLoad:
    """Test performance characteristics that affect user experience."""

    def test_response_time_consistency(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that response times remain reasonable under typical load.

        Slow responses can cause timeouts that affect button states
        and connection indicators in the frontend.
        """
        # Create a game for testing
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Test multiple requests to measure consistency
        endpoints = [
            f"/games/{game_id}",
            f"/games/{game_id}/board",
            f"/games/{game_id}/legal-moves",
        ]

        response_times = []
        for _ in range(5):  # Test each endpoint multiple times
            for endpoint in endpoints:
                start_time = time.time()
                response = test_client.get(endpoint)
                end_time = time.time()

                assert response.status_code == 200
                response_times.append(end_time - start_time)

        # All responses should be reasonably fast (under 1 second for tests)
        for response_time in response_times:
            assert response_time < 1.0, f"Response time {response_time:.3f}s too slow"

        # Response times should be relatively consistent
        if len(response_times) > 1:
            avg_time = sum(response_times) / len(response_times)
            max_deviation = max(abs(t - avg_time) for t in response_times)

            # Maximum deviation shouldn't be more than 500ms from average
            assert (
                max_deviation < 0.5
            ), f"Response time inconsistency: {max_deviation:.3f}s deviation"
