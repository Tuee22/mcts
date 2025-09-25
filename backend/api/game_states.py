"""
Immutable game state types using discriminated unions.

This module defines type-safe game states that make illegal states unrepresentable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Literal, Union

from backend.api.models import BoardState, GameMode, GameSettings, Move, Player


@dataclass(frozen=True)
class WaitingGame:
    """Game waiting for players to join - cannot have moves or winner."""

    game_id: str
    mode: GameMode
    settings: GameSettings
    created_at: datetime


@dataclass(frozen=True)
class ActiveGame:
    """Game in progress with valid current player - must have both players."""

    game_id: str
    mode: GameMode
    player1: Player
    player2: Player
    current_turn: Literal[1, 2]
    move_history: List[Move]
    board_state: BoardState
    settings: GameSettings
    created_at: datetime
    started_at: datetime

    def get_current_player(self) -> Player:
        """Get the current player based on turn."""
        return self.player1 if self.current_turn == 1 else self.player2

    def get_next_turn(self) -> Literal[1, 2]:
        """Get the next turn number."""
        return 2 if self.current_turn == 1 else 1

    def get_player_by_id(self, player_id: str) -> Player:
        """Get player by ID, raises ValueError if not found."""
        if self.player1.id == player_id:
            return self.player1
        elif self.player2.id == player_id:
            return self.player2
        else:
            raise ValueError(f"Player {player_id} not found in game")


@dataclass(frozen=True)
class CompletedGame:
    """Completed game with winner and final state - cannot change anymore."""

    game_id: str
    mode: GameMode
    player1: Player
    player2: Player
    move_history: List[Move]
    board_state: BoardState
    winner: Literal[1, 2]
    termination_reason: Literal["checkmate", "evaluation", "resignation", "timeout"]
    settings: GameSettings
    created_at: datetime
    started_at: datetime
    ended_at: datetime

    def get_winner_player(self) -> Player:
        """Get the winning player object."""
        return self.player1 if self.winner == 1 else self.player2


# Discriminated union representing all possible game states
GameState = Union[WaitingGame, ActiveGame, CompletedGame]


@dataclass(frozen=True)
class GameTransitionResult:
    """Base result of a game state transition."""

    new_state: GameState
    ai_should_move: bool = False  # Whether to queue an AI move


@dataclass(frozen=True)
class MoveTransitionResult:
    """Result of a move transition - always has a move."""

    new_state: GameState
    move: Move  # Move is always present for move transitions
    ai_should_move: bool = False  # Whether to queue an AI move


@dataclass(frozen=True)
class NonMoveTransitionResult(GameTransitionResult):
    """Result of non-move transitions (resignation, timeout, etc)."""

    pass  # No additional fields needed
