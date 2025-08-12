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
- Docker Buildx (for multi-platform builds)
- Git

### Enable Docker Buildx

Docker Buildx enables building images for multiple architectures. Ensure it's available:

```bash
# Check if buildx is available
docker buildx version

# Create and use a new buildx builder (if needed)
docker buildx create --name multiarch --use

# Enable experimental features (if not already enabled)
# Add to ~/.docker/config.json:
# {
#   "experimental": "enabled"
# }
```

### Quick Start Instructions

**For CPU-only systems (any architecture):**
```bash
git clone <repository-url>
cd mcts/docker
docker compose up -d
```

**For systems with NVIDIA GPU:**
```bash
git clone <repository-url>
cd mcts/docker  
TARGET=cuda RUNTIME=nvidia docker compose up -d
```

Docker will automatically detect and build for your system's architecture (ARM64 for Apple Silicon, AMD64 for Intel/AMD).

### Advanced Multi-Platform Building

To build images for multiple platforms simultaneously:

```bash
# Build for both ARM64 and AMD64
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg TARGETARCH=cpu \
  -t mcts:multi \
  -f docker/Dockerfile \
  --push .

# Build and load locally for current platform only
docker buildx build \
  --platform linux/$(docker info --format '{{.Architecture}}') \
  --build-arg TARGETARCH=cpu \
  -t mcts:local \
  -f docker/Dockerfile \
  --load .
```

### Access the Environment

Once the container is running:

```bash
# Access the container shell
docker compose exec mcts bash

# Or access Jupyter Lab (automatically available)
# Open browser to: http://localhost:8888
```

The project directory is mounted at `/home/mcts` inside the container.


## Usage Examples

### Basic MCTS Game

```python
from python.corridors.corridors_mcts import Corridors_MCTS
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
from python.corridors.corridors_mcts import Corridors_MCTS, human_computer_play

# Start human vs computer game
mcts = Corridors_MCTS(min_simulations=5000)
human_computer_play(mcts, human_plays_first=True)
```

### Computer Self-Play

```python
from python.corridors.corridors_mcts import Corridors_MCTS, computer_self_play

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
cd src

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

**Comprehensive Test Suite (Python + Frontend):**
```bash
# Run all tests (Python API/Core + Frontend)
poetry run test-everything

# With coverage reports
poetry run test-everything --coverage

# Python tests only
poetry run test-everything --python-only

# Frontend tests only  
poetry run test-everything --frontend-only
```

**Python Tests Only:**
```bash
# All Python tests (API + Core)
poetry run test-all

# Specific Python test suites
poetry run test-api          # API and WebSocket tests
poetry run test-core         # Core MCTS and board tests

# Direct pytest usage
poetry run pytest           # All Python tests
poetry run pytest -m 'not slow'  # Fast tests only

# Specific test categories
poetry run pytest -m python      # Pure Python tests
poetry run pytest -m cpp         # C++ binding tests  
poetry run pytest -m integration # Integration tests
poetry run pytest -m performance # Performance tests

# Benchmarks
poetry run pytest tests/benchmarks/ --benchmark-only
```

**Frontend Tests Only:**
```bash
# From frontend test directory
cd tests/frontend
npm test                    # All frontend tests
npm run test:coverage       # With coverage
npm run test:watch          # Watch mode
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
- For GPU support, ensure NVIDIA Docker runtime is installed
- Check Docker platform matches your architecture
- Use `docker compose logs` to debug startup issues
- If buildx fails, ensure experimental features are enabled
- For "no builder instance" errors, create a buildx builder: `docker buildx create --use`

**Import Errors:**
- Verify C++ module was built successfully (`_corridors_mcts.so`)
- Check PYTHONPATH includes the python/ directory
- Run `poetry install` to ensure all dependencies are present

## License

This project is licensed under the MIT License - see the LICENSE file for details.