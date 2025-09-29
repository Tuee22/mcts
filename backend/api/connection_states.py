"""
Connection state types using discriminated unions.
Makes illegal connection states unrepresentable.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import FrozenSet, Literal, Optional, Union


@dataclass(frozen=True)
class ClientDisconnected:
    """No active connection."""

    type: Literal["disconnected"] = "disconnected"
    last_seen: Optional[datetime] = None
    disconnect_reason: Optional[str] = None

    def can_connect(self) -> bool:
        """Check if reconnection is allowed."""
        if self.last_seen is None:
            return True  # Never connected before

        # Allow reconnection after 1 second cooldown
        now = datetime.now(timezone.utc)
        cooldown = timedelta(seconds=1)
        return now - self.last_seen > cooldown


@dataclass(frozen=True)
class ClientConnecting:
    """WebSocket handshake in progress."""

    connection_id: str
    type: Literal["connecting"] = "connecting"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attempt_number: int = 1

    def is_timeout(self, timeout_seconds: int = 30) -> bool:
        """Check if connection attempt has timed out."""
        now = datetime.now(timezone.utc)
        return (now - self.started_at).total_seconds() > timeout_seconds


@dataclass(frozen=True)
class ClientConnected:
    """Active WebSocket connection with game subscriptions."""

    client_id: str
    connection_id: str
    type: Literal["connected"] = "connected"
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    game_subscriptions: FrozenSet[str] = field(default_factory=frozenset)
    last_ping: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def subscribe_to_game(self, game_id: str) -> ClientConnected:
        """Add a game subscription immutably."""
        return replace(self, game_subscriptions=self.game_subscriptions | {game_id})

    def unsubscribe_from_game(self, game_id: str) -> ClientConnected:
        """Remove a game subscription immutably."""
        return replace(self, game_subscriptions=self.game_subscriptions - {game_id})

    def update_ping(self) -> ClientConnected:
        """Update last ping timestamp immutably."""
        return replace(self, last_ping=datetime.now(timezone.utc))

    def is_stale(self, timeout_seconds: int = 60) -> bool:
        """Check if connection is stale (no ping recently)."""
        now = datetime.now(timezone.utc)
        return (now - self.last_ping).total_seconds() > timeout_seconds


@dataclass(frozen=True)
class ClientReconnecting:
    """Client attempting to reconnect after disconnection."""

    client_id: str
    last_connection_id: str
    type: Literal["reconnecting"] = "reconnecting"
    attempts: int = 1
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    game_subscriptions: FrozenSet[str] = field(default_factory=frozenset)

    def increment_attempts(self) -> ClientReconnecting:
        """Increment reconnection attempts immutably."""
        return replace(self, attempts=self.attempts + 1)

    def should_give_up(self, max_attempts: int = 5) -> bool:
        """Check if we should stop trying to reconnect."""
        return self.attempts >= max_attempts


# Discriminated union of all connection states
ConnectionState = Union[
    ClientDisconnected, ClientConnecting, ClientConnected, ClientReconnecting
]


# State transition functions


def start_connection(state: ConnectionState, connection_id: str) -> ConnectionState:
    """
    Start a new connection attempt.

    Valid transitions:
    - Disconnected -> Connecting
    - Reconnecting -> Connecting (preserve client_id)
    """
    if isinstance(state, ClientDisconnected):
        if not state.can_connect():
            return state  # Too soon to reconnect
        return ClientConnecting(connection_id=connection_id)

    elif isinstance(state, ClientReconnecting):
        # Preserve client_id for reconnection
        return ClientConnecting(
            connection_id=connection_id, attempt_number=state.attempts + 1
        )

    # Invalid transition
    return state


def establish_connection(
    state: ConnectionState, client_id: str, connection_id: str
) -> ConnectionState:
    """
    Establish a successful connection.

    Valid transitions:
    - Connecting -> Connected
    - Reconnecting -> Connected (restore subscriptions)
    """
    if isinstance(state, ClientConnecting):
        return ClientConnected(client_id=client_id, connection_id=connection_id)

    elif isinstance(state, ClientReconnecting):
        # Restore previous game subscriptions
        return ClientConnected(
            client_id=client_id,
            connection_id=connection_id,
            game_subscriptions=state.game_subscriptions,
        )

    # Invalid transition
    return state


def disconnect_client(
    state: ConnectionState, reason: Optional[str] = None, allow_reconnect: bool = True
) -> ConnectionState:
    """
    Disconnect a client.

    Valid transitions:
    - Connected -> Disconnected (if not allowing reconnect)
    - Connected -> Reconnecting (if allowing reconnect)
    - Connecting -> Disconnected
    """
    if isinstance(state, ClientConnected):
        if allow_reconnect:
            # Transition to reconnecting state
            return ClientReconnecting(
                client_id=state.client_id,
                last_connection_id=state.connection_id,
                game_subscriptions=state.game_subscriptions,
            )
        else:
            # Full disconnection
            return ClientDisconnected(
                last_seen=datetime.now(timezone.utc), disconnect_reason=reason
            )

    elif isinstance(state, (ClientConnecting, ClientReconnecting)):
        # Connection attempt failed
        return ClientDisconnected(
            last_seen=datetime.now(timezone.utc),
            disconnect_reason=reason or "Connection failed",
        )

    # Already disconnected
    return state


def handle_ping(state: ConnectionState) -> ConnectionState:
    """
    Handle a ping message from client.

    Valid transitions:
    - Connected -> Connected (with updated ping time)
    """
    if isinstance(state, ClientConnected):
        return state.update_ping()

    # Invalid state for ping
    return state


def cleanup_stale_connection(
    state: ConnectionState, timeout_seconds: int = 60
) -> ConnectionState:
    """
    Clean up stale connections.

    Valid transitions:
    - Connected -> Reconnecting (if stale)
    - Connecting -> Disconnected (if timeout)
    - Reconnecting -> Disconnected (if max attempts)
    """
    if isinstance(state, ClientConnected):
        if state.is_stale(timeout_seconds):
            return ClientReconnecting(
                client_id=state.client_id,
                last_connection_id=state.connection_id,
                game_subscriptions=state.game_subscriptions,
            )

    elif isinstance(state, ClientConnecting):
        if state.is_timeout(timeout_seconds):
            return ClientDisconnected(
                last_seen=datetime.now(timezone.utc),
                disconnect_reason="Connection timeout",
            )

    elif isinstance(state, ClientReconnecting):
        if state.should_give_up():
            return ClientDisconnected(
                last_seen=datetime.now(timezone.utc),
                disconnect_reason="Max reconnection attempts reached",
            )

    return state


# Type guards


def is_connected(state: ConnectionState) -> bool:
    """Check if client is currently connected."""
    return isinstance(state, ClientConnected)


def can_send_message(state: ConnectionState) -> bool:
    """Check if we can send messages to this client."""
    return isinstance(state, ClientConnected)


def get_client_id(state: ConnectionState) -> Optional[str]:
    """Get client ID if available."""
    if isinstance(state, (ClientConnected, ClientReconnecting)):
        return state.client_id
    return None


def get_game_subscriptions(state: ConnectionState) -> FrozenSet[str]:
    """Get active game subscriptions."""
    if isinstance(state, (ClientConnected, ClientReconnecting)):
        return state.game_subscriptions
    return frozenset()
