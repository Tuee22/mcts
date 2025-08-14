# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Monte Carlo Tree Search (MCTS) implementation for the Corridors board game, featuring a high-performance C++ backend with Python bindings. The project combines advanced MCTS algorithms with efficient board representation and supports both traditional UCT and modern PUCT (Alpha-Zero style) formulations.

## Development Commands

### Environment Setup
```bash
# Install dependencies with Poetry
poetry install --with dev

# Docker development (recommended)
cd docker
TARGET=cpu docker compose up -d  # For CPU-only build
TARGET=cuda docker compose up -d # For GPU-enabled build (AMD64 only)
```

### Building C++ Components
```bash
# Build C++ shared library
cd backend/core
scons                    # Standard build
scons debug=1           # Debug build with symbols
scons test=1            # Build test executable
scons profile=1         # Profile build with gprof
scons sanitize=1        # Build with AddressSanitizer
```

### Testing
```bash
# Run all tests
poetry run test
# or
pytest

# Test categories
poetry run test-fast      # Exclude slow tests
poetry run test-slow      # Only slow tests  
poetry run test-integration # Integration tests
poetry run test-python    # Pure Python tests
poetry run test-cpp       # C++ binding tests
poetry run test-performance # Performance tests
poetry run test-edge-cases # Edge case tests

# Benchmarking
poetry run benchmark        # Run benchmarks
poetry run benchmark-compare # Compare benchmark results
```

### Code Quality
```bash
# Format code
poetry run format       # Format with black + isort
poetry run lint         # Format check only
poetry run lint-check   # Check formatting without changes

# Type checking  
poetry run typecheck    # Run mypy on backend/ and tests/
```

## Architecture

### Core Components

**C++ Backend (`backend/core/`)**
- `mcts.hpp`: Generic MCTS template implementation with UCT/PUCT support
- `board.h/.cpp`: Corridors game board representation and logic
- `corridors_threaded_api.h/.cpp`: Thread-safe API wrapper for Python bindings
- `_corridors_mcts.cpp`: Boost.Python bindings module

**Python Frontend (`backend/python/corridors/`)**
- `corridors_mcts.py`: Main Python interface with `Corridors_MCTS` class
- Provides high-level API for game play, self-play, and analysis

**Test Suite (`tests/backend/` and `tests/frontend/`)**
- Comprehensive pytest-based testing with fixtures for different MCTS configurations
- Performance benchmarks and integration tests for C++/Python interop

### Key Design Patterns

**Template-based MCTS**: The C++ MCTS implementation uses templates to work with any game that implements the required interface (legal moves, evaluation, terminal detection).

**Threaded Simulation**: The `corridors_threaded_api` runs MCTS simulations continuously in background threads, allowing real-time interaction.

**Hybrid Build System**: Uses SCons for C++ compilation and Poetry for Python dependency management. Docker provides consistent cross-platform environments.

## MCTS Configuration

The system supports extensive MCTS customization:

- **Traditional UCT**: Classic Upper Confidence Bound formula
- **PUCT**: Alpha-Zero style polynomial UCT with action probabilities  
- **Rollout vs Evaluation**: Random rollouts or domain-specific heuristic evaluation
- **Child Evaluation**: Option to evaluate all children immediately upon node expansion
- **Visit vs Equity Selection**: Choose best moves by visit count or average reward

## Game Interface Requirements

For any game to work with the MCTS template, it must implement:
- `get_legal_moves()` - Generate all legal moves from current position
- `is_terminal()` - Check if game has ended
- `get_terminal_eval()` - Return final game value
- `check_non_terminal_eval()` - Check for heuristic evaluation
- `get_action_text()` - Convert move to human-readable string

## Build Notes

- C++ code requires Boost libraries (python, numpy) and C++11 support
- SCons build system supports multiple configurations (debug, profile, sanitize)
- Docker containers provide GCC-13, Python 3.12, and all required dependencies
- Poetry manages Python dependencies with strict version pinning for reproducibility