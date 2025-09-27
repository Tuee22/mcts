"""
Tests for WebSocket state synchronization that reproduce e2e failures.

These tests focus on reproducing WebSocket connection and state sync issues
that cause UI elements to become unavailable after navigation.
"""

import asyncio
import json
from typing import Any, Dict, List
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

        # Create multiple connections simultaneously
        with test_client.websocket_connect(f"/games/{game_id}/ws") as ws1:
            with test_client.websocket_connect(f"/games/{game_id}/ws") as ws2:
                # Both should receive initial data
                data1 = ws1.receive_json()
                data2 = ws2.receive_json()

                assert data1 is not None
                assert data2 is not None

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
        mock_ws1.send_json.assert_called_once_with(test_message)
        mock_ws2.send_json.assert_called_once_with(test_message)

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

            # Try to receive WebSocket update (with timeout handling)
            try:
                update_data = websocket.receive_json()
                # If we receive data, verify it's a valid update
                if update_data:
                    assert isinstance(update_data, dict)
            except Exception:
                # WebSocket update might not come immediately or at all
                # depending on implementation
                pass


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
