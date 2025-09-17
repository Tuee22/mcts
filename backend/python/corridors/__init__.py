"""Corridors MCTS package."""

import os
import sys

# Import the C++ extension module first to avoid circular imports
try:
    from . import _corridors_mcts
except ImportError as e:
    # For development/debugging - show more helpful error
    # Look for the .so file in the new backend/build/ location
    package_dir = os.path.dirname(__file__)
    build_dir = os.path.join(package_dir, "..", "..", "build")
    build_dir = os.path.abspath(build_dir)

    so_file_old = os.path.join(package_dir, "_corridors_mcts.so")
    dylib_file_old = os.path.join(package_dir, "_corridors_mcts.dylib")
    so_file_new = os.path.join(build_dir, "_corridors_mcts.so")
    dylib_file_new = os.path.join(build_dir, "_corridors_mcts.dylib")

    # Add the build directory to Python path and try importing again
    if os.path.exists(so_file_new) or os.path.exists(dylib_file_new):
        if build_dir not in sys.path:
            sys.path.insert(0, build_dir)
        try:
            import _corridors_mcts
        except ImportError as e2:
            raise ImportError(f"C++ extension found at {so_file_new} but failed to import: {e2}")
    elif os.path.exists(so_file_old):
        raise ImportError(f"C++ extension found at old location {so_file_old} but failed to import: {e}")
    elif os.path.exists(dylib_file_old):
        raise ImportError(f"C++ extension found at old location {dylib_file_old} but failed to import: {e}")
    else:
        raise ImportError(f"C++ extension not found at {so_file_new} or {dylib_file_new}. Did you run 'scons' in backend/core/?")

# Import Python wrapper after C++ extension is available
from .corridors_mcts import Corridors_MCTS

__all__ = ["Corridors_MCTS", "_corridors_mcts"]
