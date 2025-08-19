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

**Setup environment file:**
```bash
git clone <repository-url>
cd mcts/docker
cp .env.example .env
# Edit .env to choose CPU or GPU profile
```

**For CPU systems (AMD64 or ARM64/Apple Silicon):**
```bash
cd mcts/docker
COMPOSE_PROFILES=cpu docker compose up --build -d
docker compose exec mcts poetry run pytest -q
```

**For NVIDIA GPU systems (AMD64 only):**
```bash
cd mcts/docker
COMPOSE_PROFILES=gpu docker compose up --build -d
docker compose exec mcts-gpu nvidia-smi
docker compose exec mcts-gpu poetry run pytest -q
```

### Docker Configuration

The build system uses profile-based configuration controlled entirely via `.env`:
- **CPU profile**: Multi-arch support (AMD64/ARM64), uses `python:3.12-slim-bookworm`
- **GPU profile**: AMD64 only with NVIDIA GPU, uses `nvidia/cuda:12.6.2-devel-ubuntu24.04`

Note: CUDA builds on non-AMD64 architectures will fail early by design.

Configuration is handled via environment variables in `.env`:

```bash
# Switch between profiles by editing .env
COMPOSE_PROFILES=cpu    # or: gpu

# Optional: Override base images
CPU_BASE_IMAGE=python:3.12-slim-bookworm
CUDA_BASE_IMAGE=nvidia/cuda:12.6.2-devel-ubuntu24.04
```

### Running Tests

**All unit tests:**
```bash
# CPU container
docker compose exec mcts poetry run pytest tests/backend/core/ -v

# GPU container  
docker compose exec mcts-gpu poetry run pytest tests/backend/core/ -v
```

**Quick test run:**
```bash
# CPU
docker compose exec mcts poetry run pytest -q

# GPU
docker compose exec mcts-gpu poetry run pytest -q
```

**GPU verification (CUDA only):**
```bash
docker compose exec mcts-gpu nvidia-smi
```

### Access the Environment

Once the container is running:

```bash
# Access the container shell (CPU)
docker compose exec mcts bash

# Access the container shell (GPU)
docker compose exec mcts-gpu bash

# Run interactive Python session
docker compose exec mcts python3

# Check container logs
docker compose logs mcts      # or mcts-gpu for GPU profile
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

## Development

### Building C++ Components

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

### Running Tests

**Poetry Test Commands (Recommended):**
```bash
# All tests - Python backend and frontend (recommended)
poetry run test-all                # Runs all test suites

# Python backend tests
poetry run test-python              # All Python tests (core + API)
poetry run test-python-core         # Core MCTS and board tests only
poetry run test-python-api          # API server tests only

# Frontend tests
poetry run test-frontend             # JavaScript/TypeScript frontend tests
```

**Direct Docker Testing:**
```bash
# CPU container - all tests
docker exec docker-mcts-1 poetry run test-all

# Individual test suites in container
docker exec docker-mcts-1 poetry run test-python-core    # 117 tests
docker exec docker-mcts-1 poetry run test-python-api     # 58 tests  
docker exec docker-mcts-1 poetry run test-frontend       # 3 tests
```

**Advanced Testing Options:**
```bash
# Test categories with pytest markers
poetry run pytest tests/backend/core/ -m 'not slow'      # Fast tests only
poetry run pytest tests/backend/core/ -m performance     # Performance tests
poetry run pytest tests/backend/core/ -m integration     # Integration tests
poetry run pytest tests/backend/core/ -m cpp             # C++ binding tests
poetry run pytest tests/backend/core/ -m python          # Pure Python tests

# With coverage and verbose output
poetry run pytest tests/backend/core/ --cov=corridors -v

# Specific test files
poetry run pytest tests/backend/core/test_board.py       # Board functionality
poetry run pytest tests/backend/core/test_mcts.py        # MCTS algorithm
poetry run pytest tests/backend/api/test_server.py       # API endpoints
```

**GPU Testing (CUDA only):**
```bash
# CUDA container with GPU verification
TARGET=cuda RUNTIME=nvidia docker compose exec mcts poetry run test-all
TARGET=cuda RUNTIME=nvidia docker compose exec mcts nvidia-smi
```

### Code Quality

```bash
# Format code
poetry run black . && poetry run isort .

# Check formatting
poetry run black --check .

# Type checking
poetry run mypy python/ tests/
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

### C++ Core (`src/`)
- **`mcts.hpp`**: Generic template-based MCTS implementation
- **`board.h/.cpp`**: Corridors game logic and board representation
- **`corridors_threaded_api.h/.cpp`**: Thread-safe wrapper for Python
- **`_corridors_mcts.cpp`**: Boost.Python bindings

### Python Interface (`python/`)
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

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`poetry run test`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Performance Notes

- C++ backend provides significant performance advantages for simulation-heavy workloads
- Threading allows real-time interaction during MCTS computation
- Docker containers include performance profiling tools (valgrind, gprof)
- Benchmark tests help track performance regressions

## Troubleshooting

**Build Issues:**
- Ensure Boost libraries are installed with Python support
- Check Python version compatibility (requires 3.12+)
- Verify SCons is available (`pip install scons`)

**Docker Issues:**
- For GPU support, ensure NVIDIA Docker runtime is installed: `sudo apt install nvidia-docker2`
- CUDA builds require nvidia runtime: `TARGET=cuda RUNTIME=nvidia docker compose up -d`
- Check if nvidia-smi works: `TARGET=cuda RUNTIME=nvidia docker compose exec mcts nvidia-smi`
- Use `docker compose logs mcts` to debug startup issues
- For ARM builds on x86, expect slower performance due to QEMU emulation
- Check available platforms: `docker buildx ls`

**Import Errors:**
- Verify C++ module was built successfully (`_corridors_mcts.so`)
- Check PYTHONPATH includes the python/ directory
- Run `poetry install` to ensure all dependencies are present

## License

This project is licensed under the MIT License - see the LICENSE file for details.