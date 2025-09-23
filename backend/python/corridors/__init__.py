"""Corridors MCTS package."""

import os
import sys

# Add the build directory to Python path for the C++ extension
# In Docker container, build artifacts are in /opt/mcts/backend-build
# For local development, try the old location as fallback
build_paths = [
    "/opt/mcts/backend-build",  # Docker container location
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "build")
    ),  # Local development fallback
]

for build_dir in build_paths:
    if os.path.exists(build_dir) and build_dir not in sys.path:
        sys.path.insert(0, build_dir)
        break

# Import the C++ extension module directly
# This will fail fast if the .so is not available
import _corridors_mcts

# Import async Python wrapper after C++ extension is available
from corridors.async_mcts import (
    AsyncCorridorsMCTS,
    MCTSRegistry,
    ConcurrencyViolationError,
    MCTSConfig,
)

# Alias for backward compatibility
Corridors_MCTS = AsyncCorridorsMCTS


# Utility functions for backward compatibility
def display_sorted_actions(actions, list_size=None):
    """Format sorted actions for display."""
    limited_actions = actions[:list_size] if list_size is not None else actions
    return "\n".join(
        f"{action}: {visits} visits, {equity:.4f} equity"
        for visits, equity, action in limited_actions
    )


def computer_self_play(*args, **kwargs):
    """Stub function - computer_self_play was removed in async refactor."""
    raise NotImplementedError("computer_self_play was removed in async refactor")


__all__ = [
    "AsyncCorridorsMCTS",
    "MCTSRegistry",
    "ConcurrencyViolationError",
    "MCTSConfig",
    "_corridors_mcts",
    "Corridors_MCTS",
    "display_sorted_actions",
    "computer_self_play",
]
