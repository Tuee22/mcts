"""
Functional Game Manager using immutable state transitions.

This replaces the mutable GameManager with pure functional operations.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from corridors.async_mcts import MCTSRegistry, ConcurrencyViolationError, MCTSConfig

from backend.api.game_states import (
    ActiveGame,
    CompletedGame,
    GameState,
    MoveTransitionResult,
    NonMoveTransitionResult,
    WaitingGame,
)
from backend.api.game_transitions import process_move_transition, resign_game_transition
from backend.api.models import (
    BoardState,
    GameMode,
    GameSettings,
    GameStatus,
    MCTSSettings,
    MoveResponse,
    Player,
    PlayerType,
    Position,
)
from backend.api.response_builders import build_move_response
from backend.api.pure_utils import find_first_match, safe_get, count_where

logger = logging.getLogger(__name__)


class GameManager:
    """
    Game manager using immutable state transitions.

    All operations return new states instead of mutating existing ones.
    """

    def __init__(self) -> None:
        # Only mutable state is the game storage and AI queue
        self._games: Dict[str, GameState] = {}
        self.ai_move_queue: asyncio.Queue[str] = asyncio.Queue()
        self.mcts_registry = MCTSRegistry()

    async def create_game(
        self,
        player1_type: PlayerType,
        player2_type: PlayerType,
        player1_name: str = "Player 1",
        player2_name: str = "Player 2",
        player1_id: Optional[str] = None,
        player2_id: Optional[str] = None,
        settings: Optional[GameSettings] = None,
    ) -> GameState:
        """Create a new game session using functional approach."""
        # Determine game mode functionally
        mode = _determine_game_mode(player1_type, player2_type)

        # Create players immutably
        player1, player2 = _create_players(
            player1_type,
            player2_type,
            player1_name,
            player2_name,
            player1_id,
            player2_id,
        )

        # Create initial game state
        game = ActiveGame(
            game_id=str(uuid.uuid4()),
            mode=mode,
            player1=player1,
            player2=player2,
            current_turn=1,
            move_history=[],
            board_state=_create_initial_board_state(),
            settings=settings or GameSettings(),
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
        )

        # Initialize MCTS instance
        await self._initialize_mcts_for_game(game)

        # Store the game (only mutable operation)
        self._games[game.game_id] = game

        return game

    async def make_move(
        self, game_id: str, player_id: str, action: str
    ) -> MoveResponse:
        """Make a move using functional state transitions."""
        # Get current game state
        current_state = safe_get(self._games, game_id)
        if current_state is None:
            raise ValueError("Game not found")

        # Only allow moves in active games
        if not isinstance(current_state, ActiveGame):
            raise ValueError("Cannot make moves in non-active games")

        # Validate move using pure functions
        _validate_move_request(current_state, player_id, action)

        # Get game analysis data
        eval_result, next_legal_moves, board_state = await self._analyze_game_position(
            current_state, action
        )

        # Process move transition (pure function)
        transition_result: MoveTransitionResult = process_move_transition(
            current_state,
            player_id,
            action,
            eval_result,
            next_legal_moves,
            board_state,
        )

        # Update stored state (only mutable operation)
        self._games[game_id] = transition_result.new_state

        # Queue AI move if needed
        if transition_result.ai_should_move:
            await self.ai_move_queue.put(game_id)

        # Build response using pattern matching
        return build_move_response(
            transition_result.new_state,
            transition_result.move,  # Now guaranteed to exist by MoveTransitionResult type
        )

    async def resign_game(self, game_id: str, player_id: str) -> int:
        """Process game resignation using functional transitions."""
        current_state = safe_get(self._games, game_id)
        if current_state is None:
            raise ValueError("Game not found")

        if not isinstance(current_state, ActiveGame):
            raise ValueError("Cannot resign from non-active games")

        # Process resignation (pure function)
        transition_result: NonMoveTransitionResult = resign_game_transition(
            current_state, player_id
        )

        # Update stored state (only mutable operation)
        self._games[game_id] = transition_result.new_state

        # Return winner number for backwards compatibility
        if isinstance(transition_result.new_state, CompletedGame):
            return transition_result.new_state.winner
        else:
            raise ValueError("Resignation should result in completed game")

    async def get_game(self, game_id: str) -> Optional[GameState]:
        """Get game state (pure function)."""
        return safe_get(self._games, game_id)

    async def list_games(
        self,
        status: Optional[GameStatus] = None,
        player_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[GameState]:
        """List games with optional filtering (functional approach)."""
        games = list(self._games.values())

        # Use functional filtering instead of imperative loops
        games = (
            list(filter(lambda g: _game_matches_status(g, status), games))
            if status
            else games
        )

        games = (
            list(filter(lambda g: _game_has_player(g, player_id), games))
            if player_id
            else games
        )

        # Sort by creation time (newest first)
        games.sort(key=_get_game_created_at, reverse=True)

        # Apply pagination
        return games[offset : offset + limit]

    # Private helper methods

    async def _initialize_mcts_for_game(self, game: ActiveGame) -> None:
        """Initialize MCTS instance for the game."""
        mcts_settings = game.settings.mcts_settings
        config = MCTSConfig(
            c=mcts_settings.c,
            min_simulations=mcts_settings.min_simulations,
            max_simulations=mcts_settings.max_simulations,
            use_rollout=mcts_settings.use_rollout,
            eval_children=mcts_settings.eval_children,
            use_puct=mcts_settings.use_puct,
            use_probs=mcts_settings.use_probs,
            decide_using_visits=mcts_settings.decide_using_visits,
            seed=mcts_settings.seed or 42,  # Default seed if None
        )
        await self.mcts_registry.get_or_create(game.game_id, config)

    async def _analyze_game_position(
        self, game: ActiveGame, action: str
    ) -> tuple[Optional[float], List[str], BoardState]:
        """Analyze game position after a move."""
        # Get MCTS instance
        mcts = await self.mcts_registry.get(game.game_id)

        if mcts is not None:
            # Apply move to MCTS
            current_player = game.get_current_player()
            flip = not current_player.is_hero
            await mcts.make_move_async(action, flip)

            # Get evaluation
            eval_result = await mcts.get_evaluation_async()

            # Get next legal moves
            next_legal_moves_data = await mcts.get_sorted_actions_async(flip)
            next_legal_moves = [action[2] for action in next_legal_moves_data]

            # Get board display
            display = await mcts.display_async(False)
        else:
            eval_result = None
            next_legal_moves = []
            display = ""

        # Create board state (simplified)
        board_state = BoardState(
            hero_position=Position(x=4, y=0),
            villain_position=Position(x=4, y=8),
            walls=[],
            display=display,
        )

        return eval_result, next_legal_moves, board_state

    async def cleanup(self) -> None:
        """Clean up all resources (pure function with side effects)."""
        # Cleanup all MCTS instances
        await self.mcts_registry.cleanup_all()

        # Clear game data (only mutable operation)
        self._games.clear()

        # Clear the AI move queue
        while not self.ai_move_queue.empty():
            try:
                self.ai_move_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def process_ai_moves(self) -> None:
        """Background task to process AI moves using functional patterns."""
        while True:
            try:
                # Use timeout to avoid blocking indefinitely
                game_id = await asyncio.wait_for(self.ai_move_queue.get(), timeout=1.0)

                current_state = safe_get(self._games, game_id)
                if current_state is None or not isinstance(current_state, ActiveGame):
                    continue

                current_player = current_state.get_current_player()
                if current_player.type != PlayerType.MACHINE:
                    continue

                # Run MCTS simulations with timeout
                mcts = await self.mcts_registry.get(game_id)
                if mcts is not None:
                    # Add small delay to ensure other operations complete
                    await asyncio.sleep(0.1)

                    try:
                        # Use async simulations with timeout
                        await asyncio.wait_for(
                            mcts.ensure_sims_async(
                                current_state.settings.mcts_settings.min_simulations
                            ),
                            timeout=5.0,  # 5 second timeout
                        )

                        # Choose best move
                        best_action = await mcts.choose_best_action_async(epsilon=0)
                    except asyncio.TimeoutError:
                        logger.warning(f"AI move timeout for game {game_id}")
                        # Cancel any running simulations
                        mcts.cancel_simulations()
                        continue
                else:
                    continue

                # Make the move using functional approach
                await self.make_move(game_id, current_player.id, best_action)

                logger.info(f"AI made move in game {game_id}: {best_action}")

            except asyncio.TimeoutError:
                # No AI moves to process, continue
                continue
            except Exception as e:
                logger.error(f"Error processing AI move: {e}")
                # Add small delay to prevent tight error loops
                await asyncio.sleep(0.5)

    async def delete_game(self, game_id: str) -> bool:
        """Delete a game session (pure function with side effects)."""
        if game_id in self._games:
            del self._games[game_id]
            logger.info(f"Deleted game {game_id}")
            return True
        return False

    async def get_legal_moves(self, game_id: str) -> List[str]:
        """Get legal moves for current position (placeholder)."""
        # This would need MCTS integration - simplified for now
        return []

    async def get_board_display(self, game_id: str, flip: bool = False) -> str:
        """Get ASCII board display (placeholder)."""
        # This would need MCTS integration - simplified for now
        return ""

    async def analyze_position(
        self, game_id: str, depth: int = 10000
    ) -> Dict[
        str, Union[str, float, List[Dict[str, Union[str, int, float]]], int, None]
    ]:
        """Analyze current position with MCTS (placeholder)."""
        # This would need MCTS integration - simplified for now
        return {}

    async def get_hint(
        self, game_id: str, simulations: int = 5000
    ) -> Dict[str, Union[str, float]]:
        """Get move hint using MCTS (placeholder)."""
        # This would need MCTS integration - simplified for now
        return {"action": "", "confidence": 0, "evaluation": 0}

    async def trigger_ai_move(self, game_id: str) -> None:
        """Trigger AI to make a move."""
        await self.ai_move_queue.put(game_id)

    async def join_matchmaking(
        self, player_id: str, player_name: str, settings: Optional[GameSettings] = None
    ) -> Optional[GameState]:
        """Join matchmaking queue (placeholder)."""
        # This would need matchmaking logic - simplified for now
        return None

    async def get_queue_position(self, player_id: str) -> int:
        """Get position in matchmaking queue (placeholder)."""
        return -1

    async def leave_matchmaking(self, player_id: str) -> bool:
        """Leave matchmaking queue (placeholder)."""
        return True

    async def get_leaderboard(
        self, limit: int = 100
    ) -> List[Dict[str, Union[str, int, float]]]:
        """Get game leaderboard (placeholder)."""
        return []

    async def get_player_stats(
        self, player_id: str
    ) -> Optional[Dict[str, Union[str, int, float]]]:
        """Get player statistics (placeholder)."""
        return None

    async def get_active_game_count(self) -> int:
        """Get count of active games."""
        return count_where(
            list(self._games.values()), lambda g: isinstance(g, ActiveGame)
        )


# Pure helper functions


def _game_matches_status(game: GameState, status: GameStatus) -> bool:
    """Check if game matches status (pure function)."""
    match game:
        case ActiveGame():
            return status == GameStatus.IN_PROGRESS
        case CompletedGame():
            return status == GameStatus.COMPLETED
        case WaitingGame():
            return status == GameStatus.WAITING


def _game_has_player(game: GameState, player_id: str) -> bool:
    """Check if game has player (pure function)."""
    match game:
        case ActiveGame() | CompletedGame():
            return game.player1.id == player_id or game.player2.id == player_id
        case WaitingGame():
            return False


def _get_game_created_at(game: GameState) -> datetime:
    """Get game creation time (pure function)."""
    return game.created_at


def _determine_game_mode(
    player1_type: PlayerType, player2_type: PlayerType
) -> GameMode:
    """Determine game mode from player types (pure function)."""
    return (
        GameMode.PVP
        if player1_type == player2_type == PlayerType.HUMAN
        else GameMode.MVM
        if player1_type == player2_type == PlayerType.MACHINE
        else GameMode.PVM
    )


def _create_players(
    player1_type: PlayerType,
    player2_type: PlayerType,
    player1_name: str,
    player2_name: str,
    player1_id: Optional[str],
    player2_id: Optional[str],
) -> tuple[Player, Player]:
    """Create player objects (pure function)."""
    player1 = Player(
        id=player1_id or str(uuid.uuid4()),
        name=player1_name,
        type=player1_type,
        is_hero=True,
    )

    player2 = Player(
        id=player2_id or str(uuid.uuid4()),
        name=player2_name,
        type=player2_type,
        is_hero=False,
    )

    return player1, player2


def _create_initial_board_state() -> BoardState:
    """Create initial board state (pure function)."""
    return BoardState(
        hero_position=Position(x=4, y=0),
        villain_position=Position(x=4, y=8),
        walls=[],
        display="Initial board state",
    )


def _validate_move_request(game: ActiveGame, player_id: str, action: str) -> None:
    """Validate move request (pure function that raises on invalid)."""
    # Validate player exists and is current player
    current_player = game.get_current_player()
    if current_player.id != player_id:
        raise ValueError("Not your turn")

    # Additional validation would go here
    # For now, we'll assume action validation happens in MCTS
