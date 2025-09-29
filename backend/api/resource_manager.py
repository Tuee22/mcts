"""
Immutable resource pool management to prevent leaks.
All operations return new pool instances.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, FrozenSet, Generic, Optional, Tuple, TypeVar

from backend.api.connection_states import ConnectionState, ClientConnected, is_connected
from backend.api.game_states import GameState, ActiveGame, CompletedGame

logger = logging.getLogger(__name__)

# Type variable for generic resource filtering
T = TypeVar("T")


class ResourceExhaustedError(Exception):
    """Raised when resource limits are exceeded."""

    pass


class ResourceNotFoundError(Exception):
    """Raised when a requested resource doesn't exist."""

    pass


@dataclass(frozen=True)
class CleanupResult(Generic[T]):
    """Immutable result of cleanup operation with generic typing."""

    kept: Dict[str, T]
    removed_count: int
    removed_ids: FrozenSet[str]


def partition_by_staleness(
    items: Dict[str, T], is_stale_fn: Callable[[str, T], bool]
) -> CleanupResult[T]:
    """
    Partition items into kept and removed using a pure predicate.

    This is a pure function that creates new dictionaries without mutation.
    """
    kept = {k: v for k, v in items.items() if not is_stale_fn(k, v)}
    removed_ids = frozenset(k for k, v in items.items() if is_stale_fn(k, v))

    return CleanupResult(
        kept=kept, removed_count=len(removed_ids), removed_ids=removed_ids
    )


@dataclass(frozen=True)
class ResourceMetrics:
    """Metrics for resource usage."""

    total_games: int = 0
    active_games: int = 0
    completed_games: int = 0
    total_connections: int = 0
    active_connections: int = 0
    games_per_client: Dict[str, int] = field(default_factory=dict)
    memory_usage_bytes: int = 0
    last_cleanup: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ResourcePool:
    """
    Immutable resource pool preventing leaks.
    All modifications return new pool instances.
    """

    # Resources
    games: Dict[str, GameState] = field(default_factory=dict)
    connections: Dict[str, ConnectionState] = field(default_factory=dict)
    game_connections: Dict[str, FrozenSet[str]] = field(default_factory=dict)

    # Limits
    max_games_per_client: int = 5
    max_total_games: int = 1000
    max_connections_per_game: int = 10
    max_total_connections: int = 100

    # Metrics
    metrics: ResourceMetrics = field(default_factory=ResourceMetrics)

    def can_create_game(self, client_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a client can create a new game.
        Returns (allowed, reason_if_denied).
        """
        # Check total games limit
        if len(self.games) >= self.max_total_games:
            return False, f"Maximum total games reached ({self.max_total_games})"

        # Count client's active games
        client_games = sum(
            1
            for game in self.games.values()
            if isinstance(game, ActiveGame)
            and (game.player1.id == client_id or game.player2.id == client_id)
        )

        if client_games >= self.max_games_per_client:
            return (
                False,
                f"Maximum games per client reached ({self.max_games_per_client})",
            )

        return True, None

    def can_add_connection(self, connection_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a new connection can be added.
        Returns (allowed, reason_if_denied).
        """
        if len(self.connections) >= self.max_total_connections:
            return False, f"Maximum connections reached ({self.max_total_connections})"

        if connection_id in self.connections:
            return False, f"Connection {connection_id} already exists"

        return True, None

    def can_join_game(
        self, game_id: str, connection_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a connection can join a game.
        Returns (allowed, reason_if_denied).
        """
        if game_id not in self.games:
            return False, f"Game {game_id} not found"

        current_connections = self.game_connections.get(game_id, frozenset())
        if len(current_connections) >= self.max_connections_per_game:
            return (
                False,
                f"Maximum connections for game reached ({self.max_connections_per_game})",
            )

        return True, None

    def add_game(self, game: GameState) -> ResourcePool:
        """Add a game immutably with validation."""
        can_add, reason = self.can_create_game(
            game.player1.id
            if isinstance(game, (ActiveGame, CompletedGame))
            else "unknown"
        )

        if not can_add:
            raise ResourceExhaustedError(reason)

        new_games = {**self.games, game.game_id: game}
        new_metrics = replace(
            self.metrics,
            total_games=self.metrics.total_games + 1,
            active_games=self.metrics.active_games
            + (1 if isinstance(game, ActiveGame) else 0),
            completed_games=self.metrics.completed_games
            + (1 if isinstance(game, CompletedGame) else 0),
        )

        return replace(self, games=new_games, metrics=new_metrics)

    def remove_game(self, game_id: str) -> ResourcePool:
        """Remove a game immutably."""
        if game_id not in self.games:
            return self  # Already removed

        game = self.games[game_id]
        new_games = {k: v for k, v in self.games.items() if k != game_id}
        new_game_connections = {
            k: v for k, v in self.game_connections.items() if k != game_id
        }

        new_metrics = replace(
            self.metrics,
            total_games=max(0, self.metrics.total_games - 1),
            active_games=max(
                0,
                self.metrics.active_games - (1 if isinstance(game, ActiveGame) else 0),
            ),
            completed_games=max(
                0,
                self.metrics.completed_games
                - (1 if isinstance(game, CompletedGame) else 0),
            ),
        )

        return replace(
            self,
            games=new_games,
            game_connections=new_game_connections,
            metrics=new_metrics,
        )

    def update_game(self, game: GameState) -> ResourcePool:
        """Update a game immutably."""
        if game.game_id not in self.games:
            raise ResourceNotFoundError(f"Game {game.game_id} not found")

        old_game = self.games[game.game_id]
        new_games = {**self.games, game.game_id: game}

        # Update metrics if game status changed
        active_delta = 0
        completed_delta = 0

        if isinstance(old_game, ActiveGame) and isinstance(game, CompletedGame):
            active_delta = -1
            completed_delta = 1

        new_metrics = replace(
            self.metrics,
            active_games=max(0, self.metrics.active_games + active_delta),
            completed_games=max(0, self.metrics.completed_games + completed_delta),
        )

        return replace(self, games=new_games, metrics=new_metrics)

    def add_connection(self, connection: ConnectionState) -> ResourcePool:
        """Add a connection immutably with validation."""
        connection_id = getattr(connection, "connection_id", str(id(connection)))

        can_add, reason = self.can_add_connection(connection_id)
        if not can_add:
            raise ResourceExhaustedError(reason)

        new_connections = {**self.connections, connection_id: connection}
        new_metrics = replace(
            self.metrics,
            total_connections=self.metrics.total_connections + 1,
            active_connections=self.metrics.active_connections
            + (1 if is_connected(connection) else 0),
        )

        return replace(self, connections=new_connections, metrics=new_metrics)

    def remove_connection(self, connection_id: str) -> ResourcePool:
        """Remove a connection immutably."""
        if connection_id not in self.connections:
            return self  # Already removed

        connection = self.connections[connection_id]
        new_connections = {
            k: v for k, v in self.connections.items() if k != connection_id
        }

        # Remove from all game subscriptions
        new_game_connections = {}
        for game_id, conn_set in self.game_connections.items():
            new_set = conn_set - {connection_id}
            if new_set:  # Only keep non-empty sets
                new_game_connections[game_id] = new_set

        new_metrics = replace(
            self.metrics,
            total_connections=max(0, self.metrics.total_connections - 1),
            active_connections=max(
                0,
                self.metrics.active_connections
                - (1 if is_connected(connection) else 0),
            ),
        )

        return replace(
            self,
            connections=new_connections,
            game_connections=new_game_connections,
            metrics=new_metrics,
        )

    def update_connection(self, connection: ConnectionState) -> ResourcePool:
        """Update a connection immutably."""
        connection_id = getattr(connection, "connection_id", str(id(connection)))

        if connection_id not in self.connections:
            raise ResourceNotFoundError(f"Connection {connection_id} not found")

        old_connection = self.connections[connection_id]
        new_connections = {**self.connections, connection_id: connection}

        # Update metrics if connection status changed
        active_delta = 0
        if is_connected(old_connection) != is_connected(connection):
            active_delta = 1 if is_connected(connection) else -1

        new_metrics = replace(
            self.metrics,
            active_connections=max(0, self.metrics.active_connections + active_delta),
        )

        return replace(self, connections=new_connections, metrics=new_metrics)

    def add_game_connection(self, game_id: str, connection_id: str) -> ResourcePool:
        """Add a connection to a game immutably."""
        can_join, reason = self.can_join_game(game_id, connection_id)
        if not can_join:
            raise ResourceExhaustedError(reason)

        current_connections = self.game_connections.get(game_id, frozenset())
        new_connections = current_connections | {connection_id}
        new_game_connections = {**self.game_connections, game_id: new_connections}

        return replace(self, game_connections=new_game_connections)

    def remove_game_connection(self, game_id: str, connection_id: str) -> ResourcePool:
        """Remove a connection from a game immutably."""
        current_connections = self.game_connections.get(game_id, frozenset())
        new_connections = current_connections - {connection_id}

        if new_connections:
            new_game_connections = {**self.game_connections, game_id: new_connections}
        else:
            # Remove empty set
            new_game_connections = {
                k: v for k, v in self.game_connections.items() if k != game_id
            }

        return replace(self, game_connections=new_game_connections)

    def _calculate_metrics(
        self,
        games: Dict[str, GameState],
        connections: Dict[str, ConnectionState],
        cleanup_time: datetime,
    ) -> ResourceMetrics:
        """Calculate metrics from resources using pure functions."""
        return ResourceMetrics(
            total_games=len(games),
            active_games=sum(1 for g in games.values() if isinstance(g, ActiveGame)),
            completed_games=sum(
                1 for g in games.values() if isinstance(g, CompletedGame)
            ),
            total_connections=len(connections),
            active_connections=sum(1 for c in connections.values() if is_connected(c)),
            games_per_client=self.metrics.games_per_client,  # Preserve existing
            memory_usage_bytes=self.metrics.memory_usage_bytes,  # Preserve existing
            last_cleanup=cleanup_time,
        )

    def cleanup_stale_resources(
        self, game_timeout_seconds: int = 3600, connection_timeout_seconds: int = 60
    ) -> ResourcePool:
        """
        Remove stale games and connections using pure functional approach.
        Returns a new pool with cleaned resources.
        """
        now = datetime.now(timezone.utc)
        game_cutoff = now - timedelta(seconds=game_timeout_seconds)

        # Pure predicate functions
        def is_game_stale(game_id: str, game: GameState) -> bool:
            """Check if a game is stale based on last activity."""
            return not (
                hasattr(game, "last_activity") and game.last_activity > game_cutoff
            )

        def is_connection_stale(conn_id: str, conn: ConnectionState) -> bool:
            """Check if a connection should be removed."""
            # Only keep ClientConnected that are not stale
            if isinstance(conn, ClientConnected):
                return conn.is_stale(connection_timeout_seconds)
            # Remove all other connection states during cleanup
            return True

        # Partition resources using pure functions
        games_result = partition_by_staleness(self.games, is_game_stale)
        connections_result = partition_by_staleness(
            self.connections, is_connection_stale
        )

        # Filter game connections (pure functional)
        active_game_connections = {
            game_id: conns
            for game_id, conns in self.game_connections.items()
            if game_id in games_result.kept
        }

        # Calculate new metrics (pure function)
        new_metrics = self._calculate_metrics(
            games_result.kept,  # Dict[str, GameState]
            connections_result.kept,  # Dict[str, ConnectionState]
            now,
        )

        # Log side effects separately (after pure computation)
        for game_id in games_result.removed_ids:
            logger.info(f"Removing stale game {game_id}")
        for conn_id in connections_result.removed_ids:
            logger.info(f"Removing stale connection {conn_id}")

        logger.info(
            f"Cleanup completed: removed {games_result.removed_count} games "
            f"and {connections_result.removed_count} connections"
        )

        # Return new immutable pool with properly typed connections
        return replace(
            self,
            games=games_result.kept,  # Dict[str, GameState]
            connections=connections_result.kept,  # Dict[str, ConnectionState]
            game_connections=active_game_connections,
            metrics=new_metrics,
        )

    def get_health_status(self) -> Dict[str, object]:
        """Get health status of the resource pool."""
        return {
            "healthy": True,
            "games": {
                "total": len(self.games),
                "active": self.metrics.active_games,
                "completed": self.metrics.completed_games,
                "limit": self.max_total_games,
                "usage_percent": (len(self.games) / self.max_total_games * 100)
                if self.max_total_games > 0
                else 0,
            },
            "connections": {
                "total": len(self.connections),
                "active": self.metrics.active_connections,
                "limit": self.max_total_connections,
                "usage_percent": (
                    len(self.connections) / self.max_total_connections * 100
                )
                if self.max_total_connections > 0
                else 0,
            },
            "last_cleanup": self.metrics.last_cleanup.isoformat(),
            "memory_usage_mb": self.metrics.memory_usage_bytes / (1024 * 1024),
        }
