"""
Tests for button state logic that reproduce e2e failures.

These tests focus on reproducing button availability and state issues
such as "Start Game button stuck as disabled" and missing buttons.
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.game_manager import GameManager
from backend.api.game_states import ActiveGame, CompletedGame
from backend.api.models import (
    GameCreateRequest,
    GameResponse,
    GameSettings,
    GameStatus,
    PlayerType,
)


class TestStartGameButtonState:
    """Test Start Game button state logic that causes e2e failures."""

    def test_start_game_button_enabled_conditions(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test conditions that should make Start Game button enabled.

        This reproduces the "Start Game button stuck as disabled" issue
        by verifying the backend conditions that should enable the button.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Verify all conditions that should enable Start Game button
        assert game_data["status"] == "in_progress"  # Game should be active
        assert "player1" in game_data and game_data["player1"] is not None
        assert "player2" in game_data and game_data["player2"] is not None
        assert game_data["current_turn"] in [1, 2]  # Valid turn
        assert "board_display" in game_data  # Board should exist

        # Get detailed game state
        get_response = test_client.get(f"/games/{game_id}")
        assert get_response.status_code == 200

        detailed_state = get_response.json()

        # These backend conditions should result in enabled Start Game button
        assert detailed_state["status"] == "in_progress"
        assert detailed_state["current_turn"] == 1  # Should start with player 1

        # Board state should be valid initial state
        assert "board_display" in detailed_state
        assert detailed_state["board_display"] is not None
        assert isinstance(detailed_state["board_display"], str)

    def test_start_game_button_disabled_conditions(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test conditions that should disable Start Game button.

        This helps identify what might be causing the button to stick disabled.
        """
        # Create and immediately delete game to test invalid state
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Delete the game
        delete_response = test_client.delete(f"/games/{game_id}")
        assert delete_response.status_code == 200

        # Now game should not be found - this should disable Start Game button
        get_response = test_client.get(f"/games/{game_id}")
        assert get_response.status_code == 404

        # This backend condition should result in disabled Start Game button

    def test_start_game_button_after_move_sequence(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test Start Game button state after game moves.

        This reproduces scenarios where button state becomes inconsistent
        after gameplay actions.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]
        player1 = game_data["player1"]
        assert isinstance(player1, dict)
        player1_id = player1["id"]

        # Try to make a move
        move_response = test_client.post(
            f"/games/{game_id}/moves",
            json={"player_id": player1_id, "action": "*(4,1)"},
        )

        # Whether move succeeds or fails, check game state consistency
        get_response = test_client.get(f"/games/{game_id}")
        assert get_response.status_code == 200

        current_state = get_response.json()

        # Game should still be in a valid state for UI
        if current_state["status"] == "in_progress":
            # If game continues, Start Game button should remain functional
            assert current_state["current_turn"] in [1, 2]
            assert "board_display" in current_state
        elif current_state["status"] == "completed":
            # If game ended, button state should reflect completion
            assert "winner" in current_state

    def test_start_game_button_rapid_requests(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test Start Game button state under rapid requests.

        This reproduces race conditions that might cause button to stick
        in "Starting..." state.
        """
        # Simulate rapid game creation requests (like rapid button clicks)
        responses = []
        for i in range(3):
            response = test_client.post("/games", json=pvp_game_request.model_dump())
            responses.append(response)

        # All should succeed and be in proper state
        for response in responses:
            assert response.status_code == 200
            game_data = response.json()

            # Each game should be independently valid
            assert game_data["status"] == "in_progress"
            assert game_data["current_turn"] == 1

            # Verify game state is retrievable and consistent
            game_id = game_data["game_id"]
            get_response = test_client.get(f"/games/{game_id}")
            assert get_response.status_code == 200

            state = get_response.json()
            assert state["status"] == "in_progress"

    async def test_start_game_button_with_ai_player_delay(
        self, test_client: TestClient, pvm_game_request: GameCreateRequest
    ) -> None:
        """
        Test Start Game button with AI player that might cause delays.

        AI initialization delays could cause button to stick in "Starting..." state.
        """
        # Create PvM game (Player vs Machine)
        response = test_client.post("/games", json=pvm_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Even with AI player, game should be created successfully
        assert game_data["status"] == "in_progress"
        player1 = game_data["player1"]
        player2 = game_data["player2"]
        assert isinstance(player1, dict)
        assert isinstance(player2, dict)
        assert player1["type"] == "human"
        assert player2["type"] == "machine"

        # Game should be immediately playable despite AI initialization
        get_response = test_client.get(f"/games/{game_id}")
        assert get_response.status_code == 200

        state = get_response.json()
        assert state["status"] == "in_progress"

        # Legal moves endpoint should be accessible (even if moves are empty)
        moves_response = test_client.get(f"/games/{game_id}/legal-moves")
        assert moves_response.status_code == 200

        moves_data = moves_response.json()
        assert "legal_moves" in moves_data
        # Note: legal_moves might be empty if game hasn't started properly
        assert isinstance(moves_data["legal_moves"], list)


class TestGameSettingsButtonState:
    """Test Game Settings button availability that causes e2e failures."""

    def test_game_settings_button_visibility_conditions(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test conditions that should make Game Settings button visible.

        This reproduces the "Game Settings button not found" issue
        by verifying backend state that should enable the button.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Verify game has data that should enable Game Settings button
        # Settings button is enabled when we have a valid game
        assert game_data["status"] == "in_progress"
        assert game_data["game_id"] is not None

        # Game should be in state where settings are accessible
        assert game_data["status"] == "in_progress"

    def test_game_settings_button_after_navigation_simulation(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test Game Settings button availability after simulated navigation.

        This reproduces the browser navigation issue where buttons disappear.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Simulate what happens during browser navigation:
        # 1. Page is reloaded, need to fetch current game state
        get_response = test_client.get(f"/games/{game_id}")
        assert get_response.status_code == 200

        reloaded_state = get_response.json()

        # After "navigation", all game data should still be available
        assert reloaded_state["status"] == "in_progress"
        assert reloaded_state["game_id"] is not None

        # Game should be modifiable (this enables Game Settings button)
        assert "player1" in reloaded_state
        assert "player2" in reloaded_state

    def test_game_settings_button_with_multiple_games(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test Game Settings button when multiple games exist.

        Multiple games might cause state confusion affecting button visibility.
        """
        # Create multiple games
        game_ids = []
        for i in range(3):
            response = test_client.post("/games", json=pvp_game_request.model_dump())
            assert response.status_code == 200

            game_data = response.json()
            game_ids.append(game_data["game_id"])

        # Each game should independently support Game Settings
        for game_id in game_ids:
            get_response = test_client.get(f"/games/{game_id}")
            assert get_response.status_code == 200

            state = get_response.json()
            assert state["status"] == "in_progress"
            assert state["game_id"] is not None

    def test_game_settings_button_after_game_completion(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test Game Settings button state after game completion.

        Completed games might affect button availability.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]
        player1 = game_data["player1"]
        assert isinstance(player1, dict)
        player1_id = player1["id"]

        # Try to end game via resignation
        resign_response = test_client.post(
            f"/games/{game_id}/resign", json={"player_id": player1_id}
        )

        if resign_response.status_code == 200:
            # If resignation succeeded, check completed game state
            get_response = test_client.get(f"/games/{game_id}")
            assert get_response.status_code == 200

            completed_state = get_response.json()
            assert completed_state["status"] == "completed"

            # Even completed games should retain basic info for review
            assert "game_id" in completed_state


class TestButtonStateConsistency:
    """Test overall button state consistency across the API."""

    def test_button_states_consistent_across_endpoints(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that button state conditions are consistent across all endpoints.

        Inconsistencies between endpoints could cause UI state problems.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Get game state from different endpoints
        get_game_response = test_client.get(f"/games/{game_id}")
        board_response = test_client.get(f"/games/{game_id}/board")
        legal_moves_response = test_client.get(f"/games/{game_id}/legal-moves")

        # All should succeed and return consistent state
        assert get_game_response.status_code == 200
        assert board_response.status_code == 200
        assert legal_moves_response.status_code == 200

        game_state = get_game_response.json()
        board_state = board_response.json()
        legal_moves = legal_moves_response.json()

        # Status should be consistent across endpoints
        assert game_state["status"] == "in_progress"

        # Board data should be consistent
        assert "board_display" in game_state
        assert "board" in board_state  # /games/{id}/board returns 'board' field
        assert "current_turn" in board_state

        # Legal moves should be available for active game
        assert "legal_moves" in legal_moves
        assert isinstance(legal_moves["legal_moves"], list)

    def test_button_states_after_error_conditions(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test button states after various error conditions.

        Errors might leave buttons in inconsistent states.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Try invalid move (should cause error but not break state)
        invalid_move_response = test_client.post(
            f"/games/{game_id}/moves",
            json={"player_id": "invalid_player_id", "action": "*(4,1)"},
        )

        # Move should fail
        assert invalid_move_response.status_code != 200

        # But game state should remain consistent
        get_response = test_client.get(f"/games/{game_id}")
        assert get_response.status_code == 200

        state = get_response.json()
        assert state["status"] == "in_progress"  # Should not be corrupted
        assert state["current_turn"] == 1  # Should not change

        # Buttons should still be functional
        legal_moves_response = test_client.get(f"/games/{game_id}/legal-moves")
        assert legal_moves_response.status_code == 200
