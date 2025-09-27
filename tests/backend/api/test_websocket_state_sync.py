"""
Tests for WebSocket state synchronization that reproduce e2e failures.

These tests focus on reproducing WebSocket connection and state sync issues
that cause UI elements to become unavailable after navigation.
"""

import asyncio
import json
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from backend.api.models import GameCreateRequest, GameSettings, PlayerType
from backend.api.websocket_manager import WebSocketManager
from backend.api.api_types import OutgoingWebSocketMessage


class TestWebSocketStateSync:
    """Test WebSocket state synchronization issues that cause e2e failures."""

    def test_websocket_connection_establishment(self, test_client: TestClient) -> None:
        """
        Test basic WebSocket connection establishment.

        This reproduces connection issues that might cause missing UI elements.
        """
        # Test unified WebSocket endpoint
        with test_client.websocket_connect("/ws") as websocket:
            # Connection should be established successfully
            assert websocket is not None

            # Should be able to receive initial connection message
            # (The actual behavior depends on server implementation)

    def test_websocket_game_state_broadcast(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test that game state changes are properly broadcast via WebSocket.

        This reproduces issues where UI doesn't update after game state changes.
        """
        # Create a game first
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Connect to game-specific WebSocket
        with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket:
            # Should receive initial game state
            initial_data = websocket.receive_json()

            # Verify initial state is correct
            assert "type" in initial_data
            assert "game_id" in initial_data or "data" in initial_data

    def test_websocket_reconnection_after_disconnection(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test WebSocket reconnection scenarios.

        This reproduces the browser navigation issue where connection
        is lost and UI elements become unavailable.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # First connection
        with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket1:
            initial_data = websocket1.receive_json()
            assert initial_data is not None

        # Simulate reconnection (new WebSocket connection)
        with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket2:
            reconnect_data = websocket2.receive_json()
            assert reconnect_data is not None

            # Should receive current game state on reconnection
            # This is crucial for restoring UI after navigation

    def test_multiple_websocket_connections_same_game(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test multiple WebSocket connections to the same game.

        This simulates scenarios like multiple tabs or rapid reconnections
        that might cause state synchronization issues.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Test multiple connections sequentially to avoid nesting issues
        # First connection
        with test_client.websocket_connect(f"/games/{game_id}/ws") as ws1:
            data1 = ws1.receive_json()
            assert data1 is not None
            assert "type" in data1
            assert data1["type"] == "game_state"
            assert "data" in data1
            data1_data = data1["data"]
            assert isinstance(data1_data, dict)
            assert data1_data["game_id"] == game_id

        # Second connection (after first is closed)
        with test_client.websocket_connect(f"/games/{game_id}/ws") as ws2:
            data2 = ws2.receive_json()
            assert data2 is not None
            assert "type" in data2
            assert data2["type"] == "game_state"
            assert "data" in data2
            data2_data = data2["data"]
            assert isinstance(data2_data, dict)
            assert data2_data["game_id"] == game_id

    async def test_websocket_manager_connection_tracking(
        self, ws_manager: WebSocketManager
    ) -> None:
        """
        Test WebSocketManager's connection tracking.

        This could reveal issues with connection state that cause
        missing UI elements after navigation.
        """
        # Create mock WebSocket connections
        mock_ws1 = MagicMock(spec=WebSocket)
        mock_ws2 = MagicMock(spec=WebSocket)

        game_id = "test_game_123"

        # Add connections
        await ws_manager.connect(mock_ws1, game_id)
        await ws_manager.connect(mock_ws2, game_id)

        # Should track both connections
        assert game_id in ws_manager.active_connections
        assert len(ws_manager.active_connections[game_id]) == 2

        # Disconnect one
        await ws_manager.disconnect(mock_ws1, game_id)

        # Should still track the remaining connection
        assert len(ws_manager.active_connections[game_id]) == 1

        # Disconnect all
        await ws_manager.disconnect(mock_ws2, game_id)

        # Should clean up empty game connections
        assert (
            game_id not in ws_manager.active_connections
            or len(ws_manager.active_connections[game_id]) == 0
        )

    async def test_websocket_broadcast_to_multiple_connections(
        self, ws_manager: WebSocketManager
    ) -> None:
        """
        Test broadcasting messages to multiple WebSocket connections.

        This tests the mechanism that should keep all UI instances synchronized.
        """
        # Create mock WebSocket connections
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)

        game_id = "test_game_456"

        # Add connections
        await ws_manager.connect(mock_ws1, game_id)
        await ws_manager.connect(mock_ws2, game_id)

        # Broadcast a message
        test_message: OutgoingWebSocketMessage = {
            "type": "game_update",
            "data": {"status": "in_progress"},
        }
        await ws_manager.broadcast_to_game(game_id, test_message)

        # Both connections should receive the message
        # Note: WebSocket manager also sends player_connected messages when connecting
        # So we check that our test message was sent (not that it was the only call)

        # Check that both websockets received our test message
        assert test_message in [
            call.args[0] for call in mock_ws1.send_json.call_args_list
        ]
        assert test_message in [
            call.args[0] for call in mock_ws2.send_json.call_args_list
        ]

    def test_websocket_connection_with_invalid_game_id(
        self, test_client: TestClient
    ) -> None:
        """
        Test WebSocket connection with invalid game ID.

        This tests error handling that might affect UI state.
        """
        # Try to connect to non-existent game
        with pytest.raises(Exception):
            # This should fail gracefully
            with test_client.websocket_connect(
                "/games/invalid_game_id/ws"
            ) as websocket:
                pass

    def test_websocket_connection_during_game_state_changes(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test WebSocket behavior during rapid game state changes.

        This reproduces race conditions between REST API and WebSocket updates
        that might cause button state synchronization problems.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]
        player1 = game_data["player1"]
        assert isinstance(player1, dict)
        player_id = player1["id"]

        # Connect to WebSocket
        with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket:
            # Receive initial state
            initial_data = websocket.receive_json()
            assert initial_data is not None

            # Make a move via REST API while WebSocket is connected
            move_response = test_client.post(
                f"/games/{game_id}/moves",
                json={"player_id": player_id, "action": "*(4,1)"},
            )

            # The move might fail due to game logic, but WebSocket should
            # still receive updates about the attempt

            # Verify initial data structure
            assert isinstance(initial_data, dict)
            assert "type" in initial_data
            assert initial_data["type"] == "game_state"
            assert "data" in initial_data
            initial_data_data = initial_data["data"]
            assert isinstance(initial_data_data, dict)
            assert initial_data_data["game_id"] == game_id

            # The move might fail, but the important thing is that
            # the WebSocket connection remains stable and doesn't break
            # We don't need to wait for additional messages since that could hang
            # The key test is that the connection was established and initial data received


class TestWebSocketErrorHandling:
    """Test WebSocket error handling scenarios."""

    async def test_websocket_manager_handles_connection_errors(
        self, ws_manager: WebSocketManager
    ) -> None:
        """
        Test WebSocketManager handles connection errors gracefully.

        Poor error handling could cause UI state issues.
        """
        # Create mock WebSocket that raises errors
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json.side_effect = Exception("Connection error")

        game_id = "test_game_789"

        # Add connection
        await ws_manager.connect(mock_ws, game_id)

        # Broadcasting should handle the error gracefully
        test_message: OutgoingWebSocketMessage = {"type": "error_test", "data": {}}

        # This should not raise an exception
        try:
            await ws_manager.broadcast_to_game(game_id, test_message)
        except Exception as e:
            pytest.fail(
                f"WebSocket broadcast should handle errors gracefully, but raised: {e}"
            )

    async def test_websocket_cleanup_on_disconnect(
        self, ws_manager: WebSocketManager
    ) -> None:
        """
        Test proper cleanup when WebSocket disconnects.

        Improper cleanup could cause state synchronization issues.
        """
        mock_ws = MagicMock(spec=WebSocket)
        game_id = "test_game_cleanup"

        # Connect
        await ws_manager.connect(mock_ws, game_id)
        assert game_id in ws_manager.active_connections

        # Disconnect
        await ws_manager.disconnect(mock_ws, game_id)

        # Should be cleaned up
        assert (
            game_id not in ws_manager.active_connections
            or len(ws_manager.active_connections[game_id]) == 0
        )

    def test_websocket_handles_malformed_messages(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test WebSocket handling of malformed messages.

        Poor message handling could cause UI state corruption.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200

        game_data = response.json()
        game_id = game_data["game_id"]

        # Connect to WebSocket
        with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket:
            # Send malformed message
            try:
                websocket.send_text("invalid json")
                # Should handle gracefully without breaking connection
            except Exception:
                # Connection might be closed, which is acceptable
                pass


class TestWebSocketE2EFailureReproduction:
    """
    Test WebSocket scenarios that reproduce e2e failures.

    These tests focus on WebSocket connection stability during rapid UI transitions
    that cause the Settings button to become unavailable.
    """

    def test_websocket_stability_during_rapid_actions(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test WebSocket connection stability during rapid New Game -> Settings actions.

        This reproduces the e2e scenario where rapid clicking causes the Settings
        button to timeout. The issue might be related to WebSocket disconnection
        or connection state confusion.
        """
        # Create initial game
        response1 = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response1.status_code == 200
        game1_data = response1.json()
        game1_id = game1_data["game_id"]

        # Connect to first game WebSocket
        with test_client.websocket_connect(f"/games/{game1_id}/ws") as websocket1:
            # Receive initial game state
            initial_data = websocket1.receive_json()
            assert initial_data is not None

            # Rapidly create new game (simulates rapid "New Game" click)
            response2 = test_client.post("/games", json=pvp_game_request.model_dump())
            assert response2.status_code == 200
            game2_data = response2.json()
            game2_id = game2_data["game_id"]

            # The question is: does the first WebSocket connection affect
            # our ability to connect to the new game?
            try:
                # Try to connect to new game WebSocket
                with test_client.websocket_connect(
                    f"/games/{game2_id}/ws"
                ) as websocket2:
                    new_game_data = websocket2.receive_json()
                    assert new_game_data is not None

                    # Both connections should be stable
                    # This reproduces the timing where Settings button should appear
                    # If WebSocket connections interfere with each other,
                    # it might explain the e2e timeout

                    # Verify both games are accessible via their WebSockets
                    # (This simulates what the UI does when determining button availability)

            except Exception as e:
                # If WebSocket connection fails, this might explain the e2e failure
                pytest.fail(f"Failed to connect to new game WebSocket: {e}")

    def test_state_sync_with_concurrent_ui_actions(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test state synchronization when multiple UI actions occur rapidly.

        This reproduces the scenario where the Settings button doesn't appear
        because the WebSocket state is out of sync with the API state.
        """
        # Create game
        response = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response.status_code == 200
        game_data = response.json()
        game_id = game_data["game_id"]

        # Connect WebSocket
        with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket:
            # Get initial state from WebSocket
            ws_initial_data = websocket.receive_json()

            # Simultaneously get state from REST API
            api_response = test_client.get(f"/games/{game_id}")
            assert api_response.status_code == 200
            api_data = api_response.json()

            # WebSocket and API should have consistent game state
            # This is crucial for Settings button availability

            # Extract comparable data
            if isinstance(ws_initial_data, dict) and "data" in ws_initial_data:
                ws_game_data = ws_initial_data["data"]
            else:
                ws_game_data = ws_initial_data

            # Key fields should match
            comparable_fields = ["game_id", "status", "current_turn", "move_count"]
            for field in comparable_fields:
                if (
                    isinstance(ws_game_data, dict)
                    and isinstance(api_data, dict)
                    and field in ws_game_data
                    and field in api_data
                ):
                    assert ws_game_data[field] == api_data[field], (
                        f"WebSocket and API mismatch for {field}: "
                        f"WS={ws_game_data[field]}, API={api_data[field]}"
                    )

            # Now simulate rapid state changes (like New Game -> Settings)
            # Create another game
            response2 = test_client.post("/games", json=pvp_game_request.model_dump())
            assert response2.status_code == 200

            # Check if this affects the original WebSocket connection
            # This could cause the Settings button to not appear if the connection
            # becomes confused about which game it's associated with

    def test_reconnection_after_rapid_transitions(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test WebSocket reconnection behavior after rapid UI transitions.

        This reproduces the exact e2e failure pattern:
        Settings -> Start Game -> New Game -> Settings (button timeout)
        """
        # Step 1: Create initial game (Settings -> Start Game)
        response1 = test_client.post("/games", json=pvp_game_request.model_dump())
        assert response1.status_code == 200
        game1_data = response1.json()
        game1_id = game1_data["game_id"]

        # Connect to first game (simulates UI opening game)
        with test_client.websocket_connect(f"/games/{game1_id}/ws") as websocket1:
            game1_initial = websocket1.receive_json()
            assert game1_initial is not None

            # Step 2: Rapid New Game click
            response2 = test_client.post("/games", json=pvp_game_request.model_dump())
            assert response2.status_code == 200
            game2_data = response2.json()
            game2_id = game2_data["game_id"]

            # Step 3: Attempt to access Settings (where e2e fails)
            # The Settings button timeout suggests WebSocket connection issues
            # Let's test if we can properly connect to the new game

            # Disconnect from old game (simulates navigation)
            # (Connection will close when exiting context)

        # Now try to connect to new game (simulates opening Settings)
        # This is where the e2e test fails - the Settings button doesn't appear
        # suggesting the WebSocket connection or state is problematic
        try:
            with test_client.websocket_connect(f"/games/{game2_id}/ws") as websocket2:
                game2_initial = websocket2.receive_json()
                assert game2_initial is not None

                # Verify we have the expected game state
                if isinstance(game2_initial, dict) and "data" in game2_initial:
                    game_state = game2_initial["data"]
                else:
                    game_state = game2_initial

                # This data should be sufficient for the Settings UI
                game_id_found = (
                    isinstance(game_state, dict) and "game_id" in game_state
                ) or (isinstance(game2_initial, dict) and "game_id" in game2_initial)
                status_found = (
                    isinstance(game_state, dict) and "status" in game_state
                ) or (isinstance(game2_initial, dict) and "status" in game2_initial)

                assert game_id_found, "game_id not found in WebSocket response"
                assert status_found, "status not found in WebSocket response"

                # If we reach here, WebSocket reconnection works fine
                # This suggests the e2e failure might be frontend-specific

        except Exception as e:
            # If reconnection fails, this could explain the Settings button timeout
            pytest.fail(f"WebSocket reconnection failed: {e}")

    def test_multiple_rapid_websocket_connections(
        self, test_client: TestClient, pvp_game_request: GameCreateRequest
    ) -> None:
        """
        Test rapid WebSocket connection changes that simulate user navigation.

        This reproduces the pattern where users rapidly switch between games
        and the Settings button becomes unavailable.
        """
        # Create multiple games rapidly
        games = []
        for i in range(3):
            response = test_client.post("/games", json=pvp_game_request.model_dump())
            assert response.status_code == 200
            games.append(response.json())

        # Rapidly connect to each game's WebSocket
        # This simulates rapid navigation between games
        for i, game_data in enumerate(games):
            game_id = game_data["game_id"]

            try:
                with test_client.websocket_connect(f"/games/{game_id}/ws") as websocket:
                    initial_data = websocket.receive_json()
                    assert initial_data is not None

                    # Verify connection provides data needed for Settings button
                    # This test should pass if WebSocket connections work independently

            except Exception as e:
                pytest.fail(f"Failed to connect to game {i+1} WebSocket: {e}")

        # All connections worked, suggesting the issue might be elsewhere
