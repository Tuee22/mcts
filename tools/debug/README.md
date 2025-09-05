# Debug Scripts

This directory contains debugging scripts used during development to isolate and fix issues in the MCTS implementation.

## Scripts Overview

- **`debug_terminal.py`** - Debug terminal (game-end) detection issues
- **`debug_board_state.py`** - Debug board state after wall placements  
- **`debug_visits.py`** - Debug visit counting in MCTS tree
- **`debug_evaluation.py`** - Debug position evaluation logic
- **`debug_cpp_terminal.py`** - Debug C++ terminal detection specifically
- **`debug_actions_after_move.py`** - Debug legal moves after specific moves
- **`debug_no_flip.py`** - Debug board orientation/flipping issues
- **`debug_positional_only.py`** - Debug position-specific game logic
- **`debug_root_visits.py`** - Debug root node visit counts
- **`debug_deep_terminal.py`** - Debug deep game tree terminal states

## Usage

These scripts can be run independently to reproduce specific debugging scenarios:

```bash
# Run debug scripts directly (Poetry shortcuts are disabled)
poetry run python tools/debug/debug_terminal.py
poetry run python tools/debug/debug_board_state.py
poetry run python tools/debug/debug_evaluation.py
poetry run python tools/debug/debug_visits.py
poetry run python tools/debug/debug_cpp_terminal.py
# etc.

# Or run in Docker container:
docker compose exec mcts poetry run python tools/debug/debug_terminal.py
```

## Purpose

These scripts were created to isolate specific bugs and edge cases during MCTS development, particularly around:

- Game termination detection
- Board state consistency
- MCTS tree visit count accuracy
- Move validation edge cases
- Position evaluation correctness

They serve as both debugging tools and regression test cases for complex scenarios that might not be easily covered in the main test suite.