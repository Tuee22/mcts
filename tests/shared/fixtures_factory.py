"""
Unified test fixtures factory for both frontend and backend tests.

Provides consistent mock data and responses across all test types to ensure
compatibility with the new REST API structure.
"""

from typing import Callable, Dict, List, Optional, TypedDict
from datetime import datetime
import uuid


class PlayerInfoDict(TypedDict):
    """Player information dictionary type."""

    id: str
    name: str
    type: str


class AIConfigDict(TypedDict):
    """AI configuration dictionary type."""

    difficulty: str
    time_limit_ms: int
    use_mcts: bool
    mcts_iterations: int


class MoveDict(TypedDict):
    """Move information dictionary type."""

    player_id: str
    action: str
    move_number: int
    timestamp: str


class GameResponseDict(TypedDict):
    """Game response dictionary type."""

    game_id: str
    status: str
    player1: PlayerInfoDict
    player2: PlayerInfoDict
    current_turn: int
    move_count: int
    board_display: str
    winner: Optional[str]
    created_at: str
    mode: str
    board_size: int
    move_history: List[Dict[str, str]]
    legal_moves: List[str]


class GameRequestDict(TypedDict, total=False):
    """Game creation request dictionary type."""

    mode: str
    board_size: int
    ai_config: AIConfigDict


class MoveRequestDict(TypedDict):
    """Move request dictionary type."""

    player_id: str
    action: str


class MoveResponseDict(TypedDict):
    """Move response dictionary type."""

    move: MoveDict
    game_state: GameResponseDict


class WebSocketMessageDict(TypedDict, total=False):
    """WebSocket message dictionary type."""

    type: str
    game_id: str


class ErrorResponseDict(TypedDict, total=False):
    """Error response dictionary type."""

    error: str
    code: int
    details: str


class LegalMovesResponseDict(TypedDict):
    """Legal moves response dictionary type."""

    legal_moves: List[str]


class FrontendGameSettingsDict(TypedDict):
    """Frontend game settings dictionary type."""

    mode: str
    ai_difficulty: str
    ai_time_limit: int
    board_size: int
    player1_type: str
    player2_type: str


class WebSocketServiceMockDict(TypedDict):
    """WebSocket service mock dictionary type."""

    connect: Callable[[], None]
    disconnect: Callable[[], None]
    disconnectFromGame: Callable[[], None]
    isConnected: Callable[[], bool]
    createGame: Callable[[Dict[str, str]], GameResponseDict]
    makeMove: Callable[[str, str], None]
    getAIMove: Callable[[str], None]
    joinGame: Callable[[str], None]
    requestGameState: Callable[[str], GameResponseDict]
    connectToGame: Callable[[str], None]


class TestFixturesFactory:
    """Factory class for creating consistent test fixtures."""

    @staticmethod
    def create_game_response(
        game_id: Optional[str] = None,
        status: str = "in_progress",
        mode: str = "human_vs_ai",
        current_turn: int = 1,
        move_count: int = 0,
        winner: Optional[str] = None,
        board_size: int = 9,
    ) -> GameResponseDict:
        """Create a consistent GameResponse object for tests."""
        if game_id is None:
            game_id = f"test-game-{uuid.uuid4().hex[:8]}"

        return {
            "game_id": game_id,
            "status": status,
            "player1": {"id": "player1", "name": "Player 1", "type": "human"},
            "player2": {
                "id": "player2",
                "name": "Player 2" if mode == "human_vs_human" else "AI",
                "type": "human" if mode == "human_vs_human" else "ai",
            },
            "current_turn": current_turn,
            "move_count": move_count,
            "board_display": TestFixturesFactory._create_board_display(board_size),
            "winner": winner,
            "created_at": datetime.now().isoformat(),
            "mode": mode,
            "board_size": board_size,
            "move_history": [],
            "legal_moves": ["e2", "e4", "wall_h_3_4", "wall_v_2_3"],
        }

    @staticmethod
    def create_game_request(
        mode: str = "human_vs_ai",
        ai_difficulty: str = "medium",
        ai_time_limit: int = 5000,
        board_size: int = 9,
    ) -> GameRequestDict:
        """Create a game creation request object."""
        ai_config = AIConfigDict(
            difficulty=ai_difficulty,
            time_limit_ms=ai_time_limit,
            use_mcts=ai_difficulty != "easy",
            mcts_iterations={
                "easy": 100,
                "medium": 1000,
                "hard": 5000,
                "expert": 10000,
            }.get(ai_difficulty, 1000),
        )

        request = GameRequestDict(
            mode=mode,
            board_size=board_size,
        )

        if mode != "human_vs_human":
            request["ai_config"] = ai_config

        return request

    @staticmethod
    def create_move_request(
        player_id: str = "player1", action: str = "e2e4"
    ) -> MoveRequestDict:
        """Create a move request object."""
        return {"player_id": player_id, "action": action}

    @staticmethod
    def create_move_response(
        player_id: str = "player1",
        action: str = "e2e4",
        move_number: int = 1,
        game_state: Optional[GameResponseDict] = None,
    ) -> MoveResponseDict:
        """Create a move response object."""
        if game_state is None:
            game_state = TestFixturesFactory.create_game_response(
                current_turn=2, move_count=move_number
            )

        return {
            "move": {
                "player_id": player_id,
                "action": action,
                "move_number": move_number,
                "timestamp": datetime.now().isoformat(),
            },
            "game_state": game_state,
        }

    @staticmethod
    def create_websocket_message(
        message_type: str,
        data: Optional[Dict[str, str]] = None,
        game_id: Optional[str] = None,
    ) -> WebSocketMessageDict:
        """Create a WebSocket message for testing."""
        message = WebSocketMessageDict(type=message_type)

        if game_id:
            message["game_id"] = game_id

        if data:
            # Convert to regular dict to allow arbitrary updates
            message_dict = dict(message)
            message_dict.update(data)
            # Construct WebSocketMessageDict with proper field assignment
            result = WebSocketMessageDict()
            # Only assign known fields to maintain type safety
            if "type" in message_dict and isinstance(message_dict["type"], str):
                result["type"] = message_dict["type"]
            if "game_id" in message_dict and isinstance(message_dict["game_id"], str):
                result["game_id"] = message_dict["game_id"]
            return result

        return message

    @staticmethod
    def create_error_response(
        error_code: int = 400,
        error_message: str = "Bad Request",
        details: Optional[str] = None,
    ) -> ErrorResponseDict:
        """Create an error response object."""
        response = ErrorResponseDict(error=error_message, code=error_code)

        if details:
            response["details"] = details

        return response

    @staticmethod
    def create_game_list_response(
        count: int = 3, status_filter: Optional[str] = None
    ) -> List[GameResponseDict]:
        """Create a list of games for testing list endpoints."""
        games = []
        statuses = (
            ["in_progress", "completed", "waiting"]
            if not status_filter
            else [status_filter]
        )

        for i in range(count):
            status = statuses[i % len(statuses)]
            game = TestFixturesFactory.create_game_response(
                game_id=f"game-{i+1}", status=status, move_count=i * 3
            )
            games.append(game)

        return games

    @staticmethod
    def create_legal_moves_response(
        moves: Optional[List[str]] = None,
    ) -> LegalMovesResponseDict:
        """Create a legal moves response."""
        if moves is None:
            moves = ["e2", "e4", "e6", "e8", "wall_h_3_4", "wall_v_2_3", "wall_h_5_6"]

        return {"legal_moves": moves}

    @staticmethod
    def create_frontend_game_settings(
        mode: str = "human_vs_ai",
        ai_difficulty: str = "medium",
        ai_time_limit: int = 5000,
        board_size: int = 9,
    ) -> FrontendGameSettingsDict:
        """Create frontend game settings object."""
        return {
            "mode": mode,
            "ai_difficulty": ai_difficulty,
            "ai_time_limit": ai_time_limit,
            "board_size": board_size,
            "player1_type": "human",
            "player2_type": "human" if mode == "human_vs_human" else "ai",
        }

    @staticmethod
    def create_websocket_service_mock() -> WebSocketServiceMockDict:
        """Create a complete WebSocket service mock for frontend tests."""
        return {
            "connect": lambda: None,
            "disconnect": lambda: None,
            "disconnectFromGame": lambda: None,
            "isConnected": lambda: True,
            "createGame": lambda settings: TestFixturesFactory.create_game_response(),
            "makeMove": lambda game_id, move: None,
            "getAIMove": lambda game_id: None,
            "joinGame": lambda game_id: None,
            "requestGameState": lambda game_id: TestFixturesFactory.create_game_response(
                game_id
            ),
            "connectToGame": lambda game_id: None,
        }

    @staticmethod
    def _create_board_display(size: int = 9) -> str:
        """Create a simple board display string for testing."""
        # Simple representation - in reality this would be more complex
        board = []
        for row in range(size):
            board_row = []
            for col in range(size):
                if row == 0 and col == size // 2:
                    board_row.append("1")  # Player 1 start
                elif row == size - 1 and col == size // 2:
                    board_row.append("2")  # Player 2 start
                else:
                    board_row.append(".")  # Empty
            board.append(" ".join(board_row))
        return "\n".join(board)


# Convenience functions for common test scenarios
def mock_successful_game_creation() -> GameResponseDict:
    """Quick mock for successful game creation."""
    return TestFixturesFactory.create_game_response()


def mock_game_in_progress() -> GameResponseDict:
    """Quick mock for game in progress."""
    return TestFixturesFactory.create_game_response(move_count=10, current_turn=2)


def mock_completed_game() -> GameResponseDict:
    """Quick mock for completed game."""
    return TestFixturesFactory.create_game_response(
        status="completed", winner="player1", move_count=25
    )


def mock_fetch_responses() -> (
    Dict[
        str,
        GameResponseDict
        | MoveResponseDict
        | LegalMovesResponseDict
        | List[GameResponseDict],
    ]
):
    """Create a set of mock fetch responses for frontend tests."""
    return {
        "POST /games": TestFixturesFactory.create_game_response(),
        "GET /games/test-game": TestFixturesFactory.create_game_response(
            game_id="test-game"
        ),
        "POST /games/test-game/moves": TestFixturesFactory.create_move_response(),
        "GET /games/test-game/legal-moves": TestFixturesFactory.create_legal_moves_response(),
        "GET /games": TestFixturesFactory.create_game_list_response(),
    }
