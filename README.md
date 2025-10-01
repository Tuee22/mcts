# MCTS Corridors

A high-performance Monte Carlo Tree Search (MCTS) implementation for the Corridors board game, featuring a C++ backend with Python bindings and support for both traditional UCT and modern PUCT (AlphaZero-style) algorithms.


## Features

- **High-Performance C++ Core**: Template-based MCTS implementation with optimized board representation
- **Python Interface**: Easy-to-use Python API with threading support for real-time interaction  
- **Multiple MCTS Variants**: Support for traditional UCT, PUCT, rollouts vs heuristic evaluation
- **Comprehensive Testing**: Extensive test suite with performance benchmarks
- **Docker Support**: Cross-platform development with CPU and GPU configurations
- **Interactive Play**: Human vs computer and computer self-play modes

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker and Docker Compose
- For GPU support: NVIDIA Docker runtime
- Git

### Quick Start Instructions

```bash
git clone <repository-url>
cd mcts/docker
```

**For CPU systems (AMD64 or ARM64/Apple Silicon):**
```bash
docker compose up -d
docker compose exec mcts poetry run pytest -q
```

**For NVIDIA GPU systems (AMD64 only):**
```bash
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d
docker compose exec mcts nvidia-smi
docker compose exec mcts poetry run pytest -q
```

### Docker Configuration

The build system supports two configurations:

**CPU Build (`docker-compose.yaml`):**
- Multi-arch support (AMD64/ARM64)
- Uses Ubuntu 22.04 base image
- Command: `docker compose up -d`

**GPU Build (`docker-compose.yaml` + `docker-compose.gpu.yaml`):**
- AMD64 only with NVIDIA GPU support
- Uses NVIDIA CUDA 12.6.2 base image  
- Command: `docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d`

**Architecture Detection:**
```bash
# Verify which image you're using
docker compose exec mcts cat /etc/os-release | head -2

# Check for CUDA (GPU builds only)
docker compose exec mcts nvcc --version
```

Note: The development environment automatically rebuilds the C++ extension on container start to ensure compatibility with the runtime architecture.

### Verifying C++ Extension Build

The Docker image includes pre-built C++ extensions. To verify the build succeeded:

```bash
# Test without bind mounts (uses only artifacts baked into image)
docker run --rm mcts:cpu python -c "from corridors import _corridors_mcts; print('Extension loaded:', _corridors_mcts.__file__)"
# Expected output: Extension loaded: /app/backend/build/_corridors_mcts.so

# With docker compose (includes bind mounts and volumes)
docker compose exec mcts python -c "from corridors import _corridors_mcts; print('Extension loaded:', _corridors_mcts.__file__)"
```

### Build Architecture

The Docker setup uses a clean separation between source files and build artifacts:

- **Source files**: Bind mounted from host to `/app/` for live development
- **Build artifacts**: Stored in named Docker volumes, never on host filesystem
  - `backend_build` volume: C++ extension (`_corridors_mcts.so`)
  - `frontend_build` volume: React production build

This architecture ensures:
- No build artifacts contaminate the host filesystem
- Hot reload works via `docker compose exec mcts scons` (updates volume)
- Container comes pre-built with all necessary binaries
- Clean git repository (artifacts excluded via `.dockerignore` and `.gitignore`)

### Running Tests

**All unit tests:**
```bash
docker compose exec mcts poetry run pytest tests/backend/core/ -v
```

**Quick test run:**
```bash
docker compose exec mcts poetry run pytest -q
```

**E2E tests (browser-based):**
```bash
docker compose exec mcts bash -c "cd tests/e2e && pytest -m e2e"
```

**GPU verification (CUDA only):**
```bash
docker compose exec mcts nvidia-smi
```

### Access the Environment

Once the container is running:

```bash
# Access the container shell
docker compose exec mcts bash

# Run interactive Python session
docker compose exec mcts python

# Check container logs
docker compose logs mcts
```

The project directory is mounted for live development.


## Usage Examples

### Basic MCTS Game

```python
from corridors.corridors_mcts import Corridors_MCTS
from math import sqrt

# Create MCTS instance
mcts = Corridors_MCTS(
    c=sqrt(2),              # Exploration parameter
    seed=42,                # Random seed
    min_simulations=1000,   # Minimum simulations before move
    max_simulations=10000,  # Maximum simulations
    use_rollout=True        # Use random rollouts for evaluation
)

# Let MCTS think
mcts.ensure_sims(1000)

# Get best moves
actions = mcts.get_sorted_actions()
print(f"Best move: {actions[0][2]} (visits: {actions[0][0]}, equity: {actions[0][1]:.3f})")

# Make a move
mcts.make_move(actions[0][2])

# Display board
print(mcts.display())
```

### Interactive Play

```python
from corridors.corridors_mcts import Corridors_MCTS, human_computer_play

# Start human vs computer game
mcts = Corridors_MCTS(min_simulations=5000)
human_computer_play(mcts, human_plays_first=True)
```

### Computer Self-Play

```python
from corridors.corridors_mcts import Corridors_MCTS, computer_self_play

# Create two MCTS instances
p1 = Corridors_MCTS(seed=1, min_simulations=2000)
p2 = Corridors_MCTS(seed=2, min_simulations=2000)

# Run self-play game
computer_self_play(p1, p2, stop_on_eval=True)
```

### PUCT Configuration (AlphaZero-style)

```python
mcts_puct = Corridors_MCTS(
    c=sqrt(0.025),          # Lower exploration for PUCT
    use_puct=True,          # Use PUCT formula
    use_rollout=False,      # Use heuristic evaluation
    eval_children=True,     # Evaluate all children immediately
    decide_using_visits=False  # Choose moves by equity, not visits
)
```

## Frontend Integration

The project includes a React TypeScript frontend that provides a visual game interface with real-time multiplayer support.

### Quick Start

```bash
# Start full stack (backend + frontend)
cd docker
docker compose up -d

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000  
# WebSocket: ws://localhost:8000/ws
```

### Key Integration Points

**WebSocket Communication:**
- Real-time game updates and move synchronization
- Connection management with automatic reconnection
- Game event broadcasting (start, moves, end)

**REST API Integration:**
- `POST /games` - Create new games
- `GET /games/{id}` - Get game state  
- `POST /games/{id}/moves` - Submit moves
- `GET /health` - Backend status

**CORS Configuration:**
- Development: `http://localhost:3000`
- Testing: `http://localhost:3001`, `http://localhost:3002`
- Production: Configurable via `MCTS_CORS_ORIGINS`

**Environment Variables:**
```bash
# Frontend configuration
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws

# Backend CORS setup
MCTS_CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

For detailed frontend documentation, see [frontend/README.md](frontend/README.md).

## Development

### Building C++ Components

**Note**: When using Docker, build artifacts are stored in the `backend_build` volume at `/app/backend/build/`. The host filesystem remains clean of all build artifacts.

For hot reload during development:
```bash
docker compose exec mcts cd /app/backend/core && scons
```

For local development (without Docker):
```bash
cd backend/core

# Standard build
scons

# Debug build (with symbols)
scons debug=1

# Test build (creates executable)
scons test=1

# Profile build (with gprof support)
scons profile=1

# Sanitized build (AddressSanitizer)
scons sanitize=1
```

The C++ extension (`_corridors_mcts.so`) is built to `backend/build/` directory.

### Running Tests

**🎯 Complete Test Suite**: Run all tests (Python → Frontend → E2E) with individual runners or one unified command that ensures services are properly started and tests run across Chromium, Firefox, and WebKit browsers.

**IMPORTANT: All tests must be run inside Docker containers**

**Quick Start - Complete Test Suite:**
```bash
# Start Docker services first
cd docker && docker compose up -d

# Run ALL tests (Python + Frontend + E2E across all browsers)
docker compose exec mcts poetry run test-all

# Run only E2E tests across all browsers
docker compose exec mcts poetry run test-e2e

# Run specific test categories
docker compose exec mcts poetry run test-python    # Python tests only
docker compose exec mcts poetry run test-frontend  # Frontend tests only
```

**Docker Test Commands (Detailed):**
```bash
# Test categories
docker compose exec mcts pytest -m "not slow"     # Exclude slow tests
docker compose exec mcts pytest -m "slow"        # Only slow tests  
docker compose exec mcts pytest -m "integration" # Integration tests
docker compose exec mcts pytest -m "python"     # Pure Python tests
docker compose exec mcts pytest -m "cpp"        # C++ binding tests
docker compose exec mcts pytest -m "performance" # Performance tests
docker compose exec mcts pytest -m "edge_cases"  # Edge case tests
docker compose exec mcts pytest -m "e2e"         # End-to-end browser tests

# Benchmarking
docker compose exec mcts pytest --benchmark-only # Run benchmarks
```

**Advanced Testing Options:**
```bash
# With coverage and verbose output
docker compose exec mcts pytest --cov=corridors -v

# Specific test files
docker compose exec mcts pytest tests/backend/core/test_board.py       # Board functionality
docker compose exec mcts pytest tests/backend/core/test_mcts.py        # MCTS algorithm
docker compose exec mcts pytest tests/backend/api/test_server.py       # API endpoints

# Specific test directories
docker compose exec mcts pytest tests/backend/core/     # Core tests
docker compose exec mcts pytest tests/backend/api/      # API tests
docker compose exec mcts pytest tests/integration/      # Integration tests
docker compose exec mcts pytest tests/e2e/              # E2E tests
```

**E2E Browser Testing:**
```bash
# Run E2E tests with visible browser (debugging)
docker compose exec mcts poetry run test-e2e --headed

# E2E with debug mode
docker compose exec mcts poetry run test-e2e --debug

# E2E with verbose output
docker compose exec mcts poetry run test-e2e --verbose

# Direct pytest for advanced options
docker compose exec mcts pytest tests/e2e/test_browser_compatibility.py -v
```

**Note**: E2E tests automatically run across all browsers (Chromium, Firefox, WebKit) in each test method for comprehensive compatibility testing.

**Note**: Playwright and all three browsers (Chromium, Firefox, WebKit) are pre-installed in the Docker image with all required system libraries and fonts.

**Docker Runtime Flags for Browser Reliability:**
When running the container directly (not using docker compose), use these flags for improved browser stability:
```bash
docker run --init --ipc=host mcts:cpu poetry run test --e2e-only
```

**GPU Testing (CUDA only):**
```bash
# With GPU verification
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml exec mcts poetry run test-all
docker compose exec mcts nvidia-smi
```

### Poetry Scripts

The project provides convenient Poetry script shortcuts for common development tasks:

**API Server:**
```bash
# Start production API server
docker compose exec mcts poetry run api-server

# Start development API server (with hot reload)
docker compose exec mcts poetry run api-dev
```

**Testing Scripts:**
```bash
# Complete test suite - runs ALL tests (Python + Frontend + E2E)
docker compose exec mcts poetry run test-all

# Individual test runners
docker compose exec mcts poetry run test-python      # All Python tests
docker compose exec mcts poetry run test-frontend    # Frontend tests only
docker compose exec mcts poetry run test-e2e         # E2E tests across all browsers

# Test runner options
docker compose exec mcts poetry run test-all --skip-e2e  # Python + Frontend only
docker compose exec mcts poetry run test-e2e --headed    # E2E with visible browser
docker compose exec mcts poetry run test-e2e --debug     # E2E with debug output
```

**Code Quality:**
```bash
# Type safety verification (no Any, cast, or type: ignore)
docker compose exec mcts poetry run check-type-safety
```

These scripts are defined in `pyproject.toml` and provide a consistent interface for development tasks.

### Local Development Without Docker

If you need to run tests locally without Docker:

**Prerequisites:**
- Python 3.12+
- Node.js 20+
- Poetry
- C++ compiler (GCC or Clang)

**One-time setup:**
```bash
# Install Python dependencies
poetry install --with dev

# Install Playwright browsers (required for E2E tests)
playwright install chromium firefox webkit

# Build C++ extension
cd backend/core && scons && cd ../..

# Install frontend dependencies
cd frontend && npm install && cd ..
```

**Running tests locally:**
```bash
# All tests including E2E
poetry run test-all

# Individual test categories
poetry run test-python    # Python tests only
poetry run test-frontend   # Frontend tests only
poetry run test-e2e        # E2E tests only
```

**Note:** Docker is the recommended environment as it ensures all dependencies and browsers are correctly installed.

### Code Quality

This project enforces strict type safety with zero tolerance for `Any`, `cast`, or `type: ignore`.

```bash
# Format code
poetry run black . && poetry run isort .

# Check formatting
poetry run black --check .

# Type checking with strict mode
poetry run mypy --strict .

# Run custom type safety checker (no Any, cast, or type: ignore)
poetry run check-type-safety


# Run all type and quality checks
bash tools/run_type_checks.sh
```

#### Type Safety Enforcement

The codebase maintains 100% type safety through:

1. **MyPy Strict Mode**: Configured with `disallow_any_explicit = true` in `pyproject.toml`
2. **Custom Type Safety Checker**: `tools/check_type_safety.py` enforces:
   - No usage of `Any` type (imports or annotations)
   - No usage of `cast` function
   - No `type: ignore` comments
3. **Black Integration**: Automatic code formatting with PEP 8 compliance

Run the complete type checking pipeline:
```bash
docker compose exec mcts bash /app/tools/run_type_checks.sh
```

## Game Rules: Corridors

Corridors is a two-player board game where players race to reach the opposite side while strategically placing walls to block their opponent.

**Objective**: Be the first player to reach any square on the opposite side of the 9x9 board.

**Rules**:
- Players alternate turns
- Each turn: either move your pawn one square or place a wall (if you have walls remaining)
- Pawns can move horizontally or vertically to adjacent squares
- Pawns can jump over opponent's pawn if blocked by a wall
- Each player starts with 10 walls
- Walls block movement but cannot completely trap a player (must leave a path to victory)

**Move Notation**:
- `*(4,2)` - Move pawn to coordinates (4,2)
- `H(3,4)` - Place horizontal wall at intersection (3,4)
- `V(3,4)` - Place vertical wall at intersection (3,4)

## Architecture

### C++ Core (`backend/core/`)
- **`mcts.hpp`**: Generic template-based MCTS implementation
- **`board.h/.cpp`**: Corridors game logic and board representation
- **`corridors_api.h/.cpp`**: Synchronous API wrapper for Python
- **`_corridors_mcts.cpp`**: pybind11 bindings

### Python Interface (`backend/python/corridors/`)
- **`corridors_mcts.py`**: Main Python API with game management
- Provides high-level functions for play modes and visualization

### Testing (`tests/`)
- Comprehensive pytest suite with fixtures for different MCTS configurations
- Performance benchmarks and C++/Python integration tests

## MCTS Parameters

| Parameter | Description | Default | Notes |
|-----------|-------------|---------|-------|
| `c` | Exploration constant | `sqrt(2)` | Higher = wider search, Lower = deeper |
| `seed` | Random seed | `42` | For reproducible results |
| `min_simulations` | Minimum sims before move | `10000` | Quality vs speed tradeoff |
| `max_simulations` | Maximum simulations | `10000` | Computational budget |
| `sim_increment` | Sims per iteration | `250` | API responsiveness |
| `use_rollout` | Use random rollouts | `True` | vs heuristic evaluation |
| `eval_children` | Evaluate children immediately | `False` | PUCT-style expansion |
| `use_puct` | Use PUCT formula | `False` | vs traditional UCT |
| `use_probs` | Use action probabilities | `False` | Requires evaluation function |
| `decide_using_visits` | Choose by visit count | `True` | vs average reward |

## AI-Assisted Development

This repository includes a hardened Claude Code workflow system that prevents "no low surrogate" errors and ensures reliable AI-assisted development.

### Quick Start

```bash
# Start a new AI session
npm run ai:session:new

# Check for encoding issues
npm run sanitize:check

# Verify your setup
npm run ai:verify
```

### Key Protection Features

- **UTF-16 Surrogate Protection**: Automatically detects and fixes encoding issues that cause Claude errors
- **Payload Size Management**: Prevents oversized requests with auto-chunking recommendations  
- **Pre-commit Hooks**: Blocks problematic code from entering the repository
- **CI Integration**: Validates encoding safety on all pull requests

**📖 For complete documentation, see: [docs/ai-usage.md](docs/ai-usage.md)**

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`poetry run test`)
5. **Run AI safety checks** (`npm run ai:verify`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Performance Notes

- C++ backend provides significant performance advantages for simulation-heavy workloads
- Threading allows real-time interaction during MCTS computation
- Docker containers include performance profiling tools (valgrind, gprof)
- Benchmark tests help track performance regressions

## Troubleshooting

**Build Issues:**
- Ensure pybind11 is available for Python bindings
- Check Python version compatibility (requires 3.12+)
- Verify SCons is available (`pip install scons`)

**Docker Issues:**
- For GPU support, ensure NVIDIA Docker runtime is installed: `sudo apt install nvidia-docker2`
- GPU builds require both compose files: `docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d`
- Check if nvidia-smi works: `docker compose exec mcts nvidia-smi`
- Verify your image: `docker compose exec mcts cat /etc/os-release | head -2`
- Use `docker compose logs mcts` to debug startup issues
- For ARM builds on x86, expect slower performance due to QEMU emulation
- The C++ module is rebuilt on container start for architecture compatibility

**Import Errors:**
- Verify C++ module was built successfully (`_corridors_mcts.so`)
- Check PYTHONPATH includes the backend/python/ directory
- Run `poetry install` to ensure all dependencies are present

**C++ Extension Issues:**
- Verify extension built: `docker run --rm mcts:cpu python -c "from corridors import _corridors_mcts"`
- Check build location: `docker compose exec mcts ls -la /app/backend/build/`
- Rebuild in container: `docker compose exec mcts cd /app/backend/core && scons`
- Build artifacts are in Docker volumes, not on host filesystem

## License

This project is licensed under the MIT License - see the LICENSE file for details.# Test comment to trigger workflow Mon Sep  8 10:12:42 EDT 2025
