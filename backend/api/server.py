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
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .game_manager import GameManager
from .models import (
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
from .websocket_manager import WebSocketManager
from .websocket_models import PongMessage, WebSocketMessage, parse_websocket_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

game_manager: Optional[GameManager] = None
ws_manager: Optional[WebSocketManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global game_manager, ws_manager
    game_manager = GameManager()
    ws_manager = WebSocketManager()

    # Only start background task processor in production (not during tests)
    import os

    if os.environ.get("PYTEST_CURRENT_TEST") is None:
        asyncio.create_task(game_manager.process_ai_moves())

    yield

    # Cleanup
    await game_manager.cleanup()
    await ws_manager.disconnect_all()


app = FastAPI(
    title="Corridors Game API",
    description="RESTful API for Corridors game with MCTS AI",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files configuration for frontend - updated for container path
FRONTEND_BUILD_DIR = Path("/app/frontend/build")

def setup_static_files() -> None:
    """Setup static file serving if frontend build exists."""
    if FRONTEND_BUILD_DIR.exists():
        # Mount static assets first (CSS, JS, images, etc.)
        app.mount(
            "/static",
            StaticFiles(directory=str(FRONTEND_BUILD_DIR / "static")),
            name="static",
        )

        # Serve other static files (favicon, manifest, etc.)
        app.mount(
            "/assets", 
            StaticFiles(directory=str(FRONTEND_BUILD_DIR)), 
            name="assets"
        )
        logger.info(f"Static files configured from {FRONTEND_BUILD_DIR}")
    else:
        logger.warning(f"Frontend build directory not found: {FRONTEND_BUILD_DIR}")
        logger.warning("Run 'npm run build' in the frontend directory")

# Setup static files
setup_static_files()

# CORS configuration - removed for single-server architecture
# All requests come from same origin, no CORS needed


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
        game = await game_manager.create_game(
            player1_type=request.player1_type,
            player2_type=request.player2_type,
            player1_name=request.player1_name,
            player2_name=request.player2_name,
            settings=request.settings,
        )

        # Notify WebSocket clients about new game
        await ws_manager.broadcast_game_created(game.game_id)

        return GameResponse.from_game_session(game)
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
            games=[GameResponse.from_game_session(g) for g in games], total=len(games)
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
        return GameResponse.from_game_session(game)
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

    if game.status != GameStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Game is not in progress")

    # Validate it's the player's turn
    current_player = game.get_current_player()
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
        if player_id and not game.is_player(player_id):
            raise HTTPException(status_code=403, detail="Not a player in this game")

        legal_moves = await game_manager.get_legal_moves(game_id)
        return {
            "game_id": game_id,
            "current_player": game.current_turn,
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
) -> Dict[str, Union[str, int, Optional[str]]]:
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
            "current_turn": game.current_turn,
            "move_count": len(game.move_history),
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

        if not game.is_player(player_id):
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

        if not game.is_player(player_id):
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
        # Send initial game state
        game_response = GameResponse.from_game_session(game)
        await ws_manager.broadcast_game_state(game_id, game_response)

        # Keep connection alive and handle incoming messages
        while True:
            raw_data = await websocket.receive_json()

            # Parse and validate message using Pydantic
            try:
                if not isinstance(raw_data, dict):
                    logger.warning("WebSocket message must be a dict")
                    continue
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
                move_result = await game_manager.make_move(
                    game_id=game_id,
                    player_id=message.player_id,
                    action=message.action,
                )
                await ws_manager.broadcast_move(game_id, move_result)

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
            opponent_name = (
                match.player2.name
                if match.player1.id == player_id
                else match.player1.name
            )
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


@app.websocket("/ws")
async def simple_websocket_endpoint(websocket: WebSocket) -> None:
    """Simple WebSocket connection for frontend."""
    await websocket.accept()

    try:
        # Send connection confirmation
        from .websocket_models import ConnectMessage

        connect_response = ConnectMessage(type="connect")
        await websocket.send_json(connect_response.model_dump())

        # Keep connection alive
        while True:
            try:
                # Try to receive JSON message first
                try:
                    data = await websocket.receive_json()
                except ValueError:
                    # If JSON parsing fails, try to receive as text
                    try:
                        text_data = await websocket.receive_text()
                        logger.warning(f"Invalid JSON in text message: {text_data}")
                        continue
                    except Exception:
                        # If text also fails, just log the error and continue
                        logger.warning("Failed to parse message as JSON or text")
                        continue

                # Parse and validate message using Pydantic
                try:
                    if not isinstance(data, dict):
                        logger.warning("WebSocket message must be a dict")
                        continue
                    message = parse_websocket_message(data)

                    if message.type == "ping":
                        response = PongMessage(type="pong")
                        await websocket.send_json(response.model_dump())
                    elif message.type == "create_game":
                        await websocket.send_json(
                            {"type": "game_created", "game_id": "test_game_123"}
                        )

                except (ValidationError, ValueError) as e:
                    logger.warning(f"Invalid WebSocket message: {e}")
                    continue

            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


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
async def serve_spa(
    request: Request, full_path: str
) -> Union[FileResponse, Dict[str, str]]:
    """Serve the React SPA for any non-API routes."""
    # Don't serve SPA for API routes
    if full_path.startswith(
        (
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
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")

    # Fallback if frontend build doesn't exist
    return {
        "message": "Frontend not built. Run 'npm run build' in the frontend directory."
    }


def main() -> None:
    """Production server entry point."""
    import uvicorn

    # Just run FastAPI directly, Socket.IO will be handled via endpoints
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def dev() -> None:
    """Development server entry point with auto-reload."""
    import uvicorn

    uvicorn.run(
        "api.server:app", host="0.0.0.0", port=8000, reload=True, log_level="debug"
    )


if __name__ == "__main__":
    main()
