# Test Suite Organization

This directory contains the complete test suite for the MCTS Corridors project.

## Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Global test configuration and fixtures
├── pytest.ini                  # Test configuration (if needed)
│
├── api/                         # FastAPI server tests
│   ├── conftest.py             # API-specific fixtures
│   ├── test_models.py          # Pydantic model tests
│   ├── test_endpoints.py       # REST API endpoint tests
│   ├── test_websocket.py       # WebSocket functionality tests
│   ├── test_game_manager.py    # Game logic and state management
│   └── test_integration.py     # End-to-end API workflows
│
├── core/                        # Core MCTS and board logic tests
│   ├── test_cpp_board_functions.py
│   ├── test_python_functions.py
│   ├── test_integration.py
│   ├── test_edge_cases.py
│   └── test_performance.py
│
├── fixtures/                    # Shared test data and fixtures
│   ├── __init__.py
│   ├── game_data.py            # Sample game states and moves
│   ├── mcts_configs.py         # MCTS configuration presets
│   └── board_states.py         # Pre-built board positions
│
├── utils/                       # Test utilities and runners
│   ├── __init__.py
│   ├── run_api_tests.py        # API test runner script
│   ├── run_core_tests.py       # Core logic test runner
│   ├── test_helpers.py         # Common test helper functions
│   └── mocks.py                # Reusable mock objects
│
└── benchmarks/                  # Performance benchmarks
    ├── test_benchmarks.py
    └── benchmark_configs.py
```

## Running Tests

### Quick Commands
```bash
# All tests
pytest tests/

# API tests only
pytest tests/api/

# Core logic tests only  
pytest tests/core/

# With coverage
pytest tests/ --cov=api --cov=python
```

### Using Test Runners
```bash
# API test runner
python tests/utils/run_api_tests.py --type fast --coverage

# Core test runner
python tests/utils/run_core_tests.py --performance
```

### Test Categories (Markers)
```bash
pytest -m unit          # Unit tests
pytest -m integration   # Integration tests
pytest -m "not slow"    # Exclude slow tests
pytest -m api           # API-related tests
pytest -m mcts          # MCTS algorithm tests
```

## Test Organization Principles

1. **Separation by Domain**: API, core logic, benchmarks in separate directories
2. **Shared Fixtures**: Common test data in dedicated fixtures directory
3. **Reusable Utilities**: Test helpers and mock objects in utils
4. **Clear Naming**: Descriptive test file and function names
5. **Proper Scoping**: Use appropriate fixture scopes (session, module, function)

## Adding New Tests

1. Place tests in the appropriate domain directory
2. Use existing fixtures from `fixtures/` when possible
3. Add new shared fixtures to appropriate conftest.py
4. Follow naming conventions: `test_*.py` for files, `test_*` for functions
5. Use appropriate markers for categorization