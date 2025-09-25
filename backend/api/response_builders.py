"""
Pattern matching response builders for API responses.

Uses pattern matching to create type-safe API responses from game states.
"""

from __future__ import annotations

from backend.api.game_states import ActiveGame, CompletedGame, GameState, WaitingGame
from backend.api.models import GameResponse, GameStatus, Move, MoveResponse, PlayerType


def build_game_response(state: GameState) -> GameResponse:
    """Build GameResponse using pattern matching on game state."""
    match state:
        case WaitingGame(game_id=gid, created_at=created):
            # For waiting games, we need placeholder players
            # This shouldn't normally happen in the API, but type safety requires it
            raise ValueError(
                "Cannot create GameResponse for WaitingGame without players"
            )

        case ActiveGame(
            game_id=gid,
            mode=mode,
            player1=p1,
            player2=p2,
            current_turn=turn,
            move_history=history,
            board_state=board,
            created_at=created,
            started_at=started,
        ):
            return GameResponse(
                game_id=gid,
                status=GameStatus.IN_PROGRESS,
                mode=mode,
                player1=p1,
                player2=p2,
                current_turn=turn,
                move_count=len(history),
                board_display=board.display if board else None,
                winner=None,
                created_at=created,
                started_at=started,
            )

        case CompletedGame(
            game_id=gid,
            mode=mode,
            player1=p1,
            player2=p2,
            move_history=history,
            board_state=board,
            winner=winner,
            created_at=created,
            started_at=started,
        ):
            return GameResponse(
                game_id=gid,
                status=GameStatus.COMPLETED,
                mode=mode,
                player1=p1,
                player2=p2,
                current_turn=0,  # No current turn in completed games
                move_count=len(history),
                board_display=board.display if board else None,
                winner=winner,
                created_at=created,
                started_at=started,
            )

        case _:
            # This should never happen with our discriminated union
            raise ValueError(f"Unknown game state type: {type(state)}")


def build_move_response(
    state: GameState, move: Move, success: bool = True
) -> MoveResponse:
    """Build MoveResponse using pattern matching on resulting game state."""
    match state:
        case ActiveGame(
            game_id=gid,
            current_turn=turn,
            board_state=board,
        ):
            # In active games, there is a next player
            next_player = state.get_current_player()
            return MoveResponse(
                success=success,
                game_id=gid,
                move=move,
                game_status=GameStatus.IN_PROGRESS,
                next_turn=turn,
                next_player_type=next_player.type,
                board_display=board.display if board else None,
                winner=None,
            )

        case CompletedGame(
            game_id=gid,
            board_state=board,
            winner=winner,
        ):
            # In completed games, there is no next player
            return MoveResponse(
                success=success,
                game_id=gid,
                move=move,
                game_status=GameStatus.COMPLETED,
                next_turn=0,  # No next turn
                next_player_type=None,  # No next player
                board_display=board.display if board else None,
                winner=winner,
            )

        case WaitingGame():
            # Moves cannot be made in waiting games
            raise ValueError("Cannot make moves in waiting games")

        case _:
            # This should never happen with our discriminated union
            raise ValueError(f"Unknown game state type: {type(state)}")


def get_next_player_type_from_state(state: GameState) -> PlayerType | None:
    """Get next player type using pattern matching, returning None if game ended."""
    match state:
        case ActiveGame():
            return state.get_current_player().type
        case CompletedGame():
            return None
        case WaitingGame():
            return None
        case _:
            raise ValueError(f"Unknown game state type: {type(state)}")
