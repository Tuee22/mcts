"""
Immutable game pool for functional game state management.

This module provides a purely functional approach to game management where
all operations return new pool instances, making illegal states unrepresentable.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, FrozenSet, List, Optional, Tuple

from backend.api.game_states import GameState, ActiveGame, CompletedGame, WaitingGame


class GameNotFoundError(Exception):
    """Raised when attempting to operate on a non-existent game."""

    pass


class GameAlreadyExistsError(Exception):
    """Raised when attempting to add a game with duplicate ID."""

    pass


@dataclass(frozen=True)
class GamePool:
    """
    Immutable pool of games using pure functional operations.

    All methods return new GamePool instances, ensuring thread safety
    and making state transitions explicit and traceable.
    """

    games: Dict[str, GameState] = field(default_factory=dict)
    # Track which clients are in which games for quick lookup
    client_games: Dict[str, FrozenSet[str]] = field(default_factory=dict)

    def add_game(self, game: GameState) -> GamePool:
        """
        Add a new game to the pool immutably.

        Raises:
            GameAlreadyExistsError: If game_id already exists
        """
        if game.game_id in self.games:
            raise GameAlreadyExistsError(f"Game {game.game_id} already exists")

        new_games = {**self.games, game.game_id: game}

        # Update client tracking for active games
        new_client_games = self.client_games.copy()
        if isinstance(game, (ActiveGame, CompletedGame)):
            # Add game to both players' game sets
            p1_games = self.client_games.get(game.player1.id, frozenset())
            p2_games = self.client_games.get(game.player2.id, frozenset())
            new_client_games[game.player1.id] = p1_games | {game.game_id}
            new_client_games[game.player2.id] = p2_games | {game.game_id}

        return replace(self, games=new_games, client_games=new_client_games)

    def update_game(self, game: GameState) -> GamePool:
        """
        Update an existing game immutably.

        Raises:
            GameNotFoundError: If game doesn't exist
        """
        if game.game_id not in self.games:
            raise GameNotFoundError(f"Game {game.game_id} not found")

        old_game = self.games[game.game_id]
        new_games = {**self.games, game.game_id: game}

        # Update client tracking if game transitioned to active
        new_client_games = self.client_games
        if isinstance(game, ActiveGame) and isinstance(old_game, WaitingGame):
            # Game just started, update client tracking
            new_client_games = self.client_games.copy()
            p1_games = self.client_games.get(game.player1.id, frozenset())
            p2_games = self.client_games.get(game.player2.id, frozenset())
            new_client_games[game.player1.id] = p1_games | {game.game_id}
            new_client_games[game.player2.id] = p2_games | {game.game_id}

        return replace(self, games=new_games, client_games=new_client_games)

    def remove_game(self, game_id: str) -> GamePool:
        """
        Remove a game from the pool immutably.

        Returns unchanged pool if game doesn't exist.
        """
        if game_id not in self.games:
            return self  # Already removed, return unchanged

        game = self.games[game_id]
        new_games = {k: v for k, v in self.games.items() if k != game_id}

        # Update client tracking
        new_client_games = self.client_games.copy()
        if isinstance(game, (ActiveGame, CompletedGame)):
            # Remove game from both players' sets
            p1_games = self.client_games.get(game.player1.id, frozenset())
            p2_games = self.client_games.get(game.player2.id, frozenset())

            new_p1_games = p1_games - {game_id}
            new_p2_games = p2_games - {game_id}

            if new_p1_games:
                new_client_games[game.player1.id] = new_p1_games
            elif game.player1.id in new_client_games:
                del new_client_games[game.player1.id]

            if new_p2_games:
                new_client_games[game.player2.id] = new_p2_games
            elif game.player2.id in new_client_games:
                del new_client_games[game.player2.id]

        return replace(self, games=new_games, client_games=new_client_games)

    def get_game(self, game_id: str) -> Optional[GameState]:
        """Get a game by ID, returns None if not found."""
        return self.games.get(game_id)

    def get_client_games(self, client_id: str) -> List[GameState]:
        """Get all games for a specific client."""
        game_ids = self.client_games.get(client_id, frozenset())
        return [self.games[gid] for gid in game_ids if gid in self.games]

    def get_active_games(self) -> List[ActiveGame]:
        """Get all active games."""
        return [g for g in self.games.values() if isinstance(g, ActiveGame)]

    def get_waiting_games(self) -> List[WaitingGame]:
        """Get all waiting games."""
        return [g for g in self.games.values() if isinstance(g, WaitingGame)]

    def count_client_active_games(self, client_id: str) -> int:
        """Count active games for a client."""
        return sum(
            1
            for game in self.get_client_games(client_id)
            if isinstance(game, ActiveGame)
        )

    def can_client_create_game(
        self, client_id: str, max_games: int = 5
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a client can create a new game.

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        active_count = self.count_client_active_games(client_id)
        if active_count >= max_games:
            return False, f"Client has {active_count} active games (max: {max_games})"
        return True, None

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the game pool."""
        return {
            "total": len(self.games),
            "waiting": sum(
                1 for g in self.games.values() if isinstance(g, WaitingGame)
            ),
            "active": sum(1 for g in self.games.values() if isinstance(g, ActiveGame)),
            "completed": sum(
                1 for g in self.games.values() if isinstance(g, CompletedGame)
            ),
            "unique_clients": len(self.client_games),
        }
