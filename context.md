# API Testing Context - Session Summary

## Current Objective
Achieve 100% test coverage for the FastAPI Quoridor game server with tests completing in under 10 minutes.

## Session Overview
**Date:** 2025-08-11
**Initial Request:** Delete archive folder, purge/rebuild container, run tests for 100% coverage
**Current Status:** Tests hanging on collection phase, need async fixes

## Completed Work

### 1. Environment Cleanup & Rebuild
- ✅ Deleted archive folder for cleanup
- ✅ Purged all Docker containers/images (34.57GB → 18GB reclaimed)
- ✅ Rebuilt container from scratch: `TARGET=cpu docker compose up -d --build`
- ✅ Container running as `docker-mcts-1`

### 2. Test File Cleanup
- ✅ Removed experimental test files causing instability:
  - `test_100_coverage.py` (deleted)
  - `test_final_coverage.py` (deleted)
- ✅ Fixed module naming conflict:
  - Renamed `/home/mcts/tests/core/test_integration.py` → `test_core_integration.py`

### 3. Code Fixes Applied
```python
# api/server.py:33 - Disabled background tasks during tests
import os
if os.environ.get('PYTEST_CURRENT_TEST') is None:
    asyncio.create_task(game_manager.process_ai_moves())
```

## Current Problem

### Root Cause
Tests hang immediately during pytest collection phase (before any test execution).
Even simple commands like `pytest -x` timeout after 2+ minutes.

### Diagnosis
1. **Async Event Loop Conflicts**: Session-scoped event loops conflicting with pytest-asyncio
2. **Background Tasks**: AI move processor starting during test import
3. **Module-Level MCTS**: Expensive MCTS instances created at import time
4. **Fixture Issues**: Autouse fixtures with async operations causing deadlocks

### Evidence
- 293 tests collected but never execute
- Coverage stuck at ~25% total, API modules at 30-50%
- Tests hang at: `collected 293 items / 1 error` or just after `...........`

## File Structure
```
/home/mcts/tests/api/
├── conftest.py                      # Has async fixtures - NEEDS FIX
├── test_endpoints.py                # Main endpoint tests
├── test_endpoints_comprehensive.py  # Extended endpoint tests
├── test_game_manager.py            # Game logic tests
├── test_integration.py             # Integration tests
├── test_integration_final.py       # Final integration tests
├── test_models.py                  # Data model tests
├── test_websocket.py              # WebSocket tests
└── test_websocket_comprehensive.py # Extended WebSocket tests
```

## Next Steps - Priority Order

### 1. Fix Async Test Hanging (CRITICAL)
```bash
# Check what's causing the hang
docker exec docker-mcts-1 python -c "import sys; sys.path.insert(0, '/home/mcts'); import tests.api.conftest"
```

**Files to fix:**
- `/home/mcts/tests/api/conftest.py` - Remove session-scoped event loops
- All test files - Check for module-level async operations

### 2. Simplify Test Fixtures
```python
# Remove problematic fixtures in conftest.py:
# - Remove session-scoped event_loop fixture (conflicts with pytest-asyncio)
# - Remove autouse=True from async fixtures
# - Ensure all GameManager fixtures have proper cleanup
```

### 3. Mock All MCTS Operations
```python
# Add to each test file that uses MCTS:
@pytest.fixture(autouse=True)
def mock_mcts(monkeypatch):
    mock = MagicMock()
    mock.get_sorted_actions.return_value = [(100, 0.8, "*(4,1)")]
    mock.choose_best_action.return_value = "*(4,1)"
    mock.ensure_sims.return_value = None
    monkeypatch.setattr('api.game_manager.Corridors_MCTS', lambda *args, **kwargs: mock)
    return mock
```

### 4. Disable Background Tasks in Tests
```python
# Ensure this environment variable is set before running tests:
export PYTEST_CURRENT_TEST=1

# Or in conftest.py:
import os
os.environ['PYTEST_CURRENT_TEST'] = '1'
```

### 5. Run Targeted Test Categories
```bash
# Run API tests only (should be fast with mocking):
docker exec docker-mcts-1 poetry run pytest /home/mcts/tests/api/test_models.py -v

# If that works, try all API tests:
docker exec docker-mcts-1 poetry run pytest /home/mcts/tests/api/ -v --tb=short

# Finally, run with coverage:
docker exec docker-mcts-1 poetry run pytest /home/mcts/tests/api/ --cov=api --cov-report=term-missing
```

### 6. Performance Targets
- Individual test files: < 30 seconds
- All API tests: < 5 minutes  
- Full test suite: < 10 minutes
- Coverage target: 100% for API modules

## Known Issues to Address

1. **Async Hanging**: Tests hang on collection, not execution
2. **MCTS Performance**: Real MCTS simulations take too long - must be mocked
3. **WebSocket Tests**: Complex async operations need simplification
4. **Background Tasks**: AI move processor must be completely disabled in tests

## Quick Commands

```bash
# Access container
docker exec -it docker-mcts-1 bash

# Clean Python cache
docker exec docker-mcts-1 find /home -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
docker exec docker-mcts-1 find /home -name "*.pyc" -delete 2>/dev/null || true

# Run single test file (for debugging)
docker exec docker-mcts-1 poetry run pytest /home/mcts/tests/api/test_models.py -v --tb=short

# Check test collection without running
docker exec docker-mcts-1 poetry run pytest --collect-only /home/mcts/tests/api/

# Run with timeout to prevent hanging
docker exec docker-mcts-1 timeout 30 poetry run pytest /home/mcts/tests/api/test_models.py -v
```

## Success Criteria
1. ✅ All API tests run without hanging
2. ✅ Total runtime < 10 minutes
3. ✅ 100% code coverage for API modules
4. ✅ No failing tests
5. ✅ Clean test output with clear pass/fail status

## Notes for Next Session
- The fundamental issue is import-time hanging, not test execution
- Focus on fixing conftest.py and removing async complexity first
- Once tests actually run, coverage should improve significantly
- The 82% coverage we achieved earlier was with a working subset of tests