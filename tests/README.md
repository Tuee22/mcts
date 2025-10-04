# MCTS Testing Guide

This comprehensive guide covers all testing aspects for the MCTS project, including unit, integration, end-to-end tests, and async testing best practices.

## 📚 Table of Contents

1. [Quick Start](#quick-start)
2. [Test Architecture](#test-architecture)
3. [Async Testing Best Practices](#async-testing-best-practices)
4. [Test Execution Guide](#test-execution-guide)
5. [Test Categories & Coverage](#test-categories--coverage)
6. [Environment Configuration](#environment-configuration)
7. [Debugging & Troubleshooting](#debugging--troubleshooting)
8. [Writing Tests](#writing-tests)
9. [CI/CD Integration](#cicd-integration)

---

## Quick Start

**IMPORTANT**: All tests MUST be run inside Docker containers per project requirements.

### Essential Commands

```bash
# Start Docker services first
cd docker && docker compose up -d

# Run complete test suite
docker compose exec mcts poetry run test-all

# Run specific test categories
docker compose exec mcts poetry run test-unit        # Unit tests
docker compose exec mcts poetry run test-integration # Integration tests
docker compose exec mcts poetry run test-e2e         # End-to-end tests
docker compose exec mcts poetry run test-quick       # Fast tests only

# Frontend tests
docker compose exec mcts poetry run test-frontend
```


---

## Test Architecture

The MCTS project follows a comprehensive three-layer test pyramid:

```
           🔺 E2E Tests (Playwright)
          🔺🔺 Integration Tests (pytest + real services)  
       🔺🔺🔺🔺 Unit Tests (pytest + mocks, vitest)
```

### Test Layer Responsibilities

| Layer | Tool | Coverage | Purpose |
|-------|------|----------|---------|
| **Unit** | pytest, vitest | Components, functions, classes | Fast feedback, logic validation |
| **Integration** | pytest + real HTTP/WebSocket | API contracts, CORS, DB integration | Cross-service validation |  
| **E2E** | Playwright (Python) | Full user journeys | Real browser scenarios |

---

## Async Testing Best Practices

### ✅ Writing Async Tests

- [ ] Write tests as `async def` functions
- [ ] Use `@pytest.mark.asyncio` to let pytest run them
- [ ] Directly `await` the async functions you are testing

```python
@pytest.mark.asyncio
async def test_websocket_connection():
    async with websockets.connect(uri) as ws:
        message = await ws.recv()
        assert json.loads(message)["type"] == "connect"
```

### ✅ Async Fixtures

- [ ] Define async fixtures with `async def`
- [ ] Use `async with` in fixtures for proper resource cleanup

```python
@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(base_url="http://localhost:8000") as client:
        yield client
```

### ✅ Timeouts & Stability

- [ ] Wrap awaits in `asyncio.wait_for()` when hangs are possible
- [ ] Use synchronization primitives instead of arbitrary `sleep()`

```python
# Good - explicit timeout
message = await asyncio.wait_for(websocket.recv(), timeout=5.0)

# Bad - arbitrary sleep
await asyncio.sleep(2)  # Don't do this for "stability"

# Good - event-based synchronization
event = asyncio.Event()
await asyncio.wait_for(event.wait(), timeout=10.0)
```

### ✅ Background Tasks

- [ ] Ensure background tasks are awaited or canceled before test ends
- [ ] Clean up lingering tasks to prevent leaks between tests

```python
@pytest.mark.asyncio
async def test_with_background_task():
    task = asyncio.create_task(background_operation())
    try:
        # Test code here
        await test_operation()
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
```

### ✅ Mocking Async Dependencies

- [ ] Use `unittest.mock.AsyncMock` when mocking async functions
- [ ] Patch async functions consistently with `AsyncMock`

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_with_mock():
    mock_client = AsyncMock()
    mock_client.fetch_data.return_value = {"status": "ok"}
    
    result = await service_using_client(mock_client)
    assert result["status"] == "ok"
```

### ❌ Things to Avoid

- [ ] **DO NOT** call `asyncio.run()` inside async tests (pytest manages the event loop)
- [ ] **DO NOT** leave tasks running across tests
- [ ] **DO NOT** add `sleep()` for "stability" - use explicit sync mechanisms

### Sync Wrappers

Only create synchronous wrappers if:
- Your library **exposes a sync API** that wraps async code, or  
- You must integrate into a **sync-only system** (legacy hooks, external APIs)
- Keep wrappers minimal and only at the boundary

---

## Test Execution Guide

### Using Poetry Test Runner

The project provides Poetry test scripts for common test suites:

```bash
# Complete test suites
docker compose exec mcts poetry run test-all         # Everything
docker compose exec mcts poetry run test-unit        # Unit tests
docker compose exec mcts poetry run test-integration # Integration
docker compose exec mcts poetry run test-e2e         # End-to-end
docker compose exec mcts poetry run test-frontend    # Frontend tests

# Quick feedback
docker compose exec mcts poetry run test-quick       # Fast tests only
docker compose exec mcts poetry run test-fast        # Alternative fast tests

# Benchmarks
docker compose exec mcts poetry run test-benchmarks  # Performance tests

# With pytest markers directly (when needed)
docker compose exec mcts pytest -m websocket -v     # WebSocket tests
docker compose exec mcts pytest -m cors -v          # CORS tests
docker compose exec mcts pytest -m performance -v   # Performance tests
```

### Direct pytest Commands

```bash
# Unit tests by category
docker compose exec mcts pytest tests/backend/core/ -m "unit"
docker compose exec mcts pytest tests/backend/api/ -m "unit"

# Integration tests by category
docker compose exec mcts pytest tests/integration/ -m "websocket"
docker compose exec mcts pytest tests/integration/ -m "cors"
docker compose exec mcts pytest tests/integration/ -m "connection"

# E2E tests
docker compose exec mcts poetry run test-e2e

# Performance benchmarks
docker compose exec mcts poetry run test-benchmarks
```

### Frontend Testing


```bash
# Run frontend tests using Poetry script (recommended)
docker compose exec mcts poetry run test-frontend

# Direct npm commands (if needed)
docker compose exec mcts cd /app/frontend && npm run test          # Interactive
docker compose exec mcts cd /app/frontend && npm run test:run      # Run once
docker compose exec mcts cd /app/frontend && npm run test:ui       # Web UI
docker compose exec mcts cd /app/frontend && npm run test:coverage # Coverage

# Direct vitest commands (vitest installed globally in container)
docker compose exec mcts cd /app/frontend && vitest run           # Run once
docker compose exec mcts cd /app/frontend && vitest --ui          # Web UI
docker compose exec mcts cd /app/frontend && vitest --coverage    # Coverage
```

---

## Test Categories & Coverage

### 🧪 Unit Tests
- **Location**: `tests/backend/core/`, `tests/backend/api/`
- **Speed**: Fast (~10-30 seconds)
- **Key Files**:
  - `test_cpp_board_functions.py` - C++ board implementation
  - `test_python_functions.py` - Python wrapper tests
  - `test_models.py` - Pydantic model validation
  - `test_error_paths.py` - Error handling

### 🔗 Integration Tests
- **Location**: `tests/integration/`
- **Speed**: Medium (~30-60 seconds)
- **Key Files**:
  - `test_websocket_connection.py` - WebSocket protocol
  - `test_api_configuration.py` - FastAPI configuration
  - `test_cors_configuration.py` - Cross-origin handling
  - `test_network_failures.py` - Network resilience

### ⚡ Benchmark Tests
- **Location**: `tests/benchmarks/`
- **Speed**: Slow (~60+ seconds)
- **Key Files**:
  - `test_benchmarks.py` - MCTS algorithm performance

### ⚛️ Frontend Tests
- **Location**: `tests/frontend/`, `frontend/src/`
- **Speed**: Medium (~20-45 seconds)
- **Key Files**:
  - `GameBoard.test.tsx` - Game board component
  - `GameSettings.test.tsx` - Settings interface
  - `gameStore.test.ts` - State management
  - `websocket.test.ts` - Frontend WebSocket client

### 🌐 End-to-End Tests
- **Location**: `tests/e2e/`
- **Speed**: Slowest (~90+ seconds)
- **Key Files**:
  - `test_connection_scenarios.py` - Connection patterns
  - `test_network_failures_fixed.py` - Network resilience
  - `test_browser_compatibility.py` - Cross-browser

### Test Markers

```python
@pytest.mark.unit         # Unit tests
@pytest.mark.integration  # Integration tests
@pytest.mark.benchmark    # Performance benchmarks
@pytest.mark.e2e         # End-to-end tests
@pytest.mark.slow        # Long-running tests
@pytest.mark.asyncio     # Async tests
@pytest.mark.websocket   # WebSocket tests
@pytest.mark.cors        # CORS tests
```

### Coverage Targets

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| Backend API | 85% | TBD |
| WebSocket handlers | 90% | TBD |
| Frontend components | 80% | TBD |
| Integration flows | 70% | TBD |

---

## Environment Configuration

### E2E Test Configuration

E2E tests use Playwright with configuration at `tests/e2e/playwright.config.py`.

**Important**: Use the Poetry script for E2E tests (handles configuration automatically):

```bash
# Recommended way - handles E2E configuration
docker compose exec mcts poetry run test-e2e

# Alternative direct method (ensure correct directory)
docker compose exec mcts bash -c "cd tests/e2e && pytest -m e2e"

# Incorrect - won't find playwright.config.py
docker compose exec mcts pytest tests/e2e/ -m e2e
```

### Environment Variables

| Variable | Description | Default | Used By |
|----------|-------------|---------|---------|
| `E2E_BACKEND_URL` | Backend URL for E2E tests | `http://localhost:8002` | E2E |
| `E2E_FRONTEND_URL` | Frontend URL for E2E tests | `http://localhost:3002` | E2E |
| `E2E_WS_URL` | WebSocket URL for E2E tests | `ws://localhost:8002/ws` | E2E |
| `E2E_HEADLESS` | Run E2E tests headlessly | `true` | E2E |
| `E2E_VIDEO` | Video recording mode | `retain-on-failure` | E2E |
| `E2E_TRACE` | Playwright tracing | `retain-on-failure` | E2E |
| `MCTS_API_HOST` | Integration test API host | `127.0.0.1` | Integration |
| `MCTS_API_PORT` | Integration test API port | `8001` | Integration |

### Test Data Seeding

Tests use deterministic data seeding:

```python
from tests.fixtures.data_seeder import TestDataSeeder

async with TestDataSeeder("http://localhost:8001") as seeder:
    games = await seeder.seed_test_games(count=5)
    error_game = await seeder.create_error_scenario_game("blocked_move")
```

---

## Debugging & Troubleshooting

### E2E Test Failures

Artifacts are saved to help debugging:

```bash
# Screenshots on failure
tests/e2e/screenshots/{test_name}.png

# Videos (if enabled)
tests/e2e/videos/{test_name}/

# Playwright traces
tests/e2e/traces/{test_name}.zip

# View trace interactively
poetry run playwright show-trace tests/e2e/traces/{test_name}.zip
```

### Common Issues

#### Connection Timeout Errors

```bash
# Check services
curl http://localhost:8001/health
cd docker && docker compose ps

# Increase timeouts for slower systems
E2E_TIMEOUT=60000 poetry run pytest tests/e2e/ -v
```

#### WebSocket Connection Refused

```bash
# Verify WebSocket URL
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     http://localhost:8001/ws

# Check CORS configuration
curl -H "Origin: http://localhost:3001" \
     http://localhost:8001/health

# Use different ports for parallel runs
MCTS_API_PORT=8003 poetry run pytest tests/integration/ -v
```

#### Element Not Found in E2E

```bash
# Run with browser visible
docker compose exec mcts poetry run test-e2e --headed

# Use explicit waits
await page.wait_for_selector('[data-testid="connection-status"]', timeout=10000)
```

### Performance Issues

```bash
# Run only fast tests during development
docker compose exec mcts poetry run test-fast

# Profile test execution
docker compose exec mcts pytest --durations=10 tests/

# Run tests in parallel (careful with shared resources)
docker compose exec mcts pytest -n auto tests/backend/
```

### Port Conflicts

```bash
# Check what's using test ports
lsof -i :8001 -i :3001 -i :8002 -i :3002

# Kill processes
pkill -f "uvicorn.*8001"
pkill -f "serve.*3001"
```

### Docker Issues

```bash
# Reset Docker environment
cd docker
docker compose down -v
docker compose build --no-cache
docker compose up -d

# Check logs
docker compose logs mcts
```

### Clean Test Environment

```bash
# Full reset
rm -rf tests/e2e/screenshots/* tests/e2e/videos/* tests/e2e/traces/*
pkill -f pytest
pkill -f uvicorn
pkill -f serve
```

---

## Writing Tests

### Adding Async Tests

```python
import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
@pytest.mark.integration
async def test_async_api_endpoint():
    async with AsyncClient(base_url="http://localhost:8001") as client:
        response = await client.post("/api/endpoint", json={"data": "test"})
        assert response.status_code == 200
        
        # Use wait_for for operations that might hang
        result = await asyncio.wait_for(
            client.get("/api/slow-endpoint"),
            timeout=10.0
        )
        assert result.status_code == 200
```

### Adding E2E Tests

```python
# tests/e2e/test_new_feature.py
import pytest
from playwright.async_api import Page, expect

@pytest.mark.e2e 
@pytest.mark.asyncio
async def test_new_connection_scenario(page: Page, e2e_urls):
    await page.goto(e2e_urls["frontend"])
    
    # Wait for connection
    await expect(page.locator('[data-testid="connection-text"]')).to_have_text("Connected")
    
    # Test your scenario
    await page.click('[data-testid="start-game"]')
    await expect(page.locator('[data-testid="game-board"]')).to_be_visible()

# Run using Poetry script (recommended):
# docker compose exec mcts poetry run test-e2e
```

### Adding Integration Tests

```python
# tests/integration/test_new_integration.py
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_new_api_endpoint(backend_server, test_config):
    async with AsyncClient(
        base_url=f"http://{test_config['api_host']}:{test_config['api_port']}"
    ) as client:
        response = await client.post("/new-endpoint", json={})
        assert response.status_code == 200
```

### Test Data Fixtures

```python
from tests.fixtures.game_data import TestGameData

def test_with_game_data():
    game_config = TestGameData.get_game_config("quick_human_vs_ai")
    moves = TestGameData.get_move_sequence("opening_moves")
    # Test implementation
```

## Flakiness Prevention

- ✅ **Deterministic test data** via fixtures
- ✅ **Explicit waits** instead of sleeps
- ✅ **Stable selectors** (data-testid, not CSS)
- ✅ **Service readiness** checks before tests
- ✅ **Isolated test environments** (unique ports)
- ✅ **Retry logic** for known-flaky scenarios
- ✅ **Quarantine markers** for unstable tests

### Quarantine Tests

```python
@pytest.mark.quarantine
@pytest.mark.skip(reason="Flaky - investigating connection issues")
def test_flaky_scenario():
    pass
```

Run quarantined tests separately:

```bash
docker compose exec mcts pytest -m quarantine -v
```

---

## CI/CD Integration

The CI pipeline runs tests in stages:

1. **Unit Tests** (fast feedback ~5 min)
2. **Integration Tests** (service validation ~10 min)  
3. **E2E Tests** (full scenarios ~15 min)
4. **Performance Tests** (nightly only ~30 min)

### CI Environment Variables

```yaml
env:
  E2E_HEADLESS: true
  E2E_VIDEO: retain-on-failure  
  E2E_TRACE: retain-on-failure
  CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

### Artifact Collection

CI automatically collects:
- Coverage reports (XML/HTML)
- E2E screenshots/videos on failure
- Playwright traces for debugging
- Performance benchmark results

## Test Execution Summary

When you run `poetry run test-all`, you get a comprehensive summary:

```
📊 TEST EXECUTION SUMMARY
================================================================================
🎉 All executed tests passed!

📋 Test Suite Results:
  ✅ Unit Tests - Core: PASSED
  ✅ Unit Tests - API: PASSED  
  ✅ Integration Tests: PASSED
  ✅ Utility & Fixture Tests: PASSED
  ✅ Benchmark Tests: PASSED
  ✅ Frontend Tests: PASSED
  ✅ E2E Tests: PASSED

📊 Summary: 7 passed, 0 failed, 0 skipped (of 7 suites)
================================================================================
```

## Contributing Guidelines

1. **Add tests for new features** - especially connection-related code
2. **Update this documentation** when adding new test categories
3. **Use existing fixtures** instead of creating new test data
4. **Add appropriate markers** (`@pytest.mark.integration`, etc.)
5. **Test failure scenarios** - don't just test happy paths
6. **Consider flakiness** - use explicit waits and stable selectors
7. **Follow async best practices** - review the checklist above

