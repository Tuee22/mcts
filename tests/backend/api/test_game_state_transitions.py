"""
Tests for game state transitions that reproduce e2e failures.

These tests focus on reproducing the "Start Game button stuck as disabled"
and related state transition issues found in e2e tests.
"""

import asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from backend.api.game_manager import GameManager
from backend.api.game_states import ActiveGame, GameState
from backend.api.models import GameCreateRequest, GameSettings, PlayerType


class TestGameStateTransitions:
    """Test game state management issues that cause e2e failures."""

    async def test_new_game_creation_transitions_properly(
        self,
        test_client: TestClient,
        pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that creating a new game properly transitions states.

        This reproduces the "Start Game button stuck as disabled" issue
        by checking that game creation completes properly.
        """
        # Create initial game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Verify game is in proper active state
        assert game_data["status"] == "in_progress"
        assert game_data["current_turn"] == 1

        # Get game state to verify it's properly initialized
        get_response = test_client.get(f"/games/{game_id}")
        assert get_response.status_code == 200

        game_state = get_response.json()

        # These conditions should make the Start Game button enabled
        # If any fail, it indicates the state issue causing the disabled button
        assert game_state["status"] == "in_progress"
        assert "player1" in game_state
        assert "player2" in game_state
        assert game_state["current_turn"] in [1, 2]

        # The board should be in a valid initial state
        assert "board_state" in game_state
        assert game_state["board_state"] is not None

    async def test_rapid_new_game_creation_race_condition(
        self,
        test_client: TestClient,
        pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test rapid game creation to reproduce race conditions.

        This simulates the scenario where users might click "New Game"
        multiple times rapidly, potentially causing state inconsistencies.
        """
        # Create multiple games in rapid succession
        responses = []
        for i in range(3):
            response = test_client.post("/games", json=pvp_game_request.model_dump())
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            game_data = response.json()

            # Each game should be properly initialized
            assert game_data["status"] == "in_progress"
            assert game_data["current_turn"] == 1

            # Verify the game can be retrieved
            game_id = game_data["game_id"]
            get_response = test_client.get(f"/games/{game_id}")
            assert get_response.status_code == 200

    async def test_game_state_after_new_game_action(
        self,
        test_client: TestClient,
        pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test game state after simulating "New Game" button click.

        This reproduces the specific flow that causes the button to stick
        in "Starting..." state.
        """
        # Create initial game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        first_game_data = response.json()
        first_game_id = first_game_data["game_id"]

        # Make a move to change the game state
        move_response = test_client.post(
            f"/games/{first_game_id}/moves",
            json={
                "player_id": first_game_data["player1"]["id"],
                "action": "*(4,1)"
            }
        )
        # This might fail due to game logic, that's okay for this test

        # Now simulate "New Game" by creating another game
        # This is what the frontend does when New Game is clicked
        new_response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert new_response.status_code == 200

        new_game_data = new_response.json()
        new_game_id = new_game_data["game_id"]

        # The new game should be completely independent and properly initialized
        assert new_game_id != first_game_id
        assert new_game_data["status"] == "in_progress"
        assert new_game_data["current_turn"] == 1

        # The new game should be retrievable and in correct state
        get_response = test_client.get(f"/games/{new_game_id}")
        assert get_response.status_code == 200

        retrieved_state = get_response.json()
        assert retrieved_state["status"] == "in_progress"

    async def test_game_deletion_and_recreation_cycle(
        self,
        test_client: TestClient,
        pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test the cycle of creating, deleting, and recreating games.

        This could reveal issues with cleanup that cause button state problems.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Delete game
        delete_response = test_client.delete(f"/games/{game_id}")
        assert delete_response.status_code == 200

        # Verify game is gone
        get_response = test_client.get(f"/games/{game_id}")
        assert get_response.status_code == 404

        # Create new game - should work properly
        new_response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert new_response.status_code == 200

        new_game_data = new_response.json()
        assert new_game_data["status"] == "in_progress"
        assert new_game_data["current_turn"] == 1

    async def test_concurrent_game_operations(
        self,
        test_client: TestClient,
        pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test concurrent game operations that might cause state issues.

        This simulates the race conditions between REST API and WebSocket
        that could cause button state synchronization problems.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]
        player_id = game_data["player1"]["id"]

        # Simulate concurrent operations:
        # 1. Get game state
        # 2. Try to make a move
        # 3. Get legal moves
        # These could happen simultaneously from frontend

        get_response = test_client.get(f"/games/{game_id}")
        legal_moves_response = test_client.get(f"/games/{game_id}/legal-moves")

        # Both should succeed
        assert get_response.status_code == 200
        assert legal_moves_response.status_code == 200

        # Game state should remain consistent
        game_state = get_response.json()
        assert game_state["status"] == "in_progress"

        # Legal moves should be available
        legal_moves = legal_moves_response.json()
        assert "legal_moves" in legal_moves
        assert len(legal_moves["legal_moves"]) > 0


class TestGameManagerStateConsistency:
    """Test GameManager internal state consistency issues."""

    async def test_game_manager_game_storage_consistency(
        self,
        game_manager: GameManager,
        default_game_settings: GameSettings
    ) -> None:
        """
        Test that GameManager maintains consistent internal state.

        This could reveal issues causing button state problems.
        """
        # Create game through manager
        game = await game_manager.create_game(
            player1_type=PlayerType.HUMAN,
            player2_type=PlayerType.HUMAN,
            player1_name="Alice",
            player2_name="Bob",
            settings=default_game_settings
        )

        assert isinstance(game, ActiveGame)
        assert game.game_id in game_manager._games

        # Retrieved game should be identical
        retrieved_game = game_manager.get_game(game.game_id)
        assert retrieved_game == game

        # State should be consistent
        assert retrieved_game.current_turn == 1
        assert len(retrieved_game.move_history) == 0

    async def test_game_manager_concurrent_access(
        self,
        game_manager: GameManager,
        default_game_settings: GameSettings
    ) -> None:
        """
        Test GameManager under concurrent access patterns.

        This simulates the load that might cause state synchronization issues.
        """
        # Create multiple games concurrently
        tasks = []
        for i in range(5):
            task = game_manager.create_game(
                player1_type=PlayerType.HUMAN,
                player2_type=PlayerType.HUMAN,
                player1_name=f"Player{i}_1",
                player2_name=f"Player{i}_2",
                settings=default_game_settings
            )
            tasks.append(task)

        games = await asyncio.gather(*tasks)

        # All games should be created successfully
        assert len(games) == 5

        # All should be unique and properly stored
        game_ids = [game.game_id for game in games]
        assert len(set(game_ids)) == 5  # All unique

        # All should be retrievable
        for game in games:
            retrieved = game_manager.get_game(game.game_id)
            assert retrieved == game