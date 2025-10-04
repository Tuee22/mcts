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

You may stage changes with `git add` but must stop before committing. Only create commits when the user explicitly asks with phrases like "commit this", "create a commit", or "git commit".

## **Build Artifacts Policy**

**ZERO TOLERANCE: Never commit or copy any build artifacts, lock files, or generated content into git.**

### Volume-Based Architecture
- **Build artifacts stay in Docker volumes**: `backend_build`, `frontend_build`
- **Host filesystem remains clean**: No `.so`, `build/`, or `node_modules/` on host
- **Hot reload via container**: `docker compose exec mcts poetry run backend-build`
- **Separation of concerns**: Source files (bind mount) vs artifacts (volumes)

### Excluded from Git and Docker Context
- **NO LOCK FILES**: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `poetry.lock`
- **NO BUILD OUTPUTS**: `build/`, `dist/`, `.next/`, `out/`, `node_modules/`, `*.so`
- **NO GENERATED FILES**: Coverage reports, logs, cache directories
- **VERSIONING STRATEGY**: All dependencies use `>=X.Y.Z <X+1.0.0` pattern to prevent breaking changes
- **CLEAN BUILDS**: Docker builds generate fresh lock files for deterministic, reproducible environments

## Project Overview

This is a Monte Carlo Tree Search (MCTS) implementation for the Corridors board game, featuring a high-performance C++ backend with Python bindings. The project combines advanced MCTS algorithms with efficient board representation and supports both traditional UCT and modern PUCT (Alpha-Zero style) formulations.

### Architecture

The project uses a **single-server architecture** where FastAPI serves both the API and frontend from port 8000. The Docker setup uses named volumes to preserve build artifacts while supporting bind mounts for live development.

## Development Commands

### Environment Setup
```bash
# Install dependencies with Poetry
poetry install --with dev

# Docker development (recommended)
cd docker

# CPU-only build
docker compose build    # Build images (includes frontend and C++ compilation)
docker compose up -d    # Run unified server on port 8000

# GPU build (AMD64 only, requires NVIDIA Docker)
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml build
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d

# Clean build (if needed)
docker compose down -v  # Remove named volumes
docker compose build --no-cache

# Managing build artifacts
docker compose exec mcts rm -rf /opt/mcts/frontend-build/build  # Force frontend rebuild
docker compose exec mcts rm -rf /opt/mcts/backend-build/*.so  # Force C++ rebuild  
docker compose restart mcts  # Restart to trigger rebuilds

# Hot reload (development)
docker compose exec mcts poetry run backend-build  # Rebuild C++ extension to volume
```

### Building C++ Components
**IMPORTANT: All backend builds MUST be run inside Docker containers using Poetry scripts**

```bash
# Backend build management (using Poetry scripts - recommended)
docker compose exec mcts poetry run backend-build      # Standard optimized build
docker compose exec mcts poetry run backend-debug      # Debug build with symbols
docker compose exec mcts poetry run backend-profile    # Profile build with gprof
docker compose exec mcts poetry run backend-sanitize   # Build with AddressSanitizer
docker compose exec mcts poetry run backend-test       # Build test executable
docker compose exec mcts poetry run backend-clean      # Clean build artifacts
docker compose exec mcts poetry run backend-rebuild    # Clean and rebuild

# Direct SCons commands (fallback, if needed)
cd backend/core
scons target=/opt/mcts/backend-build/_corridors_mcts   # Standard build
scons target=/opt/mcts/backend-build/_corridors_mcts debug=1    # Debug build
scons test=1            # Build test executable (local)
```

### Testing
**IMPORTANT: All tests MUST be run inside Docker containers**
**IMPORTANT: Integration tests require the unified server, which runs automatically on port 8000 in the Docker container and serves both API and frontend**
**CRITICAL: E2E tests MUST be run through Poetry commands to ensure all tests are discovered**

```bash
# Start Docker services first (this also starts the unified server on port 8000)
cd docker && docker compose up -d

# Run all tests (inside container) - recommended approach
docker compose exec mcts poetry run test-all

# E2E Tests - ALWAYS use Poetry commands (ensures complete test discovery)
docker compose exec mcts poetry run test-e2e           # Run all e2e tests
docker compose exec mcts poetry run test-e2e-validate  # Validate test discovery only
docker compose exec mcts poetry run test-e2e-list      # List all tests that will run
docker compose exec mcts poetry run test-e2e-full      # Run with pre-validation

# ❌ NEVER run e2e tests directly - may miss parametrized tests:
# docker compose exec mcts pytest tests/e2e/  # DO NOT USE - misses browser variants

# Run specific test categories (inside container)
docker compose exec mcts pytest -m "not slow"     # Exclude slow tests
docker compose exec mcts pytest -m "slow"        # Only slow tests  
docker compose exec mcts pytest -m "integration" # Integration tests
docker compose exec mcts pytest -m "python"     # Pure Python tests
docker compose exec mcts pytest -m "cpp"        # C++ binding tests
docker compose exec mcts pytest -m "performance" # Performance tests
docker compose exec mcts pytest -m "edge_cases"  # Edge case tests

# Benchmarking (inside container)
docker compose exec mcts pytest --benchmark-only # Run benchmarks

# Quick test subsets (useful during development)
docker compose exec mcts poetry run test-all --skip-e2e --skip-benchmarks  # Fast tests only
```

#### E2E Test Execution Notes
E2E tests are parametrized to run across 3 browsers (chromium, firefox, webkit). With ~111 test functions, this creates ~333 total test cases. The Poetry commands ensure:
- All browser variants are discovered and run
- Test count validation prevents missing tests
- Proper parallel execution settings
- Comprehensive reporting

#### Frontend Building
**CRITICAL: All frontend builds MUST output to `/opt/mcts/frontend-build/build` - NEVER to `frontend/build/`**

**Use Poetry commands for all frontend build operations:**

```bash
# Start Docker services first
cd docker && docker compose up -d

# Build frontend (RECOMMENDED - uses Poetry build manager)
docker compose exec mcts poetry run frontend-build                 # Production build
docker compose exec mcts poetry run frontend-build --dev           # Development build with source maps

# Validate build locations and diagnose issues
docker compose exec mcts poetry run frontend-build-check           # Check for incorrect build locations

# Clean up incorrect build locations
docker compose exec mcts poetry run frontend-build-clean           # Remove wrong build directories

# Serve built frontend for testing
docker compose exec mcts poetry run frontend-serve                 # Serve on port 3000
docker compose exec mcts poetry run frontend-serve --port 8080     # Serve on custom port

# FALLBACK: Direct npm build (not recommended)
docker compose exec mcts cd /opt/mcts/frontend-build && npm run build  # Uses BUILD_PATH from package.json
```

**Build Path Enforcement:**
- Poetry `frontend-build` command enforces `/opt/mcts/frontend-build/build` location
- Environment validation ensures Docker container and correct directories
- Automatic cleanup detection and warnings for wrong build locations  
- Backend serves from `/opt/mcts/frontend-build/build` (line 221 in server.py)
- `frontend/build/` is blocked by .gitignore as additional safety net
- Multiple layers: Poetry script validation + BUILD_PATH + .gitignore

#### Frontend Testing
**ZERO NPX POLICY**: All commands use direct package names or npm scripts - npx is completely prohibited
**NO JEST POLICY**: Vitest-only testing stack - Jest is completely prohibited

```bash
# Start Docker services first
cd docker && docker compose up -d

# Run frontend tests (inside container) - all commands use direct vitest
docker compose exec mcts cd /app/frontend && npm run test          # Interactive mode
docker compose exec mcts cd /app/frontend && npm run test:run      # Run once and exit
docker compose exec mcts cd /app/frontend && npm run test:ui       # Web UI interface
docker compose exec mcts cd /app/frontend && npm run test:coverage # With coverage report

# Alternative: Direct vitest commands (vitest installed globally in container)
docker compose exec mcts cd /app/frontend && vitest run           # Run once
docker compose exec mcts cd /app/frontend && vitest --ui          # Web UI
docker compose exec mcts cd /app/frontend && vitest --coverage    # Coverage
```

**Note on Test Execution:**
- The Docker container automatically starts the unified server on port 8000 (see Dockerfile CMD)
- This server serves both the API and frontend from a single port
- Integration tests connect to this running server on port 8000
- DO NOT create instruction files for test execution - run tests directly
- Agents should execute tests directly using Bash tool, not create documentation files

### Code Quality
**IMPORTANT: All quality commands MUST be run inside Docker containers**

```bash
# Start Docker services first
cd docker && docker compose up -d

# Format code (inside container) - includes .py and .pyi files in stubs/
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
- `corridors_api.h/.cpp`: Synchronous API wrapper for Python bindings
- `_corridors_mcts.cpp`: pybind11 bindings module

**Python Frontend (`backend/python/corridors/`)**
- `corridors_mcts.py`: Main Python interface with `Corridors_MCTS` class
- Provides high-level API for game play, self-play, and analysis

**Test Suite (`tests/backend/` and `tests/frontend/`)**
- Comprehensive pytest-based testing with fixtures for different MCTS configurations
- Performance benchmarks and integration tests for C++/Python interop

### Key Design Patterns

**Template-based MCTS**: The C++ MCTS implementation uses templates to work with any game that implements the required interface (legal moves, evaluation, terminal detection).

**Async Simulation**: The `AsyncCorridorsMCTS` wrapper runs MCTS simulations using asyncio ThreadPoolExecutor, providing cancellation support and proper async/await integration.

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

- C++ code requires pybind11 for Python bindings and C++11 support
- SCons build system supports multiple configurations (debug, profile, sanitize)
- Docker containers provide GCC-13, Python 3.12, and all required dependencies
- Poetry manages Python dependencies with strict version pinning for reproducibility

## Development Standards

This project enforces strict quality standards:

- **Formatting**: Black formatter with PEP 8 compliance
- **Type Safety**: MyPy strict mode with zero tolerance for Any, cast(), type: ignore
- **Testing**: Comprehensive pytest suite with 95%+ coverage
- **Build Validation**: Docker containers for consistent environments
- **Custom Type Stubs**: Project maintains custom stubs to eliminate Any usage

All quality checks should be run manually as needed:

```bash
# Format code (inside container)
docker compose exec mcts poetry run black .
docker compose exec mcts poetry run isort .

# Type checking (inside container)  
docker compose exec mcts poetry run mypy --strict .

# Run tests (inside container)
docker compose exec mcts poetry run pytest -q
```