"""Type definitions for the API module."""

from typing import (
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Tuple,
    Union,
    runtime_checkable,
)

from typing_extensions import TypedDict

# Import discriminated union types for state management
from .state_types import (
    ConnectionState,
    GameSession,
    AppState,
    StateAction,
    is_connected,
    is_game_active,
    can_start_game,
    can_make_move,
)


@runtime_checkable
class WebSocketProtocol(Protocol):
    """Protocol for WebSocket interface."""

    client_state: int  # FastAPI WebSocket state

    async def accept(self) -> None:
        ...

    async def close(self, code: int = 1000) -> None:
        ...

    async def send_text(self, data: str) -> None:
        ...

    async def send_json(self, data: object) -> None:
        ...

    async def receive_text(self) -> str:
        ...

    async def receive_json(self) -> object:
        ...


# WebSocket message types
class MoveData(TypedDict):
    """Data for a move."""

    player_id: str
    action: str
    move_number: int
    evaluation: Optional[float]
    timestamp: str


class MoveMessageData(TypedDict):
    """Data for move message."""

    game_id: str
    move: MoveData
    game_status: str
    next_turn: int
    board_display: Optional[str]  # Can be None
    winner: Optional[int]


class GameStateData(TypedDict):
    """Data for game state message."""

    game_id: str
    board_display: Optional[str]  # Can be None
    legal_moves: List[str]
    status: str  # From game_response.status
    player1_id: str
    player2_id: str
    current_turn: int
    winner: Optional[int]
    created_at: str


class GameEndedData(TypedDict):
    """Data for game ended message."""

    game_id: str
    winner: Optional[int]
    game_status: str


class GameCreatedData(TypedDict):
    """Data for game created message."""

    game_id: str


class OutgoingWebSocketMessage(TypedDict):
    """Base outgoing WebSocket message."""

    type: str
    data: Union[
        MoveMessageData,
        GameStateData,
        GameEndedData,
        GameCreatedData,
        Dict[str, Union[str, int, bool, List[str], Optional[int]]],
    ]


class PlayerConnectedMessage(OutgoingWebSocketMessage):
    """Player connected message."""

    pass


class PlayerDisconnectedMessage(OutgoingWebSocketMessage):
    """Player disconnected message."""

    pass


class GameStateMessage(OutgoingWebSocketMessage):
    """Game state message."""

    pass


class MoveBroadcastMessage(OutgoingWebSocketMessage):
    """Move broadcast message."""

    pass


class GameEndedMessage(OutgoingWebSocketMessage):
    """Game ended message."""

    pass


class GameCreatedMessage(OutgoingWebSocketMessage):
    """Game created message."""

    pass
