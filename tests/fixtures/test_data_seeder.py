"""Test data seeding utilities for consistent test environments."""

import asyncio
import json
import uuid
from typing import Dict, List, Optional

import httpx
from httpx import AsyncClient


class TestDataSeeder:
    """Utility class for seeding test data in backend for integration tests."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = None

    async def __aenter__(self):
        self.client = AsyncClient(base_url=self.base_url)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def seed_test_games(self, count: int = 5) -> List[Dict]:
        """Seed test games with various configurations."""
        games = []
        
        for i in range(count):
            game_config = {
                "player1_type": "human",
                "player2_type": "machine" if i % 2 == 0 else "human",
                "player1_name": f"TestPlayer{i}_1",
                "player2_name": f"TestPlayer{i}_2" if i % 2 != 0 else "AI",
                "settings": {
                    "board_size": 9 if i < 3 else 7,
                    "time_limit_seconds": 30,
                    "use_analysis": i % 3 == 0
                }
            }
            
            response = await self.client.post("/games", json=game_config)
            if response.status_code == 200:
                games.append(response.json())
            else:
                print(f"Failed to create game {i}: {response.text}")
                
        return games

    async def seed_game_with_moves(self, move_sequence: List[str] = None) -> Dict:
        """Create a game and play through a sequence of moves."""
        if move_sequence is None:
            move_sequence = [
                "*(4,1)", "*(4,7)", "*(4,2)", "*(4,6)",  # Opening moves
                "H(3,2)", "V(4,6)", "*(3,2)", "*(5,6)"   # Some walls and moves
            ]
        
        # Create game
        game_config = {
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": "Seeder Player 1",
            "player2_name": "Seeder Player 2"
        }
        
        response = await self.client.post("/games", json=game_config)
        if response.status_code != 200:
            raise Exception(f"Failed to create game: {response.text}")
        
        game = response.json()
        game_id = game["game_id"]
        current_player = game["player1"]["id"]
        
        # Play moves
        for i, move in enumerate(move_sequence):
            player_id = game["player1"]["id"] if i % 2 == 0 else game["player2"]["id"]
            move_data = {
                "player_id": player_id,
                "action": move
            }
            
            response = await self.client.post(f"/games/{game_id}/moves", json=move_data)
            if response.status_code != 200:
                print(f"Failed to make move {move}: {response.text}")
                break
                
        # Get final game state
        response = await self.client.get(f"/games/{game_id}")
        return response.json() if response.status_code == 200 else game

    async def create_error_scenario_game(self, scenario: str = "invalid_move") -> Dict:
        """Create a game set up for specific error testing scenarios."""
        game_config = {
            "player1_type": "human",
            "player2_type": "human", 
            "player1_name": "Error Test P1",
            "player2_name": "Error Test P2"
        }
        
        response = await self.client.post("/games", json=game_config)
        if response.status_code != 200:
            raise Exception(f"Failed to create error scenario game: {response.text}")
            
        game = response.json()
        
        if scenario == "blocked_move":
            # Set up walls to block movement
            game_id = game["game_id"]
            wall_moves = ["H(3,4)", "H(4,4)", "H(5,4)"]  # Block horizontal path
            
            for i, wall in enumerate(wall_moves):
                player_id = game["player1"]["id"] if i % 2 == 0 else game["player2"]["id"]
                move_data = {"player_id": player_id, "action": wall}
                await self.client.post(f"/games/{game_id}/moves", json=move_data)
                
        elif scenario == "depleted_walls":
            # Play moves to deplete one player's walls
            game_id = game["game_id"]
            wall_moves = [f"H({i},{j})" for i in range(8) for j in range(2, 4)][:10]
            
            for i, wall in enumerate(wall_moves):
                player_id = game["player1"]["id"]  # Only player 1 places walls
                move_data = {"player_id": player_id, "action": wall}
                if i % 2 == 0:  # Alternate with opponent moves
                    await self.client.post(f"/games/{game_id}/moves", json=move_data)
                else:
                    # Opponent just moves
                    move_data = {"player_id": game["player2"]["id"], "action": f"*(4,{7-i%3})"}
                    await self.client.post(f"/games/{game_id}/moves", json=move_data)
        
        # Return updated game state
        response = await self.client.get(f"/games/{game_id}")
        return response.json() if response.status_code == 200 else game

    async def clear_all_games(self) -> int:
        """Clear all games from the backend (for test cleanup)."""
        response = await self.client.get("/games")
        if response.status_code != 200:
            return 0
            
        games = response.json().get("games", [])
        cleared_count = 0
        
        for game in games:
            delete_response = await self.client.delete(f"/games/{game['game_id']}")
            if delete_response.status_code in [200, 204]:
                cleared_count += 1
                
        return cleared_count

    async def get_health_status(self) -> Dict:
        """Get backend health status."""
        response = await self.client.get("/health")
        return response.json() if response.status_code == 200 else {"status": "unhealthy"}

    async def wait_for_backend_ready(self, timeout: int = 30) -> bool:
        """Wait for backend to be ready for testing."""
        for _ in range(timeout):
            try:
                health = await self.get_health_status()
                if health.get("status") == "healthy":
                    return True
            except:
                pass
            await asyncio.sleep(1)
        return False


class WebSocketTestSeeder:
    """Utility for seeding WebSocket-specific test scenarios."""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url

    async def create_connection_test_data(self) -> Dict:
        """Create data structure for WebSocket connection tests."""
        return {
            "connection_messages": [
                {"type": "connect", "message": "Connected to Corridors game server"},
                {"type": "ping", "data": "test_ping"},
                {"type": "pong", "data": "test_pong"}
            ],
            "game_messages": [
                {"type": "create_game", "data": {"mode": "human_vs_ai"}},
                {"type": "game_created", "game_id": "test-game-001"},
                {"type": "move", "data": {"game_id": "test-game-001", "move": "*(4,4)"}},
                {"type": "game_ended", "game_id": "test-game-001", "winner": "player1"}
            ],
            "error_messages": [
                {"type": "error", "error": "Invalid move", "code": 400},
                {"type": "error", "error": "Game not found", "code": 404},
                {"type": "error", "error": "Connection lost", "code": 1006}
            ]
        }

    def get_malformed_messages(self) -> List:
        """Get list of malformed messages for error testing."""
        return [
            "not json",
            '{"incomplete": ',
            '{"type": null}',
            '{"type": "unknown"}',
            '{"type": "move", "data": null}',
            b"binary data",
            "",
            "{'single_quotes': true}",  # Invalid JSON
            '{"very_large_message": "' + "x" * 10000 + '"}',  # Large message
        ]


# Helper functions for easy use in tests
async def seed_basic_test_data(backend_url: str) -> Dict:
    """Seed basic test data and return summary."""
    async with TestDataSeeder(backend_url) as seeder:
        await seeder.wait_for_backend_ready()
        
        # Clear any existing test data
        cleared = await seeder.clear_all_games()
        
        # Seed new data
        games = await seeder.seed_test_games(3)
        game_with_moves = await seeder.seed_game_with_moves()
        error_game = await seeder.create_error_scenario_game()
        
        return {
            "cleared_games": cleared,
            "seeded_games": len(games),
            "game_with_moves": game_with_moves["game_id"],
            "error_scenario_game": error_game["game_id"],
            "health": await seeder.get_health_status()
        }


def get_deterministic_game_id(prefix: str = "test") -> str:
    """Generate deterministic game ID for testing."""
    return f"{prefix}-game-{uuid.uuid4().hex[:8]}"


def get_deterministic_player_id(prefix: str = "test") -> str:
    """Generate deterministic player ID for testing."""
    return f"{prefix}-player-{uuid.uuid4().hex[:8]}"