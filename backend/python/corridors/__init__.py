"""Corridors MCTS package."""

# Import the C++ extension module first to avoid circular imports
try:
    from . import _corridors_mcts
except ImportError as e:
    # For development/debugging - show more helpful error
    import os
    base_dir = os.path.dirname(__file__)
    so_file = os.path.join(base_dir, "_corridors_mcts.so")
    dylib_file = os.path.join(base_dir, "_corridors_mcts.dylib")
    
    # Check for platform-specific library files
    if os.path.exists(so_file):
        raise ImportError(f"C++ extension found at {so_file} but failed to import: {e}")
    elif os.path.exists(dylib_file):
        raise ImportError(f"C++ extension found at {dylib_file} but failed to import: {e}")
    else:
        raise ImportError(f"C++ extension not found at {so_file} or {dylib_file}. Did you run 'scons' in backend/core/?")

# Import Python wrapper after C++ extension is available
from .corridors_mcts import Corridors_MCTS

__all__ = ["Corridors_MCTS", "_corridors_mcts"]
