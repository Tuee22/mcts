"""
Sample game data for testing.
"""

from backend.api.models import GameSettings, MCTSSettings, PlayerType

# Common game configurations
FAST_GAME_SETTINGS = GameSettings(
    mcts_settings=MCTSSettings(
        c=0.158, min_simulations=50, max_simulations=50, use_rollout=True, seed=42
    )
)

STANDARD_GAME_SETTINGS = GameSettings(
    mcts_settings=MCTSSettings(
        c=1.4, min_simulations=1000, max_simulations=1000, use_rollout=True, seed=42
    )
)

PUCT_GAME_SETTINGS = GameSettings(
    mcts_settings=MCTSSettings(
        c=0.158,
        min_simulations=500,
        max_simulations=500,
        use_puct=True,
        use_probs=True,
        seed=42,
    )
)

# Sample move sequences
OPENING_MOVES = [
    "*(4,1)",  # Hero forward
    "*(4,7)",  # Villain forward
    "*(4,2)",  # Hero forward
    "*(4,6)",  # Villain forward
]

WALL_GAME_MOVES = [
    "*(4,1)",  # Hero forward
    "*(4,7)",  # Villain forward
    "H(4,1)",  # Hero places horizontal wall
    "V(3,6)",  # Villain places vertical wall
    "*(3,1)",  # Hero moves left
    "*(5,7)",  # Villain moves right
]

# Player configurations
HUMAN_PLAYERS = {
    "alice": {"name": "Alice", "type": PlayerType.HUMAN},
    "bob": {"name": "Bob", "type": PlayerType.HUMAN},
}

AI_PLAYERS = {
    "ai_easy": {"name": "Easy AI", "type": PlayerType.MACHINE},
    "ai_hard": {"name": "Hard AI", "type": PlayerType.MACHINE},
}
