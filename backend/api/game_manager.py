import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corridors.async_mcts import MCTSRegistry, ConcurrencyViolationError

from .models import (
    AnalysisResult,
    BoardState,
    GameMode,
    GameSession,
    GameSettings,
    GameStatus,
    MCTSSettings,
    Move,
    MoveResponse,
    Player,
    PlayerType,
    Position,
)

# Rebuild the model now that Corridors_MCTS is available
GameSession.model_rebuild()

logger = logging.getLogger(__name__)


class GameManager:
    """
    Manages all game sessions and MCTS instances with race condition protection.
    
    Uses per-game locks to ensure atomic operations and prevent C++ instance
    corruption from concurrent API requests.
    """

    def __init__(self) -> None:
        self.games: Dict[str, GameSession] = {}
        self.matchmaking_queue: List[
            Dict[str, Union[str, Optional[GameSettings], datetime]]
        ] = []
        self.ai_move_queue: asyncio.Queue[str] = asyncio.Queue()
        
        # Global lock for games dict operations  
        self._global_lock = asyncio.Lock()
        
        # Per-game locks for API-level serialization
        self._game_locks: Dict[str, asyncio.Lock] = {}

        # Async MCTS registry for better concurrency management
        self.mcts_registry = MCTSRegistry()

    async def _get_game_lock(self, game_id: str) -> asyncio.Lock:
        """Get or create per-game lock for serialization."""
        async with self._global_lock:
            if game_id not in self._game_locks:
                self._game_locks[game_id] = asyncio.Lock()
            return self._game_locks[game_id]

    async def create_game(
        self,
        player1_type: PlayerType,
        player2_type: PlayerType,
        player1_name: str = "Player 1",
        player2_name: str = "Player 2",
        player1_id: Optional[str] = None,
        player2_id: Optional[str] = None,
        settings: Optional[GameSettings] = None,
    ) -> GameSession:
        """Create a new game session."""
        async with self._lock:
            # Determine game mode
            if player1_type == PlayerType.HUMAN and player2_type == PlayerType.HUMAN:
                mode = GameMode.PVP
            elif (
                player1_type == PlayerType.MACHINE
                and player2_type == PlayerType.MACHINE
            ):
                mode = GameMode.MVM
            else:
                mode = GameMode.PVM

            # Create players
            import uuid

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

            # Create game session
            game = GameSession(
                mode=mode,
                player1=player1,
                player2=player2,
                settings=settings or GameSettings(),
            )

            # Initialize async MCTS instance
            mcts_settings = game.settings.mcts_settings

            # Create async MCTS instance for race-condition-free concurrency
            await self.mcts_registry.get_or_create(
                game_id=game.game_id,
                c=mcts_settings.c,
                seed=mcts_settings.seed or 42,
                min_simulations=mcts_settings.min_simulations,
                max_simulations=mcts_settings.max_simulations,
                sim_increment=50,  # Default increment
                use_rollout=mcts_settings.use_rollout,
                eval_children=mcts_settings.eval_children,
                use_puct=mcts_settings.use_puct,
                use_probs=mcts_settings.use_probs,
                decide_using_visits=mcts_settings.decide_using_visits,
            )

            # Use only async registry for thread safety - no sync instances

            # Set initial board state
            game.board_state = await self._get_board_state(game)

            # Start the game
            game.status = GameStatus.IN_PROGRESS
            game.started_at = datetime.now(timezone.utc)

            # Store the game
            self.games[game.game_id] = game

            logger.info(f"Created game {game.game_id} ({mode})")

        # Queue AI move outside the lock to avoid deadlock
        if player1_type == PlayerType.MACHINE:
            await self.ai_move_queue.put(game.game_id)

        return game

    async def get_game(self, game_id: str) -> Optional[GameSession]:
        """Get a game session by ID."""
        return self.games.get(game_id)

    async def list_games(
        self,
        status: Optional[GameStatus] = None,
        player_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[GameSession]:
        """List games with optional filtering."""
        games = list(self.games.values())

        # Filter by status
        if status:
            games = [g for g in games if g.status == status]

        # Filter by player
        if player_id:
            games = [g for g in games if g.is_player(player_id)]

        # Sort by creation time (newest first)
        def get_created_at(game: GameSession) -> datetime:
            return game.created_at

        games.sort(key=get_created_at, reverse=True)

        # Apply pagination
        return games[offset : offset + limit]

    async def delete_game(self, game_id: str) -> bool:
        """Delete a game session."""
        async with self._lock:
            if game_id in self.games:
                game = self.games[game_id]
                game.status = GameStatus.CANCELLED
                game.ended_at = datetime.now(timezone.utc)
                del self.games[game_id]
                logger.info(f"Deleted game {game_id}")
                return True
            return False

    async def make_move(
        self, game_id: str, player_id: str, action: str
    ) -> MoveResponse:
        """Make a move in the game with race condition protection."""
        # Get per-game lock for atomic operations
        game_lock = await self._get_game_lock(game_id)
        
        async with game_lock:
            game = self.games.get(game_id)
            if not game:
                raise ValueError("Game not found")

            # Validate player
            player = game.get_player(player_id)
            if not player:
                raise ValueError("Player not in this game")

            # Check if it's player's turn
            current_player = game.get_current_player()
            if current_player.id != player_id:
                raise ValueError("Not your turn")

            # Get legal moves to validate
            legal_moves = await self._get_legal_moves_internal(game)
            if action not in legal_moves:
                raise ValueError(f"Illegal move: {action}")

            # Apply the move to MCTS instance
            flip = not current_player.is_hero
            mcts = await self.mcts_registry.get(game_id)
            if mcts is not None:
                # Let ConcurrencyViolationError bubble up for loud failure
                await mcts.make_move_async(action, flip)

            # Create move record
            move = Move(
                player_id=player_id,
                action=action,
                move_number=len(game.move_history) + 1,
            )

            # Get evaluation if available
            eval_result = None
            mcts = await self.mcts_registry.get(game_id)
            if mcts is not None:
                eval_result = await mcts.get_evaluation_async()
            if eval_result is not None:
                move.evaluation = eval_result

            game.move_history.append(move)

            # Update board state
            game.board_state = await self._get_board_state(game)

            # Check for game end
            next_legal_moves = await self._get_legal_moves_internal(
                game, for_next_player=True
            )
            if not next_legal_moves or eval_result is not None:
                game.status = GameStatus.COMPLETED
                game.ended_at = datetime.now(timezone.utc)

                # Determine winner
                if eval_result is not None:
                    # Positive eval means hero wins
                    game.winner = 1 if eval_result > 0 else 2
                else:
                    # No moves means current player wins
                    game.winner = 1 if current_player.is_hero else 2

                game.termination_reason = (
                    "checkmate" if not next_legal_moves else "evaluation"
                )

            # Switch turns
            game.current_turn = 2 if game.current_turn == 1 else 1
            next_player = game.get_current_player()

            # Queue AI move if next player is machine
            if (
                game.status == GameStatus.IN_PROGRESS
                and next_player.type == PlayerType.MACHINE
            ):
                await self.ai_move_queue.put(game_id)

            return MoveResponse(
                success=True,
                game_id=game_id,
                move=move,
                game_status=game.status,
                next_turn=game.current_turn,
                next_player_type=next_player.type,
                board_display=game.board_state.display,
                winner=game.winner,
            )

    async def get_legal_moves(self, game_id: str) -> List[str]:
        """Get legal moves for current position."""
        game = self.games.get(game_id)
        if not game:
            return []
        return await self._get_legal_moves_internal(game)

    async def _get_legal_moves_internal(
        self, game: GameSession, for_next_player: bool = False
    ) -> List[str]:
        """Internal method to get legal moves."""
        current_player = game.get_current_player()
        flip = not current_player.is_hero

        if for_next_player:
            flip = not flip

        mcts = await self.mcts_registry.get(game.game_id)
        if mcts is not None:
            sorted_actions = await mcts.get_sorted_actions_async(flip)
            return [action[2] for action in sorted_actions]
        return []

    async def get_board_display(self, game_id: str, flip: bool = False) -> str:
        """Get ASCII board display."""
        game = self.games.get(game_id)
        if not game:
            return ""
        mcts = await self.mcts_registry.get(game_id)
        if mcts is not None:
            display_result: str = await mcts.display_async(flip)
            return display_result
        return ""

    async def _get_board_state(self, game: GameSession) -> BoardState:
        """Get current board state."""
        display = ""
        mcts = await self.mcts_registry.get(game.game_id)
        if mcts is not None:
            display = await mcts.display_async(False)

        # Parse positions from display (simplified - would need actual parsing)
        # This is a placeholder - actual implementation would parse the board
        return BoardState(
            hero_position=Position(x=4, y=0),
            villain_position=Position(x=4, y=8),
            walls=[],
            display=display,
        )

    async def analyze_position(
        self, game_id: str, depth: int = 10000
    ) -> Dict[
        str, Union[str, float, List[Dict[str, Union[str, int, float]]], int, None]
    ]:
        """Analyze current position with MCTS."""
        game = self.games.get(game_id)
        if not game:
            return {}

        # Ensure minimum simulations
        mcts = await self.mcts_registry.get(game_id)
        if mcts is not None:
            await mcts.ensure_sims_async(depth)

        current_player = game.get_current_player()
        flip = not current_player.is_hero
        sorted_actions = []
        eval_result = None
        if mcts is not None:
            sorted_actions = await mcts.get_sorted_actions_async(flip)
            eval_result = await mcts.get_evaluation_async()

        return {
            "evaluation": eval_result,
            "sorted_actions": [
                {"action": action[2], "visits": action[0], "equity": action[1]}
                for action in sorted_actions[:10]
            ],
            "simulations": depth,
        }

    async def get_hint(
        self, game_id: str, simulations: int = 5000
    ) -> Dict[str, Union[str, float]]:
        """Get move hint using MCTS."""
        game = self.games.get(game_id)
        if not game:
            return {}

        # Run simulations
        best_action = ""
        mcts = await self.mcts_registry.get(game_id)
        if mcts is not None:
            await mcts.ensure_sims_async(simulations)
            # Get best move
            best_action = await mcts.choose_best_action_async(epsilon=0)

        # Get evaluation
        current_player = game.get_current_player()
        flip = not current_player.is_hero
        sorted_actions = []
        if mcts is not None:
            sorted_actions = await mcts.get_sorted_actions_async(flip)

        # Find the best action in sorted list
        best_info = next((a for a in sorted_actions if a[2] == best_action), None)

        if best_info:
            total_visits = sum(a[0] for a in sorted_actions)
            confidence = best_info[0] / total_visits if total_visits > 0 else 0

            return {
                "action": best_action,
                "confidence": confidence,
                "evaluation": best_info[1],
            }

        return {"action": best_action, "confidence": 0, "evaluation": 0}

    async def cleanup(self) -> None:
        """Clean up all resources."""
        # Cleanup all MCTS instances
        await self.mcts_registry.cleanup_all()

        # Clear game data
        async with self._global_lock:
            self.games.clear()
            self._game_locks.clear()
        
        self.matchmaking_queue.clear()

        # Clear the AI move queue
        while not self.ai_move_queue.empty():
            try:
                self.ai_move_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def resign_game(self, game_id: str, player_id: str) -> int:
        """Handle player resignation."""
        game_lock = await self._get_game_lock(game_id)
        async with game_lock:
            game = self.games.get(game_id)
            if not game:
                raise ValueError("Game not found")

            player = game.get_player(player_id)
            if not player:
                raise ValueError("Player not in game")

            # The other player wins
            game.winner = 2 if player.is_hero else 1
            game.status = GameStatus.COMPLETED
            game.ended_at = datetime.now(timezone.utc)
            game.termination_reason = "resignation"

            return game.winner

    async def trigger_ai_move(self, game_id: str) -> None:
        """Trigger AI to make a move."""
        await self.ai_move_queue.put(game_id)

    async def process_ai_moves(self) -> None:
        """Background task to process AI moves."""
        while True:
            try:
                # Use timeout to avoid blocking indefinitely
                game_id = await asyncio.wait_for(self.ai_move_queue.get(), timeout=1.0)

                game = self.games.get(game_id)
                if not game or game.status != GameStatus.IN_PROGRESS:
                    continue

                current_player = game.get_current_player()
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
                                game.settings.mcts_settings.min_simulations
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

                # Make the move
                await self.make_move(game_id, current_player.id, best_action)

                logger.info(f"AI made move in game {game_id}: {best_action}")

            except asyncio.TimeoutError:
                # No AI moves to process, continue
                continue
            except Exception as e:
                logger.error(f"Error processing AI move: {e}")
                # Add small delay to prevent tight error loops
                await asyncio.sleep(0.5)

    async def join_matchmaking(
        self, player_id: str, player_name: str, settings: Optional[GameSettings] = None
    ) -> Optional[GameSession]:
        """Join matchmaking queue."""
        async with self._lock:
            # Check if already in queue
            if any(p["player_id"] == player_id for p in self.matchmaking_queue):
                return None

            # Check for available opponent
            if self.matchmaking_queue:
                opponent = self.matchmaking_queue.pop(0)

                # Create game
                player1_name = str(opponent["player_name"])
                player1_id = str(opponent["player_id"])
                opponent_settings = opponent.get("settings")
                if isinstance(opponent_settings, GameSettings):
                    final_settings: Optional[GameSettings] = (
                        settings or opponent_settings
                    )
                else:
                    final_settings = settings

                game = await self.create_game(
                    player1_type=PlayerType.HUMAN,
                    player2_type=PlayerType.HUMAN,
                    player1_name=player1_name,
                    player2_name=player_name,
                    player1_id=player1_id,
                    player2_id=player_id,
                    settings=final_settings,
                )

                return game
            else:
                # Add to queue
                self.matchmaking_queue.append(
                    {
                        "player_id": player_id,
                        "player_name": player_name,
                        "settings": settings,
                        "joined_at": datetime.now(timezone.utc),
                    }
                )
                return None

    async def leave_matchmaking(self, player_id: str) -> bool:
        """Leave matchmaking queue."""
        async with self._lock:
            self.matchmaking_queue = [
                p for p in self.matchmaking_queue if p["player_id"] != player_id
            ]
            return True

    async def get_queue_position(self, player_id: str) -> int:
        """Get position in matchmaking queue."""
        for i, player in enumerate(self.matchmaking_queue):
            if player["player_id"] == player_id:
                return i + 1
        return -1

    async def get_active_game_count(self) -> int:
        """Get count of active games."""
        return sum(1 for g in self.games.values() if g.status == GameStatus.IN_PROGRESS)

    async def get_leaderboard(
        self, limit: int = 100
    ) -> List[Dict[str, Union[str, int, float]]]:
        """Get game leaderboard (placeholder)."""
        # This would typically query a database
        return []

    async def get_player_stats(
        self, player_id: str
    ) -> Optional[Dict[str, Union[str, int, float]]]:
        """Get player statistics (placeholder)."""
        # This would typically query a database
        games_played = sum(
            1
            for g in self.games.values()
            if g.is_player(player_id) and g.status == GameStatus.COMPLETED
        )

        wins = sum(
            1
            for g in self.games.values()
            if g.is_player(player_id)
            and g.status == GameStatus.COMPLETED
            and (
                (g.winner == 1 and g.player1.id == player_id)
                or (g.winner == 2 and g.player2.id == player_id)
            )
        )

        return {
            "player_id": player_id,
            "games_played": games_played,
            "wins": wins,
            "losses": games_played - wins,
            "win_rate": wins / games_played if games_played > 0 else 0,
        }
