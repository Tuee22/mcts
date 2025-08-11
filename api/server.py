from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Optional, List, Any
import asyncio
import uuid
from datetime import datetime
import logging

from .models import (
    GameCreateRequest, GameResponse, MoveRequest, MoveResponse,
    GameStatus, PlayerType, Player, GameSession,
    GameListResponse, GameSettings
)
from .game_manager import GameManager
from .websocket_manager import WebSocketManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

game_manager: GameManager = None
ws_manager: WebSocketManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global game_manager, ws_manager
    game_manager = GameManager()
    ws_manager = WebSocketManager()
    
    # Only start background task processor in production (not during tests)
    import os
    if os.environ.get('PYTEST_CURRENT_TEST') is None:
        asyncio.create_task(game_manager.process_ai_moves())
    
    yield
    
    # Cleanup
    await game_manager.cleanup()
    await ws_manager.disconnect_all()


app = FastAPI(
    title="Corridors Game API",
    description="RESTful API for Corridors game with MCTS AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    try:
        game = await game_manager.create_game(
            player1_type=request.player1_type,
            player2_type=request.player2_type,
            player1_name=request.player1_name,
            player2_name=request.player2_name,
            settings=request.settings
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
    offset: int = 0
) -> GameListResponse:
    """List all games with optional filtering."""
    games = await game_manager.list_games(
        status=status,
        player_id=player_id,
        limit=limit,
        offset=offset
    )
    return GameListResponse(
        games=[GameResponse.from_game_session(g) for g in games],
        total=len(games)
    )


@app.get("/games/{game_id}", response_model=GameResponse)
async def get_game(game_id: str) -> GameResponse:
    """Get detailed information about a specific game."""
    game = await game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return GameResponse.from_game_session(game)


@app.delete("/games/{game_id}")
async def delete_game(game_id: str):
    """Delete/cancel a game session."""
    success = await game_manager.delete_game(game_id)
    if not success:
        raise HTTPException(status_code=404, detail="Game not found")
    
    await ws_manager.broadcast_game_ended(game_id, "cancelled")
    return {"message": "Game deleted successfully"}


# ==================== Game Play Endpoints ====================

@app.post("/games/{game_id}/moves", response_model=MoveResponse)
async def make_move(
    game_id: str,
    request: MoveRequest,
    background_tasks: BackgroundTasks
) -> MoveResponse:
    """
    Make a move in the game.
    
    Action format:
    - *(X,Y): Move token to position (X,Y)
    - H(X,Y): Place horizontal wall at (X,Y)
    - V(X,Y): Place vertical wall at (X,Y)
    """
    game = await game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.status != GameStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Game is not in progress")
    
    # Validate it's the player's turn
    current_player = game.get_current_player()
    if current_player.type == PlayerType.HUMAN and current_player.id != request.player_id:
        raise HTTPException(status_code=403, detail="Not your turn")
    
    try:
        # Apply the move
        result = await game_manager.make_move(
            game_id=game_id,
            player_id=request.player_id,
            action=request.action
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
async def get_legal_moves(game_id: str, player_id: Optional[str] = None):
    """Get all legal moves for the current position."""
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
        "legal_moves": legal_moves
    }


@app.get("/games/{game_id}/board")
async def get_board_state(
    game_id: str,
    player_id: Optional[str] = None,
    flip: bool = False
):
    """Get the current board state visualization."""
    game = await game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    board_display = await game_manager.get_board_display(game_id, flip)
    return {
        "game_id": game_id,
        "board": board_display,
        "current_turn": game.current_turn,
        "move_count": len(game.move_history)
    }


@app.post("/games/{game_id}/resign")
async def resign_game(game_id: str, player_id: str):
    """Allow a player to resign from the game."""
    game = await game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if not game.is_player(player_id):
        raise HTTPException(status_code=403, detail="Not a player in this game")
    
    winner = await game_manager.resign_game(game_id, player_id)
    await ws_manager.broadcast_game_ended(game_id, "resignation", winner)
    
    return {
        "message": "Game resigned",
        "winner": winner
    }


# ==================== AI Analysis Endpoints ====================

@app.get("/games/{game_id}/analysis")
async def get_position_analysis(
    game_id: str,
    depth: Optional[int] = 10000,
    player_id: Optional[str] = None
):
    """
    Get AI analysis of the current position.
    Returns sorted actions with visit counts and evaluations.
    """
    game = await game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    analysis = await game_manager.analyze_position(game_id, depth)
    return {
        "game_id": game_id,
        "position_evaluation": analysis.get("evaluation"),
        "best_moves": analysis.get("sorted_actions", [])[:10],
        "total_simulations": analysis.get("simulations")
    }


@app.post("/games/{game_id}/hint")
async def get_move_hint(
    game_id: str,
    player_id: str,
    simulations: int = 5000
):
    """Get AI suggestion for the best move."""
    game = await game_manager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if not game.is_player(player_id):
        raise HTTPException(status_code=403, detail="Not a player in this game")
    
    hint = await game_manager.get_hint(game_id, simulations)
    return {
        "suggested_move": hint["action"],
        "confidence": hint["confidence"],
        "evaluation": hint["evaluation"]
    }


# ==================== WebSocket Endpoints ====================

@app.websocket("/games/{game_id}/ws")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    """
    WebSocket connection for real-time game updates.
    
    Clients receive:
    - Move notifications
    - Game state changes
    - Player connection/disconnection events
    """
    game = await game_manager.get_game(game_id)
    if not game:
        await websocket.close(code=4004, reason="Game not found")
        return
    
    await ws_manager.connect(websocket, game_id)
    
    try:
        # Send initial game state
        await websocket.send_json({
            "type": "game_state",
            "data": GameResponse.from_game_session(game).dict()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "move":
                # Alternative way to make moves via WebSocket
                move_result = await game_manager.make_move(
                    game_id=game_id,
                    player_id=data["player_id"],
                    action=data["action"]
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
    player_id: str,
    player_name: str,
    settings: Optional[GameSettings] = None
):
    """Join the matchmaking queue to find an opponent."""
    match = await game_manager.join_matchmaking(player_id, player_name, settings)
    
    if match:
        return {
            "status": "matched",
            "game_id": match.game_id,
            "opponent": match.opponent_name
        }
    else:
        return {
            "status": "queued",
            "position": await game_manager.get_queue_position(player_id)
        }


@app.delete("/matchmaking/queue/{player_id}")
async def leave_matchmaking_queue(player_id: str):
    """Leave the matchmaking queue."""
    success = await game_manager.leave_matchmaking(player_id)
    if not success:
        raise HTTPException(status_code=404, detail="Player not in queue")
    return {"message": "Left matchmaking queue"}


# ==================== Statistics Endpoints ====================

@app.get("/stats/leaderboard")
async def get_leaderboard(limit: int = 100):
    """Get the game leaderboard."""
    leaderboard = await game_manager.get_leaderboard(limit)
    return {"leaderboard": leaderboard}


@app.get("/stats/player/{player_id}")
async def get_player_stats(player_id: str):
    """Get statistics for a specific player."""
    stats = await game_manager.get_player_stats(player_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Player not found")
    return stats


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_games": await game_manager.get_active_game_count(),
        "connected_clients": ws_manager.get_connection_count()
    }


def main():
    """Production server entry point."""
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


def dev():
    """Development server entry point with auto-reload."""
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )


if __name__ == "__main__":
    dev()