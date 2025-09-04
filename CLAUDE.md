# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## **Environment Rules**

**CRITICAL: ALL shell commands MUST execute inside the Docker container, never on the host.**

- **Container**: All commands run in the `mcts` Docker service
- **Auto-start**: If the container is not running, it will be started automatically
- **Fail-closed**: Commands must never run on the host; if container is unavailable, execution fails with clear error
- **Workdir**: Container workdir `/app` maps to repository root and is volume-mounted for live development

## **Git Commit Policy**

**CRITICAL: Never make git commits automatically. All git commits must be explicitly requested by the user.**

This project uses the @no-git-commits agent policy. You may stage changes with `git add` but must stop before committing. Only create commits when the user explicitly asks with phrases like "commit this", "create a commit", or "git commit".

## Project Overview

This is a Monte Carlo Tree Search (MCTS) implementation for the Corridors board game, featuring a high-performance C++ backend with Python bindings. The project combines advanced MCTS algorithms with efficient board representation and supports both traditional UCT and modern PUCT (Alpha-Zero style) formulations.

## Development Commands

### Environment Setup
```bash
# Install dependencies with Poetry
poetry install --with dev

# Docker development (recommended)
cd docker

# CPU-only build
docker compose build    # Build images
docker compose up -d    # Run services

# GPU build (AMD64 only, requires NVIDIA Docker)
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml build
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d
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
**IMPORTANT: All tests MUST be run inside Docker containers**

```bash
# Start Docker services first
cd docker && docker compose up -d

# Run all tests (inside container)
docker compose exec mcts pytest

# Test categories (inside container)
docker compose exec mcts pytest -m "not slow"     # Exclude slow tests
docker compose exec mcts pytest -m "slow"        # Only slow tests  
docker compose exec mcts pytest -m "integration" # Integration tests
docker compose exec mcts pytest -m "python"     # Pure Python tests
docker compose exec mcts pytest -m "cpp"        # C++ binding tests
docker compose exec mcts pytest -m "performance" # Performance tests
docker compose exec mcts pytest -m "edge_cases"  # Edge case tests

# Benchmarking (inside container)
docker compose exec mcts pytest --benchmark-only # Run benchmarks
```

### Code Quality
**IMPORTANT: All quality commands MUST be run inside Docker containers**

```bash
# Start Docker services first
cd docker && docker compose up -d

# Format code (inside container)
docker compose exec mcts black .
docker compose exec mcts isort .

# Type checking (inside container)  
docker compose exec mcts mypy --strict .

# Alternative: Run all quality checks in one command
docker compose exec mcts bash -c "black . && isort . && mypy --strict ."
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

## Claude Code Integration

This repository uses Claude Code agents and automated quality assurance hooks for development.

### Claude Code Workflow

This repository uses a **loop-safe** quality gate workflow that runs **ONCE** when you finish implementing a feature.

#### How It Works

The workflow executes on the **Stop hook** (when Claude finishes responding) and runs:
**Black → mypy → tests**

#### Loop Prevention

- **First Stop run**: If any stage fails, the hook exits with code 2 (blocking) and feeds the error back to Claude for automatic fixing
- **Second Stop run** (continuation): If stages still fail, the hook exits with code 1 (non-blocking) to prevent infinite loops and requires manual intervention

#### Environment Detection

The orchestrator automatically:
- **Prefers Docker**: Runs commands inside the `mcts` Docker Compose service with `poetry run`
- **Falls back locally**: If Docker unavailable, runs equivalent local Poetry commands
- **Auto-starts services**: Starts the `mcts` container if not running

#### Manual Execution

Run the quality gate manually:
```bash
# Full quality gate
.claude/hooks/quality-gate-safe.py

# Individual stages
docker compose exec mcts poetry run black .
docker compose exec mcts poetry run mypy --strict .
docker compose exec mcts poetry run pytest -q
```

### Available Agents

#### Core Quality Assurance
- **@formatter-black**: Python code formatting with Black (PEP 8 compliance)
- **@mypy-type-checker**: Comprehensive type checking with zero tolerance policy
- **@builder-docker**: Docker container builds for development and CI
- **@tester-pytest**: Test suite execution and validation

#### Specialized Build Agents
- **@builder-cpu**: CPU-only Docker builds for development/CI
- **@builder-gpu**: GPU-enabled Docker builds (AMD64 only)
- **@no-git-commits**: Policy agent preventing automatic git commits

### Environment Configuration

Control the automated pipeline with environment variables:

```bash
export MCTS_FORMAT_CMD="docker compose exec mcts black ."
export MCTS_TYPECHECK_CMD="docker compose exec mcts mypy --strict ."
export MCTS_BUILD_CMD="docker compose build"
export MCTS_TEST_CMD="docker compose exec mcts pytest -q"
export MCTS_SKIP_BUILD="false"
export MCTS_SKIP_TESTS="false"
export MCTS_VERBOSE="true"
export MCTS_FAIL_FAST="true"
```

#### Configuration

**Default behavior**: Quality gate runs automatically on Stop hook.

**Override behavior**: Create `.claude/settings.local.json`:
```json
{
  "hooks": {
    "Stop": []
  }
}
```

**Test scope**: The orchestrator runs the full test suite by default. If Docker services unavailable, falls back to Python-only tests.

#### Troubleshooting

**Quality gate logs**: Check `.claude/logs/quality-gate-*.log` for detailed execution logs.

**Docker issues**: Ensure Docker is running and `mcts` service is available:
```bash
cd docker && docker compose up -d mcts
```

**Tool availability**: Black and mypy are managed by Poetry in the container.

#### Optional Test Guard

An optional test guard warns when modifying existing passing tests:

**Enable test guard**: Add to `.claude/settings.json` PreToolUse hooks:
```json
{
  "matcher": "Edit|Write", 
  "hooks": [{"type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/test-guard.py"}]
}
```

**Configure behavior**: In `.claude/settings.local.json`:
```json
{
  "test_guard": {
    "mode": "warn"  // or "block" to prevent modifications
  }
}
```

The guard allows new test creation and initial red/green cycles but warns about modifying tests that were previously passing in the same session.

### Development Workflow

1. **Implement features**: Write code and tests normally
2. **Automatic quality check**: Stop hook runs Black → mypy → tests once when you finish
3. **Fix issues**: On failures, Claude automatically fixes and re-runs the sequence
4. **Manual intervention**: If issues persist after one fix cycle, use suggested agents

### Agent Documentation

- **Agent Registry**: `.claude/AGENTS.md` - Complete agent documentation
- **Machine-Readable**: `.claude/agents.json` - Programmatic agent definitions
- **Hook Configuration**: `.claude/settings.json` - Pipeline settings

### Quality Standards

This project enforces strict quality standards:

- **Formatting**: Black formatter with PEP 8 compliance
- **Type Safety**: MyPy strict mode with zero tolerance for Any, cast(), type: ignore
- **Testing**: Comprehensive pytest suite with 95%+ coverage
- **Build Validation**: Docker containers for consistent environments
- **Custom Type Stubs**: Project maintains custom stubs to eliminate Any usage

The automated pipeline ensures all contributions meet these standards before integration.