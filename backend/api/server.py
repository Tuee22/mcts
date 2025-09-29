import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Union

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from backend.api.game_manager import GameManager
from corridors.async_mcts import ConcurrencyViolationError
from backend.api.models import (
    GameCreateRequest,
    GameListResponse,
    GameResponse,
    GameSession,
    GameSettings,
    GameStatus,
    MoveRequest,
    MoveResponse,
    Player,
    PlayerType,
)
from backend.api.game_states import (
    ActiveGame,
    CompletedGame,
    GameState,
    WaitingGame,
)
from backend.api.response_builders import build_game_response
from backend.api.websocket_manager import WebSocketManager
from backend.api.websocket_unified import unified_ws_manager, WSMessageData
from backend.api.websocket_models import (
    PongMessage,
    WebSocketMessage,
    parse_websocket_message,
)
from backend.api.pure_utils import validate_websocket_data
from backend.api.cleanup_config import CleanupConfig, RunMode

# Import uvicorn for optional server launching
import uvicorn


# Helper functions for working with GameState discriminated union


def game_is_in_progress(game: GameState) -> bool:
    """Check if game is in progress using pattern matching."""
    return isinstance(game, ActiveGame)


def game_has_player(game: GameState, player_id: str) -> bool:
    """Check if game has player using pattern matching."""
    match game:
        case ActiveGame() | CompletedGame():
            return game.player1.id == player_id or game.player2.id == player_id
        case _:
            return False


def get_game_current_player(game: GameState) -> Optional[Player]:
    """Get current player using pattern matching."""
    match game:
        case ActiveGame():
            return game.get_current_player()
        case _:
            return None


def get_game_current_turn(game: GameState) -> Optional[int]:
    """Get current turn using pattern matching."""
    match game:
        case ActiveGame():
            return game.current_turn
        case CompletedGame():
            return game.winner
        case _:
            return None


def get_game_move_count(game: GameState) -> int:
    """Get move count using pattern matching."""
    match game:
        case ActiveGame() | CompletedGame():
            return len(game.move_history)
        case _:
            return 0


def get_game_status(game: GameState) -> str:
    """Get game status using pattern matching."""
    match game:
        case ActiveGame():
            return GameStatus.IN_PROGRESS.value
        case CompletedGame():
            return GameStatus.COMPLETED.value
        case WaitingGame():
            return GameStatus.WAITING.value


def get_opponent_name(game: GameState, player_id: str) -> Optional[str]:
    """Get opponent name for a player using pattern matching."""
    match game:
        case ActiveGame() | CompletedGame():
            return (
                game.player2.name
                if game.player1.id == player_id
                else game.player1.name
                if game.player2.id == player_id
                else None
            )
        case _:
            return None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

game_manager: Optional[GameManager] = None
ws_manager: Optional[WebSocketManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global game_manager, ws_manager

    # Initialize managers
    game_manager = GameManager()
    ws_manager = WebSocketManager()

    # Determine which tasks to start using functional pattern matching
    config = CleanupConfig.from_environment()

    # Pattern matching for task startup based on runtime mode
    match config.mode:
        case RunMode.PRODUCTION:
            # Production: both AI processing and cleanup
            asyncio.create_task(game_manager.process_ai_moves())
            asyncio.create_task(game_manager.cleanup_inactive_games())
            logger.info(f"Started production tasks: AI processing + cleanup")
        case RunMode.TEST:
            # Test: only cleanup (no AI processing to avoid interference)
            asyncio.create_task(game_manager.cleanup_inactive_games())
            logger.info(f"Started test tasks: cleanup only")

    yield

    # Cleanup (same for all modes)
    await game_manager.cleanup()
    await ws_manager.disconnect_all()
    await unified_ws_manager.cleanup()


app = FastAPI(
    title="Corridors Game API",
    description="RESTful API for Corridors game with MCTS AI",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(ConcurrencyViolationError)
async def concurrency_violation_handler(
    request: Request, exc: ConcurrencyViolationError
) -> JSONResponse:
    """
    Global exception handler for race conditions - LOUD FAILURE.

    This ensures that any race condition detected at any level
    (async_mcts, registry, or API) results in a loud server error
    that crashes the request and gets logged prominently.
    """
    error_msg = f"RACE CONDITION DETECTED: {exc}"
    logger.error(
        f"🚨 CONCURRENCY VIOLATION 🚨 Request: {request.method} {request.url} | Error: {error_msg}"
    )

    # Return 500 Internal Server Error with detailed message for debugging
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "Race condition detected - concurrent access to game state",
            "message": str(exc),
            "type": "ConcurrencyViolationError",
        },
    )


# Create API router for /api-prefixed endpoints (health only)
api_router = APIRouter(prefix="/api")

# Static files configuration for frontend - build artifacts outside /app
FRONTEND_BUILD_DIR = Path("/opt/mcts/frontend-build/build")


def setup_static_files() -> None:
    """Setup static file serving for pre-built frontend."""
    # Mount static assets first (CSS, JS, images, etc.)
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_BUILD_DIR / "static")),
        name="static",
    )

    # Serve other static files (favicon, manifest, etc.)
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_BUILD_DIR)), name="assets")
    logger.info(f"Static files configured from {FRONTEND_BUILD_DIR}")


# Setup static files
setup_static_files()

# CORS configuration - removed for single-server architecture
# All requests come from same origin, no CORS needed


# ==================== WebSocket Endpoints ====================


@app.websocket("/ws")
async def websocket_unified_endpoint(websocket: WebSocket) -> None:
    """
    Unified WebSocket endpoint for all game communication.

    Replaces the previous dual-endpoint system (/ws and /games/{id}/ws)
    with a single endpoint using message-based routing.
    """
    connection_id = None
    try:
        # Connect to the unified WebSocket manager
        connection_id = await unified_ws_manager.connect(websocket)

        # Handle incoming messages
        while True:
            # Receive JSON message from client
            raw_data = await websocket.receive_json()

            # raw_data is guaranteed to be a dict by receive_json()

            # Special handling for ping messages: copy root-level fields to data
            if raw_data.get("type") == "ping":
                data_field = raw_data.get("data", {})
                if isinstance(data_field, dict):
                    # Copy all root-level fields (except standard ones) to data
                    for key, value in raw_data.items():
                        if key not in {"type", "id", "data", "error", "timestamp"}:
                            data_field[key] = value
                    raw_data["data"] = data_field

            # Process the message through the unified manager
            # Use functional validation with ternary operator
            validated_data: WSMessageData = (
                {
                    k: v
                    for k, v in raw_data.items()
                    if isinstance(v, (str, int, float, bool, dict))
                }
                if isinstance(raw_data, dict) and raw_data.get("type") == "ping"
                else validate_websocket_data(raw_data)
            )

            response = await unified_ws_manager.handle_message(
                connection_id, validated_data
            )

            # Send response if one was generated
            if response:
                await unified_ws_manager._send_to_connection(connection_id, response)

    except WebSocketDisconnect:
        if connection_id:
            await unified_ws_manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if connection_id:
            await unified_ws_manager.disconnect(connection_id)


# ==================== Game Management Endpoints ====================


@app.post("/games", response_model=GameResponse)
async def create_game(request: GameCreateRequest) -> GameResponse:
    """
    Create a new game session.

    Supports three modes:
    - Player vs Player (PvP)
    - Player vs Machine (PvM)
    - Machine vs Machine (MvM)
    """
    if game_manager is None or ws_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        # Add timeout to prevent hanging requests
        game = await asyncio.wait_for(
            game_manager.create_game(
                player1_type=request.player1_type,
                player2_type=request.player2_type,
                player1_name=request.player1_name,
                player2_name=request.player2_name,
                settings=request.settings,
            ),
            timeout=10.0,  # 10 second timeout
        )

        # Notify WebSocket clients about new game
        await ws_manager.broadcast_game_created(game.game_id)

        return build_game_response(game)
    except asyncio.TimeoutError:
        logger.error("Game creation timed out")
        raise HTTPException(status_code=504, detail="Game creation timed out")
    except Exception as e:
        logger.error(f"Failed to create game: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/games", response_model=GameListResponse)
async def list_games(
    status: Optional[GameStatus] = None,
    player_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> GameListResponse:
    """List all games with optional filtering."""
    if game_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        games = await game_manager.list_games(
            status=status, player_id=player_id, limit=limit, offset=offset
        )
        return GameListResponse(
            games=[build_game_response(g) for g in games], total=len(games)
        )
    except Exception as e:
        logger.error(f"Failed to list games: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/games/{game_id}", response_model=GameResponse)
async def get_game(game_id: str) -> GameResponse:
    """Get detailed information about a specific game."""
    if game_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        game = await game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        return build_game_response(game)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get game: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/games/{game_id}")
async def delete_game(game_id: str) -> Dict[str, str]:
    """Delete/cancel a game session."""
    if game_manager is None or ws_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        success = await game_manager.delete_game(game_id)
        if not success:
            raise HTTPException(status_code=404, detail="Game not found")

        await ws_manager.broadcast_game_ended(game_id, "cancelled")
        return {"message": "Game deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete game: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Game Play Endpoints ====================


@app.post("/games/{game_id}/moves", response_model=MoveResponse)
async def make_move(
    game_id: str, request: MoveRequest, background_tasks: BackgroundTasks
) -> MoveResponse:
    """
    Make a move in the game.

    Action format:
    - *(X,Y): Move token to position (X,Y)
    - H(X,Y): Place horizontal wall at (X,Y)
    - V(X,Y): Place vertical wall at (X,Y)
    """
    if game_manager is None or ws_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    game = await game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if not game_is_in_progress(game):
        raise HTTPException(status_code=400, detail="Game is not in progress")

    # Validate it's the player's turn
    current_player = get_game_current_player(game)
    if current_player is None:
        raise HTTPException(status_code=400, detail="Cannot determine current player")
    if (
        current_player.type == PlayerType.HUMAN
        and current_player.id != request.player_id
    ):
        raise HTTPException(status_code=403, detail="Not your turn")

    try:
        # Apply the move
        result = await game_manager.make_move(
            game_id=game_id, player_id=request.player_id, action=request.action
        )

        # Broadcast move to WebSocket clients
        await ws_manager.broadcast_move(game_id, result)

        # If next player is AI, trigger AI move processing
        if result.next_player_type == PlayerType.MACHINE:
            background_tasks.add_task(game_manager.trigger_ai_move, game_id)

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to make move: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/games/{game_id}/legal-moves")
async def get_legal_moves(
    game_id: str, player_id: Optional[str] = None
) -> Dict[str, Union[str, int, List[str]]]:
    """Get all legal moves for the current position."""
    if game_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        game = await game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        # Optionally validate player access
        if player_id and not game_has_player(game, player_id):
            raise HTTPException(status_code=403, detail="Not a player in this game")

        legal_moves = await game_manager.get_legal_moves(game_id)
        return {
            "game_id": game_id,
            "current_player": get_game_current_turn(game) or 0,
            "legal_moves": legal_moves,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get legal moves: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/games/{game_id}/board")
async def get_board_state(
    game_id: str, player_id: Optional[str] = None, flip: bool = False
) -> Dict[str, Union[str, int, Optional[str], Optional[int]]]:
    """Get the current board state visualization."""
    if game_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        game = await game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        board_display = await game_manager.get_board_display(game_id, flip)
        return {
            "game_id": game_id,
            "board": board_display,
            "current_turn": get_game_current_turn(game),
            "move_count": get_game_move_count(game),
            "status": get_game_status(game),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get board state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/games/{game_id}/resign")
async def resign_game(game_id: str, player_id: str) -> Dict[str, Union[str, int]]:
    """Allow a player to resign from the game."""
    if game_manager is None or ws_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        game = await game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if not game_has_player(game, player_id):
            raise HTTPException(status_code=403, detail="Not a player in this game")

        winner = await game_manager.resign_game(game_id, player_id)
        await ws_manager.broadcast_game_ended(game_id, "resignation", winner)

        return {"message": "Game resigned", "winner": winner}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resign game: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI Analysis Endpoints ====================


@app.get("/games/{game_id}/analysis")
async def get_position_analysis(
    game_id: str, depth: Optional[int] = 10000, player_id: Optional[str] = None
) -> Dict[str, Union[str, float, List[Dict[str, Union[str, int, float]]], int, None]]:
    """
    Get AI analysis of the current position.
    Returns sorted actions with visit counts and evaluations.
    """
    if game_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        game = await game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        # Ensure depth is not None
        analysis_depth = depth if depth is not None else 10000
        analysis = await game_manager.analyze_position(game_id, analysis_depth)

        sorted_actions = analysis.get("sorted_actions", [])
        best_moves = sorted_actions[:10] if isinstance(sorted_actions, list) else []

        return {
            "game_id": game_id,
            "position_evaluation": analysis.get("evaluation"),
            "best_moves": best_moves,
            "total_simulations": analysis.get("simulations"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/games/{game_id}/hint")
async def get_move_hint(
    game_id: str, player_id: str, simulations: int = 5000
) -> Dict[str, Union[str, float]]:
    """Get AI suggestion for the best move."""
    if game_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        game = await game_manager.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        if not game_has_player(game, player_id):
            raise HTTPException(status_code=403, detail="Not a player in this game")

        hint = await game_manager.get_hint(game_id, simulations)
        return {
            "suggested_move": hint["action"],
            "confidence": hint["confidence"],
            "evaluation": hint["evaluation"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WebSocket Endpoints ====================


@app.websocket("/games/{game_id}/ws")
async def websocket_endpoint(websocket: WebSocket, game_id: str) -> None:
    """
    WebSocket connection for real-time game updates.

    Clients receive:
    - Move notifications
    - Game state changes
    - Player connection/disconnection events
    """
    if game_manager is None or ws_manager is None:
        await websocket.close(code=1011)
        return
    game = await game_manager.get_game(game_id)
    if not game:
        await websocket.close(code=4004)
        return

    await ws_manager.connect(websocket, game_id)

    try:
        # Send initial game state directly to the new connection
        game_response = build_game_response(game)

        # Get legal moves for current position
        legal_moves = []
        try:
            legal_moves = await game_manager.get_legal_moves(game_id)
        except Exception as e:
            logger.error(f"Failed to get legal moves: {e}")

        game_data = {
            "type": "game_state",
            "data": {
                "game_id": game_response.game_id,
                "status": game_response.status,
                "player1_id": game_response.player1.id,
                "player2_id": game_response.player2.id,
                "current_turn": game_response.current_turn,
                "winner": game_response.winner,
                "board_display": game_response.board_display,
                "board_size": 9,  # Default board size - could be made configurable
                "legal_moves": legal_moves,
                "created_at": game_response.created_at.isoformat(),
            },
        }
        await websocket.send_json(game_data)

        # Keep connection alive and handle incoming messages
        while True:
            raw_data = await websocket.receive_json()

            # Parse and validate message using Pydantic
            try:
                # raw_data is guaranteed to be a dict by receive_json()
                message = parse_websocket_message(raw_data)
            except (ValidationError, ValueError) as e:
                logger.warning(f"Invalid WebSocket message: {e}")
                continue

            # Handle different message types
            if message.type == "ping":
                response = PongMessage(type="pong")
                await websocket.send_json(response.model_dump())
            elif message.type == "move":
                # Alternative way to make moves via WebSocket
                try:
                    move_result = await game_manager.make_move(
                        game_id=game_id,
                        player_id=message.player_id,
                        action=message.action,
                    )
                    await ws_manager.broadcast_move(game_id, move_result)

                    # Send updated game state
                    game = await game_manager.get_game(game_id)
                    if game:
                        game_response = build_game_response(game)
                        legal_moves = []
                        try:
                            legal_moves = await game_manager.get_legal_moves(game_id)
                        except Exception as e:
                            logger.error(f"Failed to get legal moves after move: {e}")

                        game_data = {
                            "type": "game_state",
                            "data": {
                                "game_id": game_response.game_id,
                                "status": game_response.status,
                                "player1_id": game_response.player1.id,
                                "player2_id": game_response.player2.id,
                                "current_turn": game_response.current_turn,
                                "winner": game_response.winner,
                                "board_display": game_response.board_display,
                                "board_size": 9,  # Default board size - could be made configurable
                                "legal_moves": legal_moves,
                                "created_at": game_response.created_at.isoformat(),
                            },
                        }
                        await websocket.send_json(game_data)
                except Exception as e:
                    logger.error(f"Failed to make move via WebSocket: {e}")
                    await websocket.send_json(
                        {"type": "error", "error": f"Failed to make move: {str(e)}"}
                    )

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, game_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_manager.disconnect(websocket, game_id)


# ==================== Tournament/Matchmaking Endpoints ====================


@app.post("/matchmaking/queue")
async def join_matchmaking_queue(
    player_id: str, player_name: str, settings: Optional[GameSettings] = None
) -> Dict[str, Union[str, int]]:
    """Join the matchmaking queue to find an opponent."""
    if game_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        match = await game_manager.join_matchmaking(player_id, player_name, settings)

        if match:
            # Find opponent name based on which player the current player is
            opponent_name = get_opponent_name(match, player_id)
            if opponent_name is None:
                raise HTTPException(status_code=500, detail="Invalid match state")
            return {
                "status": "matched",
                "game_id": match.game_id,
                "opponent": opponent_name,
            }
        else:
            return {
                "status": "queued",
                "position": await game_manager.get_queue_position(player_id),
            }
    except Exception as e:
        logger.error(f"Failed to join matchmaking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/matchmaking/queue/{player_id}")
async def leave_matchmaking_queue(player_id: str) -> Dict[str, str]:
    """Leave the matchmaking queue."""
    if game_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        success = await game_manager.leave_matchmaking(player_id)
        if not success:
            raise HTTPException(status_code=404, detail="Player not in queue")
        return {"message": "Left matchmaking queue"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to leave matchmaking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Statistics Endpoints ====================


@app.get("/stats/leaderboard")
async def get_leaderboard(
    limit: int = 100,
) -> Dict[str, List[Dict[str, Union[str, int, float]]]]:
    """Get the game leaderboard."""
    if game_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        leaderboard = await game_manager.get_leaderboard(limit)
        return {"leaderboard": leaderboard}
    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/player/{player_id}")
async def get_player_stats(player_id: str) -> Dict[str, Union[str, int, float]]:
    """Get statistics for a specific player."""
    if game_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    try:
        stats = await game_manager.get_player_stats(player_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Player not found")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get player stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Simple WebSocket for Frontend ====================


# ==================== Health Check ====================


@app.get("/health")
async def health_check() -> Dict[str, Union[str, int]]:
    """Health check endpoint."""
    if game_manager is None or ws_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return {
        "status": "healthy",
        "active_games": await game_manager.get_active_game_count(),
        "connected_clients": ws_manager.get_connection_count(),
    }

    # Duplicate health endpoint removed - use /health instead


# ==================== Test Endpoints for E2E Tests ====================


@app.get("/test/external", response_model=None)
async def test_external_page() -> Dict[str, str]:
    """Mock external page for browser navigation tests."""
    return {
        "status": "success",
        "message": "This is a mock external page for testing",
        "page": "external",
    }


@app.get("/test/api", response_model=None)
async def test_api_page() -> Dict[str, Union[str, Dict[str, str]]]:
    """Mock API endpoint for browser navigation tests."""
    return {
        "status": "success",
        "message": "This is a mock API endpoint for testing",
        "data": {"timestamp": datetime.now().isoformat()},
    }


# Include API router after all routes are defined
app.include_router(api_router)

# ==================== Frontend SPA Routes ====================


@app.get("/manifest.json", response_model=None)
async def manifest() -> FileResponse:
    """Serve the PWA manifest file."""
    manifest_path = FRONTEND_BUILD_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(str(manifest_path))
    raise HTTPException(status_code=404, detail="Manifest not found")


@app.get("/favicon.ico", response_model=None)
async def favicon() -> FileResponse:
    """Serve the favicon."""
    favicon_path = FRONTEND_BUILD_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/robots.txt", response_model=None)
async def robots() -> FileResponse:
    """Serve the robots.txt file."""
    robots_path = FRONTEND_BUILD_DIR / "robots.txt"
    if robots_path.exists():
        return FileResponse(str(robots_path))
    raise HTTPException(status_code=404, detail="Robots.txt not found")


@app.get("/{full_path:path}", response_model=None)
async def serve_spa(request: Request, full_path: str) -> FileResponse:
    """Serve the React SPA for any non-API routes."""
    # Don't serve SPA for API routes
    if full_path.startswith(
        (
            "api/",
            "games",
            "matchmaking",
            "stats",
            "ws",
            "health",
            "docs",
            "openapi.json",
            "redoc",
        )
    ):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    # Serve index.html for all other routes (React Router will handle routing)
    index_path = FRONTEND_BUILD_DIR / "index.html"
    return FileResponse(str(index_path), media_type="text/html")


def main() -> None:
    """Production server entry point."""
    # Just run FastAPI directly, Socket.IO will be handled via endpoints
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def dev() -> None:
    """Development server entry point with auto-reload."""
    uvicorn.run(
        "api.server:app", host="0.0.0.0", port=8000, reload=True, log_level="debug"
    )


if __name__ == "__main__":
    main()
