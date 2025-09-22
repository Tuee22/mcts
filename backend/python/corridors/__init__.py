"""Corridors MCTS package."""

import os
import sys

# Add the build directory to Python path for the C++ extension
package_dir = os.path.dirname(__file__)
build_dir = os.path.join(package_dir, "..", "..", "build")
build_dir = os.path.abspath(build_dir)

if build_dir not in sys.path:
    sys.path.insert(0, build_dir)

# Import the C++ extension module directly
# This will fail fast if the .so is not available
import _corridors_mcts

# Import async Python wrapper after C++ extension is available
from corridors.async_mcts import (
    AsyncCorridorsMCTS,
    MCTSRegistry,
    ConcurrencyViolationError,
)

__all__ = [
    "AsyncCorridorsMCTS",
    "MCTSRegistry",
    "ConcurrencyViolationError",
    "_corridors_mcts",
]
