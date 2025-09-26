"""
Pure functional game transition logic.

All functions in this module are pure - they don't mutate input and
return new state objects instead.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import List, Literal, Optional

from backend.api.game_states import (
    ActiveGame,
    CompletedGame,
    GameState,
    MoveTransitionResult,
    NonMoveTransitionResult,
    WaitingGame,
)
from backend.api.models import BoardState, Move, PlayerType


def start_game(
    waiting: WaitingGame, player1: Move, player2: Move
) -> NonMoveTransitionResult:
    """Transition from WaitingGame to ActiveGame when both players join."""
    # This is a placeholder - actual implementation would come from game creation
    raise NotImplementedError("Game starting logic to be implemented")


def process_move_transition(
    game: ActiveGame,
    player_id: str,
    action: str,
    eval_result: Optional[float],
    next_legal_moves: List[str],
    board_state: BoardState,
) -> MoveTransitionResult:
    """Process a move and return new game state (pure function)."""
    # Validate player turn
    current_player = game.get_current_player()
    if current_player.id != player_id:
        raise ValueError("Not your turn")

    # Create new move record
    move = Move(
        player_id=player_id,
        action=action,
        move_number=len(game.move_history) + 1,
        evaluation=eval_result,
        timestamp=datetime.now(timezone.utc),
    )

    # Determine if game should end
    game_ends = not next_legal_moves or eval_result is not None

    return (
        _create_completed_game_transition(
            game, move, eval_result, next_legal_moves, board_state
        )
        if game_ends
        else _create_continued_game_transition(game, move, board_state)
    )


def resign_game_transition(
    game: ActiveGame, resigning_player_id: str
) -> NonMoveTransitionResult:
    """Process a resignation and return completed game state."""
    resigning_player = game.get_player_by_id(resigning_player_id)
    winner: Literal[1, 2] = 2 if resigning_player == game.player1 else 1

    # Create completed game with activity timestamp using functional pattern
    completed = CompletedGame(
        game_id=game.game_id,
        mode=game.mode,
        player1=game.player1,
        player2=game.player2,
        move_history=game.move_history,
        board_state=game.board_state,
        winner=winner,
        termination_reason="resignation",
        settings=game.settings,
        created_at=game.created_at,
        started_at=game.started_at,
        ended_at=datetime.now(timezone.utc),
        last_activity=datetime.now(timezone.utc),
    )

    return NonMoveTransitionResult(new_state=completed, ai_should_move=False)


# Private helper functions


def _create_completed_game_transition(
    game: ActiveGame,
    move: Move,
    eval_result: Optional[float],
    next_legal_moves: List[str],
    board_state: BoardState,
) -> MoveTransitionResult:
    """Create a completed game state transition."""
    winner = _determine_winner(game.current_turn, eval_result)
    termination_reason: Literal["checkmate", "evaluation"] = (
        "checkmate" if not next_legal_moves else "evaluation"
    )

    # Create completed game with updated activity timestamp
    completed = CompletedGame(
        game_id=game.game_id,
        mode=game.mode,
        player1=game.player1,
        player2=game.player2,
        move_history=[*game.move_history, move],
        board_state=board_state,
        winner=winner,
        termination_reason=termination_reason,
        settings=game.settings,
        created_at=game.created_at,
        started_at=game.started_at,
        ended_at=datetime.now(timezone.utc),
        last_activity=datetime.now(timezone.utc),
    )

    return MoveTransitionResult(
        new_state=completed,
        move=move,
        ai_should_move=False,  # No AI moves in completed games
    )


def _create_continued_game_transition(
    game: ActiveGame, move: Move, board_state: BoardState
) -> MoveTransitionResult:
    """Create next active game state transition with updated activity."""
    next_turn = game.get_next_turn()
    next_player = game.player1 if next_turn == 1 else game.player2

    # Update all game state including last_activity using functional patterns
    continued = replace(
        game,
        current_turn=next_turn,
        move_history=[*game.move_history, move],
        board_state=board_state,
        last_activity=datetime.now(timezone.utc),
    )

    return MoveTransitionResult(
        new_state=continued,
        move=move,
        ai_should_move=next_player.type == PlayerType.MACHINE,
    )


def _determine_winner(
    current_turn: Literal[1, 2], eval_result: Optional[float]
) -> Literal[1, 2]:
    """Determine winner based on evaluation or current turn."""
    return (1 if eval_result > 0 else 2) if eval_result is not None else current_turn
