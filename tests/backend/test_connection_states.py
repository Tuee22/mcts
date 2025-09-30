"""
Tests for connection state types and transitions.
Verifies that illegal states are unrepresentable.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from backend.api.connection_states import (
    ClientDisconnected,
    ClientConnecting,
    ClientConnected,
    ClientReconnecting,
    ConnectionState,
    start_connection,
    establish_connection,
    disconnect_client,
    handle_ping,
    cleanup_stale_connection,
    is_connected,
    can_send_message,
    get_client_id,
    get_game_subscriptions,
)


class TestConnectionStates:
    """Test connection state representations."""

    def test_disconnected_state_immutable(self) -> None:
        """Test that disconnected state is immutable."""
        state = ClientDisconnected(
            last_seen=datetime.now(timezone.utc), disconnect_reason="Test"
        )

        # Should be frozen - test immutability by attempting invalid operation
        with pytest.raises(AttributeError):
            # Testing that frozen dataclass prevents attribute mutation
            setattr(state, "last_seen", datetime.now(timezone.utc))

    def test_connected_state_subscriptions(self) -> None:
        """Test game subscription management."""
        state = ClientConnected(
            client_id="client-123",
            connection_id="conn-456",
        )

        # Add subscription
        state2 = state.subscribe_to_game("game-1")
        assert "game-1" in state2.game_subscriptions
        assert len(state.game_subscriptions) == 0  # Original unchanged

        # Add another
        state3 = state2.subscribe_to_game("game-2")
        assert len(state3.game_subscriptions) == 2

        # Remove subscription
        state4 = state3.unsubscribe_from_game("game-1")
        assert "game-1" not in state4.game_subscriptions
        assert "game-2" in state4.game_subscriptions

    def test_reconnecting_state_preserves_subscriptions(self) -> None:
        """Test that reconnecting state preserves game subscriptions."""
        subscriptions = frozenset(["game-1", "game-2", "game-3"])
        state = ClientReconnecting(
            client_id="client-123",
            last_connection_id="conn-old",
            game_subscriptions=subscriptions,
        )

        assert state.game_subscriptions == subscriptions
        assert state.attempts == 1

        # Increment attempts
        state2 = state.increment_attempts()
        assert state2.attempts == 2
        assert state2.game_subscriptions == subscriptions  # Preserved

    def test_connection_cooldown(self) -> None:
        """Test reconnection cooldown logic."""
        # Never connected before - can connect
        state = ClientDisconnected()
        assert state.can_connect() is True

        # Just disconnected - cannot reconnect immediately
        now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        state = ClientDisconnected(last_seen=now)

        with patch("backend.api.connection_states.datetime") as mock_dt:
            # Just after disconnect - cannot reconnect
            mock_dt.now.return_value = now
            mock_dt.timezone = timezone
            assert state.can_connect() is False

            # After cooldown - can reconnect
            mock_dt.now.return_value = now + timedelta(seconds=2)
            assert state.can_connect() is True

    def test_connection_timeout(self) -> None:
        """Test connection attempt timeout."""
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        state = ClientConnecting(connection_id="conn-123", started_at=start_time)

        with patch("backend.api.connection_states.datetime") as mock_dt:
            # Not timeout yet
            mock_dt.now.return_value = start_time + timedelta(seconds=29)
            mock_dt.timezone = timezone
            assert state.is_timeout(30) is False

            # Now timeout
            mock_dt.now.return_value = start_time + timedelta(seconds=31)
            assert state.is_timeout(30) is True

    def test_stale_connection_detection(self) -> None:
        """Test stale connection detection."""
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        state = ClientConnected(
            client_id="client-123", connection_id="conn-456", last_ping=initial_time
        )

        with patch("backend.api.connection_states.datetime") as mock_dt:
            # Not stale yet
            mock_dt.now.return_value = initial_time + timedelta(seconds=30)
            mock_dt.timezone = timezone
            assert state.is_stale(60) is False

            # Update ping
            mock_dt.now.return_value = initial_time + timedelta(seconds=30)
            state = state.update_ping()

            # Still not stale
            mock_dt.now.return_value = initial_time + timedelta(seconds=60)
            assert state.is_stale(60) is False

            # Now stale (91 seconds after last ping)
            mock_dt.now.return_value = initial_time + timedelta(seconds=91)
            assert state.is_stale(60) is True

    def test_max_reconnection_attempts(self) -> None:
        """Test max reconnection attempt detection."""
        state = ClientReconnecting(
            client_id="client-123", last_connection_id="conn-old", attempts=3
        )

        assert state.should_give_up(5) is False

        state = state.increment_attempts()
        assert state.attempts == 4
        assert state.should_give_up(5) is False

        state = state.increment_attempts()
        assert state.attempts == 5
        assert state.should_give_up(5) is True


class TestConnectionTransitions:
    """Test connection state transitions."""

    def test_start_connection_from_disconnected(self) -> None:
        """Test starting connection from disconnected state."""
        state = ClientDisconnected(last_seen=None)
        new_state = start_connection(state, "conn-123")

        assert isinstance(new_state, ClientConnecting)
        assert new_state.connection_id == "conn-123"
        assert new_state.attempt_number == 1

    def test_start_connection_from_reconnecting(self) -> None:
        """Test starting connection from reconnecting state."""
        state = ClientReconnecting(
            client_id="client-123", last_connection_id="conn-old", attempts=2
        )
        new_state = start_connection(state, "conn-new")

        assert isinstance(new_state, ClientConnecting)
        assert new_state.connection_id == "conn-new"
        assert new_state.attempt_number == 3

    def test_invalid_start_connection(self) -> None:
        """Test invalid connection start attempts."""
        # Cannot start from connected state
        state = ClientConnected(client_id="client-123", connection_id="conn-456")
        new_state = start_connection(state, "conn-new")
        assert new_state == state  # Unchanged

    def test_establish_connection_from_connecting(self) -> None:
        """Test establishing connection from connecting state."""
        state = ClientConnecting(connection_id="conn-123")
        new_state = establish_connection(state, "client-456", "conn-123")

        assert isinstance(new_state, ClientConnected)
        assert new_state.client_id == "client-456"
        assert new_state.connection_id == "conn-123"
        assert len(new_state.game_subscriptions) == 0

    def test_establish_connection_from_reconnecting(self) -> None:
        """Test establishing connection from reconnecting state."""
        subscriptions = frozenset(["game-1", "game-2"])
        state = ClientReconnecting(
            client_id="client-123",
            last_connection_id="conn-old",
            game_subscriptions=subscriptions,
        )
        new_state = establish_connection(state, "client-123", "conn-new")

        assert isinstance(new_state, ClientConnected)
        assert new_state.client_id == "client-123"
        assert new_state.connection_id == "conn-new"
        assert new_state.game_subscriptions == subscriptions  # Restored

    def test_disconnect_client_allow_reconnect(self) -> None:
        """Test disconnecting client with reconnection allowed."""
        state = ClientConnected(
            client_id="client-123",
            connection_id="conn-456",
            game_subscriptions=frozenset(["game-1"]),
        )
        new_state = disconnect_client(state, allow_reconnect=True)

        assert isinstance(new_state, ClientReconnecting)
        assert new_state.client_id == "client-123"
        assert new_state.last_connection_id == "conn-456"
        assert new_state.game_subscriptions == frozenset(["game-1"])

    def test_disconnect_client_no_reconnect(self) -> None:
        """Test disconnecting client without reconnection."""
        state = ClientConnected(client_id="client-123", connection_id="conn-456")
        new_state = disconnect_client(state, reason="Banned", allow_reconnect=False)

        assert isinstance(new_state, ClientDisconnected)
        assert new_state.disconnect_reason == "Banned"
        assert new_state.last_seen is not None

    def test_disconnect_from_connecting(self) -> None:
        """Test disconnecting from connecting state."""
        state = ClientConnecting(connection_id="conn-123")
        new_state = disconnect_client(state, reason="Timeout")

        assert isinstance(new_state, ClientDisconnected)
        assert new_state.disconnect_reason == "Timeout"

    def test_handle_ping(self) -> None:
        """Test handling ping messages."""
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        state = ClientConnected(
            client_id="client-123", connection_id="conn-456", last_ping=initial_time
        )
        original_ping = state.last_ping

        with patch("backend.api.connection_states.datetime") as mock_dt:
            mock_dt.now.return_value = initial_time + timedelta(seconds=30)
            mock_dt.timezone = timezone
            new_state = handle_ping(state)

            assert isinstance(new_state, ClientConnected)
            assert new_state.last_ping > original_ping
            assert state.last_ping == original_ping  # Original unchanged

    def test_handle_ping_invalid_state(self) -> None:
        """Test handling ping in invalid states."""
        # Cannot ping disconnected client
        state = ClientDisconnected()
        new_state = handle_ping(state)
        assert new_state == state  # Unchanged

    def test_cleanup_stale_connected(self) -> None:
        """Test cleanup of stale connected clients."""
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        state = ClientConnected(
            client_id="client-123",
            connection_id="conn-456",
            game_subscriptions=frozenset(["game-1"]),
            last_ping=initial_time,
        )

        with patch("backend.api.connection_states.datetime") as mock_dt:
            mock_dt.timezone = timezone

            # Not stale yet
            mock_dt.now.return_value = initial_time + timedelta(seconds=30)
            new_state = cleanup_stale_connection(state, timeout_seconds=60)
            assert isinstance(new_state, ClientConnected)

            # Now stale
            mock_dt.now.return_value = initial_time + timedelta(seconds=61)
            new_state = cleanup_stale_connection(state, timeout_seconds=60)
            assert isinstance(new_state, ClientReconnecting)
            assert new_state.game_subscriptions == frozenset(["game-1"])

    def test_cleanup_timeout_connecting(self) -> None:
        """Test cleanup of timed-out connecting state."""
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        state = ClientConnecting(connection_id="conn-123", started_at=initial_time)

        with patch("backend.api.connection_states.datetime") as mock_dt:
            mock_dt.now.return_value = initial_time + timedelta(seconds=31)
            mock_dt.timezone = timezone
            new_state = cleanup_stale_connection(state, timeout_seconds=30)
            assert isinstance(new_state, ClientDisconnected)
            assert new_state.disconnect_reason == "Connection timeout"

    def test_cleanup_max_reconnect_attempts(self) -> None:
        """Test cleanup after max reconnection attempts."""
        state = ClientReconnecting(
            client_id="client-123", last_connection_id="conn-old", attempts=5
        )

        new_state = cleanup_stale_connection(state)
        assert isinstance(new_state, ClientDisconnected)
        assert new_state.disconnect_reason == "Max reconnection attempts reached"


class TestTypeGuards:
    """Test type guard functions."""

    def test_is_connected(self) -> None:
        """Test is_connected type guard."""
        assert is_connected(ClientDisconnected()) is False
        assert is_connected(ClientConnecting(connection_id="c")) is False
        assert is_connected(ClientConnected("c1", "c2")) is True
        assert is_connected(ClientReconnecting("c1", "c2")) is False

    def test_can_send_message(self) -> None:
        """Test can_send_message type guard."""
        assert can_send_message(ClientDisconnected()) is False
        assert can_send_message(ClientConnecting(connection_id="c")) is False
        assert can_send_message(ClientConnected("c1", "c2")) is True
        assert can_send_message(ClientReconnecting("c1", "c2")) is False

    def test_get_client_id(self) -> None:
        """Test getting client ID from state."""
        assert get_client_id(ClientDisconnected()) is None
        assert get_client_id(ClientConnecting(connection_id="c")) is None
        assert get_client_id(ClientConnected("client-123", "c2")) == "client-123"
        assert get_client_id(ClientReconnecting("client-456", "c2")) == "client-456"

    def test_get_game_subscriptions(self) -> None:
        """Test getting game subscriptions from state."""
        assert get_game_subscriptions(ClientDisconnected()) == frozenset()
        assert (
            get_game_subscriptions(ClientConnecting(connection_id="c")) == frozenset()
        )

        connected = ClientConnected(
            "c1", "c2", game_subscriptions=frozenset(["game-1", "game-2"])
        )
        assert get_game_subscriptions(connected) == frozenset(["game-1", "game-2"])

        reconnecting = ClientReconnecting(
            "c1", "c2", game_subscriptions=frozenset(["game-3"])
        )
        assert get_game_subscriptions(reconnecting) == frozenset(["game-3"])


class TestStateTransitionScenarios:
    """Test complete connection lifecycle scenarios."""

    def test_full_connection_lifecycle(self) -> None:
        """Test complete connection lifecycle."""
        # Start disconnected
        state: ConnectionState = ClientDisconnected()

        # Start connection
        state = start_connection(state, "conn-1")
        assert isinstance(state, ClientConnecting)

        # Establish connection
        state = establish_connection(state, "client-1", "conn-1")
        assert isinstance(state, ClientConnected)

        # Subscribe to game
        state = state.subscribe_to_game("game-1")
        assert "game-1" in state.game_subscriptions

        # Handle ping
        state = handle_ping(state)
        assert isinstance(state, ClientConnected)

        # Disconnect with reconnect
        state = disconnect_client(state, allow_reconnect=True)
        assert isinstance(state, ClientReconnecting)
        assert "game-1" in state.game_subscriptions

        # Start reconnection
        state = start_connection(state, "conn-2")
        assert isinstance(state, ClientConnecting)

        # Establish reconnection
        state = establish_connection(state, "client-1", "conn-2")
        assert isinstance(state, ClientConnected)
        assert "game-1" in state.game_subscriptions  # Restored

        # Final disconnect
        state = disconnect_client(state, allow_reconnect=False)
        assert isinstance(state, ClientDisconnected)

    def test_connection_failure_scenario(self) -> None:
        """Test connection failure scenario."""
        # Start connection
        state: ConnectionState = ClientDisconnected()
        state = start_connection(state, "conn-1")

        # Connection times out
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        state = ClientConnecting(connection_id="conn-1", started_at=initial_time)

        with patch("backend.api.connection_states.datetime") as mock_dt:
            mock_dt.now.return_value = initial_time + timedelta(seconds=31)
            mock_dt.timezone = timezone
            state = cleanup_stale_connection(state, timeout_seconds=30)

        assert isinstance(state, ClientDisconnected)
        assert state.disconnect_reason == "Connection timeout"
