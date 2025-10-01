"""Discriminated union types for API state management.

These types ensure 1:1 correspondence with frontend state types,
making illegal states unrepresentable at the type level.
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional, Union
from typing_extensions import TypedDict


# Type definitions for game state representation
class Position(TypedDict):
    """Position on the game board."""

    x: int
    y: int


class Wall(TypedDict):
    """Wall placement on the game board."""

    x: int
    y: int
    orientation: Literal["horizontal", "vertical"]


class Move(TypedDict):
    """Game move representation."""

    notation: str
    player: int
    type: Literal["move", "wall"]
    position: Optional[Position]
    wall: Optional[Wall]


class GameStateDict(TypedDict):
    """Game state representation matching frontend GameState."""

    board_size: int
    current_player: int
    players: List[Position]
    walls: List[Wall]
    walls_remaining: List[int]  # [player1_walls, player2_walls]
    legal_moves: List[str]
    winner: Optional[int]
    move_history: List[Move]


class GameSettingsDict(TypedDict):
    """Game settings representation matching frontend GameSettings."""

    mode: str
    ai_difficulty: str
    ai_time_limit: int
    board_size: int


# Connection state discriminated unions
class DisconnectedState(TypedDict):
    """Connection state when disconnected."""

    type: Literal["disconnected"]
    error: Optional[str]
    can_reset: Literal[True]


class ConnectingState(TypedDict):
    """Connection state when attempting to connect."""

    type: Literal["connecting"]
    attempt_number: int
    can_reset: Literal[False]


class ConnectedState(TypedDict):
    """Connection state when successfully connected."""

    type: Literal["connected"]
    client_id: str
    since: str  # ISO timestamp
    can_reset: Literal[True]


class ReconnectingState(TypedDict):
    """Connection state when attempting to reconnect."""

    type: Literal["reconnecting"]
    last_client_id: str
    attempt_number: int
    can_reset: Literal[False]


ConnectionState = Union[
    DisconnectedState,
    ConnectingState,
    ConnectedState,
    ReconnectingState,
]


# Game session discriminated unions - simplified to match frontend
class NoGameSession(TypedDict):
    """Session state when no game is active."""

    type: Literal["no-game"]


class ActiveGameSession(TypedDict):
    """Session state when game is active."""

    type: Literal["active-game"]
    game_id: str
    state: GameStateDict
    last_sync: str  # ISO timestamp


class GameOverSession(TypedDict):
    """Session state when game has ended."""

    type: Literal["game-over"]
    game_id: str
    state: GameStateDict
    winner: int  # Player index (0 or 1)


GameSession = Union[
    NoGameSession,
    ActiveGameSession,
    GameOverSession,
]


# Notification types
class Notification(TypedDict):
    """UI notification."""

    id: str
    type: Literal["info", "success", "warning", "error"]
    message: str
    timestamp: str  # ISO timestamp


# Settings types
class GameSettings(TypedDict):
    """Game configuration settings."""

    mode: Literal["human_vs_ai", "human_vs_human", "ai_vs_ai"]
    ai_difficulty: Literal["easy", "medium", "hard"]
    ai_time_limit: int
    board_size: int


class PersistedSettings(TypedDict):
    """Settings that persist across sessions."""

    game_settings: GameSettings
    theme: Literal["light", "dark"]
    sound_enabled: bool


class UIState(TypedDict):
    """Transient UI state."""

    settings_expanded: bool
    selected_history_index: Optional[int]
    notifications: List[Notification]


# Combined app state
class AppState(TypedDict):
    """Complete application state."""

    connection: ConnectionState
    session: GameSession
    settings: PersistedSettings
    ui: UIState


# Action types for state transitions
class ConnectionStartAction(TypedDict):
    """Start connection attempt."""

    type: Literal["CONNECTION_START"]


class ConnectionEstablishedAction(TypedDict):
    """Connection successfully established."""

    type: Literal["CONNECTION_ESTABLISHED"]
    client_id: str


class ConnectionLostAction(TypedDict):
    """Connection lost."""

    type: Literal["CONNECTION_LOST"]
    error: Optional[str]


class ConnectionRetryAction(TypedDict):
    """Retry connection."""

    type: Literal["CONNECTION_RETRY"]


class GameCreatedAction(TypedDict):
    """Game successfully created."""

    type: Literal["GAME_CREATED"]
    game_id: str
    state: GameStateDict


class GameCreateFailedAction(TypedDict):
    """Game creation failed."""

    type: Literal["GAME_CREATE_FAILED"]
    error: str


class NewGameRequestedAction(TypedDict):
    """New game requested - direct transition to no-game state."""

    type: Literal["NEW_GAME_REQUESTED"]


class GameStateUpdatedAction(TypedDict):
    """Game state updated."""

    type: Literal["GAME_STATE_UPDATED"]
    state: GameStateDict


class ResetGameAction(TypedDict):
    """Reset game state."""

    type: Literal["RESET_GAME"]


class SettingsToggledAction(TypedDict):
    """Toggle settings panel."""

    type: Literal["SETTINGS_TOGGLED"]


class SettingsUpdatedAction(TypedDict):
    """Update game settings."""

    type: Literal["SETTINGS_UPDATED"]
    settings: GameSettingsDict


class ThemeChangedAction(TypedDict):
    """Change UI theme."""

    type: Literal["THEME_CHANGED"]
    theme: Literal["light", "dark"]


class SoundToggledAction(TypedDict):
    """Toggle sound effects."""

    type: Literal["SOUND_TOGGLED"]


class HistoryIndexSetAction(TypedDict):
    """Set history navigation index."""

    type: Literal["HISTORY_INDEX_SET"]
    index: Optional[int]


class NotificationAddedAction(TypedDict):
    """Add notification."""

    type: Literal["NOTIFICATION_ADDED"]
    notification: Notification


class NotificationRemovedAction(TypedDict):
    """Remove notification."""

    type: Literal["NOTIFICATION_REMOVED"]
    id: str


class MoveMadeAction(TypedDict):
    """Player made a move."""

    type: Literal["MOVE_MADE"]
    move: Move


class MoveFailedAction(TypedDict):
    """Move attempt failed."""

    type: Literal["MOVE_FAILED"]
    error: str


StateAction = Union[
    ConnectionStartAction,
    ConnectionEstablishedAction,
    ConnectionLostAction,
    ConnectionRetryAction,
    GameCreatedAction,
    GameCreateFailedAction,
    NewGameRequestedAction,
    GameStateUpdatedAction,
    ResetGameAction,
    SettingsToggledAction,
    SettingsUpdatedAction,
    ThemeChangedAction,
    SoundToggledAction,
    HistoryIndexSetAction,
    NotificationAddedAction,
    NotificationRemovedAction,
    MoveMadeAction,
    MoveFailedAction,
]


def is_connected(state: ConnectionState) -> bool:
    """Type guard to check if connection is established."""
    return state["type"] == "connected"


def can_reset(state: ConnectionState) -> bool:
    """Check if reset operation is allowed in this connection state."""
    return state["can_reset"]


def is_game_active(session: GameSession) -> bool:
    """Type guard to check if game is active."""
    return session["type"] == "active-game"


def can_start_game(state: AppState) -> bool:
    """Check if a new game can be started."""
    return is_connected(state["connection"]) and state["session"]["type"] == "no-game"


def can_make_move(state: AppState) -> bool:
    """Check if a move can be made."""
    if not is_connected(state["connection"]) or not is_game_active(state["session"]):
        return False

    # Type narrowing: after is_game_active check, we know session is ActiveGameSession
    session = state["session"]
    if session["type"] == "active-game":
        return session["state"]["winner"] is None

    return False
