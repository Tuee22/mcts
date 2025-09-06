"""Response models for API response validation in tests."""

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Union


@dataclass
class HealthResponse:
    """Health check response model."""

    status: Literal["healthy"]
    active_games: int
    connected_clients: int

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "HealthResponse":
        """Create instance from dictionary."""
        status: Literal["healthy"] = "healthy"
        active_games_val = data["active_games"]
        connected_clients_val = data["connected_clients"]
        assert isinstance(active_games_val, int)
        assert isinstance(connected_clients_val, int)
        return cls(
            status=status,
            active_games=active_games_val,
            connected_clients=connected_clients_val,
        )


@dataclass
class ErrorResponse:
    """Error response model."""

    detail: str

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "ErrorResponse":
        """Create instance from dictionary."""
        detail_val = data["detail"]
        assert isinstance(detail_val, str)
        return cls(detail=detail_val)


@dataclass
class PlayerInfo:
    """Player information model."""

    id: str
    name: str
    type: str

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "PlayerInfo":
        """Create instance from dictionary."""
        id_val = data["id"]
        name_val = data["name"]
        type_val = data["type"]
        assert isinstance(id_val, str)
        assert isinstance(name_val, str)
        assert isinstance(type_val, str)
        return cls(
            id=id_val,
            name=name_val,
            type=type_val,
        )


@dataclass
class GameResponse:
    """Game response model."""

    game_id: str
    status: str
    player1: PlayerInfo
    player2: PlayerInfo
    current_turn: int
    winner: Optional[int] = None
    move_count: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "GameResponse":
        """Create instance from dictionary."""
        player1_data = data["player1"]
        player2_data = data["player2"]
        assert isinstance(player1_data, dict)
        assert isinstance(player2_data, dict)

        game_id_val = data["game_id"]
        status_val = data["status"]
        current_turn_val = data["current_turn"]
        assert isinstance(game_id_val, str)
        assert isinstance(status_val, str)
        assert isinstance(current_turn_val, int)

        winner_val = data.get("winner")
        move_count_val = data.get("move_count")
        created_at_val = data.get("created_at")

        winner_final = None
        if winner_val is not None:
            assert isinstance(winner_val, int)
            winner_final = winner_val

        move_count_final = None
        if move_count_val is not None:
            assert isinstance(move_count_val, int)
            move_count_final = move_count_val

        created_at_final = None
        if created_at_val is not None:
            assert isinstance(created_at_val, str)
            created_at_final = created_at_val

        return cls(
            game_id=game_id_val,
            status=status_val,
            player1=PlayerInfo.from_dict(player1_data),
            player2=PlayerInfo.from_dict(player2_data),
            current_turn=current_turn_val,
            winner=winner_final,
            move_count=move_count_final,
            created_at=created_at_final,
        )


@dataclass
class GameListData:
    """Game list response data."""

    games: List[GameResponse]
    total: int

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "GameListData":
        """Create instance from dictionary."""
        games_data = data["games"]
        total_val = data["total"]
        assert isinstance(games_data, list)
        assert isinstance(total_val, int)

        return cls(
            games=[
                GameResponse.from_dict(game)
                for game in games_data
                if isinstance(game, dict)
            ],
            total=total_val,
        )


@dataclass
class GameListResponse:
    """Game list response wrapper."""

    games: List[GameResponse]
    total: int

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "GameListResponse":
        """Create instance from dictionary."""
        games_data = data["games"]
        total_val = data["total"]
        assert isinstance(games_data, list)
        assert isinstance(total_val, int)

        return cls(
            games=[
                GameResponse.from_dict(game)
                for game in games_data
                if isinstance(game, dict)
            ],
            total=total_val,
        )


@dataclass
class MoveResponseData:
    """Move response data."""

    game_id: str
    player_id: str
    action: str
    valid: bool
    game_over: bool
    winner: Optional[int] = None
    next_player_type: str = ""
    board_state: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "MoveResponseData":
        """Create instance from dictionary."""
        game_id_val = data["game_id"]
        player_id_val = data["player_id"]
        action_val = data["action"]
        valid_val = data["valid"]
        game_over_val = data["game_over"]
        assert isinstance(game_id_val, str)
        assert isinstance(player_id_val, str)
        assert isinstance(action_val, str)
        assert isinstance(valid_val, bool)
        assert isinstance(game_over_val, bool)

        winner_val = data.get("winner")
        next_player_type_val = data.get("next_player_type", "")
        board_state_val = data.get("board_state")

        winner_final = None
        if winner_val is not None:
            assert isinstance(winner_val, int)
            winner_final = winner_val

        board_state_final = None
        if board_state_val is not None:
            assert isinstance(board_state_val, str)
            board_state_final = board_state_val

        assert isinstance(next_player_type_val, str)

        return cls(
            game_id=game_id_val,
            player_id=player_id_val,
            action=action_val,
            valid=valid_val,
            game_over=game_over_val,
            winner=winner_final,
            next_player_type=next_player_type_val,
            board_state=board_state_final,
        )


@dataclass
class BoardStateResponse:
    """Board state response."""

    game_id: str
    board: str
    current_turn: int
    move_count: int

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "BoardStateResponse":
        """Create instance from dictionary."""
        game_id_val = data["game_id"]
        board_val = data["board"]
        current_turn_val = data["current_turn"]
        move_count_val = data["move_count"]
        assert isinstance(game_id_val, str)
        assert isinstance(board_val, str)
        assert isinstance(current_turn_val, int)
        assert isinstance(move_count_val, int)

        return cls(
            game_id=game_id_val,
            board=board_val,
            current_turn=current_turn_val,
            move_count=move_count_val,
        )


@dataclass
class LegalMovesResponse:
    """Legal moves response."""

    game_id: str
    current_player: int
    legal_moves: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "LegalMovesResponse":
        """Create instance from dictionary."""
        legal_moves_data = data["legal_moves"]
        assert isinstance(legal_moves_data, list)

        game_id_val = data["game_id"]
        current_player_val = data["current_player"]
        assert isinstance(game_id_val, str)
        assert isinstance(current_player_val, int)

        return cls(
            game_id=game_id_val,
            current_player=current_player_val,
            legal_moves=[str(move) for move in legal_moves_data],
        )


@dataclass
class WebSocketConnectMessage:
    """WebSocket connect message."""

    type: Literal["connect"]
    message: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "WebSocketConnectMessage":
        """Create instance from dictionary."""
        msg_type: Literal["connect"] = "connect"
        message_val = data.get("message")
        return cls(
            type=msg_type,
            message=str(message_val) if message_val is not None else None,
        )


@dataclass
class WebSocketPongMessage:
    """WebSocket pong message."""

    type: Literal["pong"]

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "WebSocketPongMessage":
        """Create instance from dictionary."""
        msg_type: Literal["pong"] = "pong"
        return cls(type=msg_type)


@dataclass
class WebSocketGameStateMessage:
    """WebSocket game state message."""

    type: Literal["game_state"]
    data: Dict[str, Union[str, int, bool]]

    @classmethod
    def from_dict(cls, data_dict: Dict[str, object]) -> "WebSocketGameStateMessage":
        """Create instance from dictionary."""
        data = data_dict["data"]
        assert isinstance(data, dict)

        msg_type: Literal["game_state"] = "game_state"
        return cls(
            type=msg_type,
            data={k: v for k, v in data.items() if isinstance(v, (str, int, bool))},
        )


@dataclass
class WebSocketGameCreatedMessage:
    """WebSocket game created message."""

    type: Literal["game_created"]
    data: Dict[str, Union[str, int, bool]]

    @classmethod
    def from_dict(cls, data_dict: Dict[str, object]) -> "WebSocketGameCreatedMessage":
        """Create instance from dictionary."""
        data = data_dict["data"]
        assert isinstance(data, dict)

        msg_type: Literal["game_created"] = "game_created"
        return cls(
            type=msg_type,
            data={k: v for k, v in data.items() if isinstance(v, (str, int, bool))},
        )


@dataclass
class WebSocketGameEndedMessage:
    """WebSocket game ended message."""

    type: Literal["game_ended"]
    data: Dict[str, Union[str, int, bool]]

    @classmethod
    def from_dict(cls, data_dict: Dict[str, object]) -> "WebSocketGameEndedMessage":
        """Create instance from dictionary."""
        data = data_dict["data"]
        assert isinstance(data, dict)

        msg_type: Literal["game_ended"] = "game_ended"
        return cls(
            type=msg_type,
            data={k: v for k, v in data.items() if isinstance(v, (str, int, bool))},
        )


# Union type for all possible WebSocket messages in tests
TestWebSocketMessage = Union[
    WebSocketConnectMessage,
    WebSocketPongMessage,
    WebSocketGameStateMessage,
    WebSocketGameCreatedMessage,
    WebSocketGameEndedMessage,
]


def parse_test_websocket_message(data: Dict[str, object]) -> TestWebSocketMessage:
    """Parse a test WebSocket message using the appropriate model based on type."""
    message_type = data.get("type")

    if message_type == "connect":
        return WebSocketConnectMessage.from_dict(data)
    elif message_type == "pong":
        return WebSocketPongMessage.from_dict(data)
    elif message_type == "game_state":
        return WebSocketGameStateMessage.from_dict(data)
    elif message_type == "game_created":
        return WebSocketGameCreatedMessage.from_dict(data)
    elif message_type == "game_ended":
        return WebSocketGameEndedMessage.from_dict(data)
    else:
        raise ValueError(f"Unknown message type: {message_type}")
