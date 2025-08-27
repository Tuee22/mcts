# Testing Guide for MCTS Project

This document explains the comprehensive testing strategy for the MCTS project, covering unit, integration, and end-to-end tests designed to catch disconnection and connection issues early.

## Test Pyramid Overview

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

## Running Tests Locally

### Prerequisites

```bash
# Install Python dependencies
poetry install --with dev

# Install frontend dependencies  
cd frontend && npm install

# Install Playwright browsers
poetry run playwright install chromium

# Build C++ components
cd backend/core && poetry run scons
```

### Setting up Convenient Aliases (Optional)

For frequently used commands, you can add these aliases to your shell configuration:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias mcts-test-all='docker compose exec mcts poetry run test-runner all'
alias mcts-test-unit='docker compose exec mcts poetry run test-runner unit'
alias mcts-test-quick='docker compose exec mcts poetry run test-runner quick'
alias mcts-test-e2e='docker compose exec mcts poetry run test-runner e2e'
```

### Quick Test Commands

All test commands must be run inside the Docker container as per project requirements:

```bash
# Run all tests (unit + integration + e2e)
docker compose exec mcts poetry run test-runner all

# Run specific test suites
docker compose exec mcts poetry run test-runner unit        # Unit tests only
docker compose exec mcts poetry run test-runner integration  # Integration tests
docker compose exec mcts poetry run test-runner e2e          # End-to-end tests
docker compose exec mcts poetry run test-runner quick        # Fast tests only

# Test connection scenarios specifically
docker compose exec mcts poetry run test-runner connection

# Run with options
docker compose exec mcts poetry run test-runner unit -v --no-slow    # Verbose, skip slow
docker compose exec mcts poetry run test-runner e2e --headed --video  # Visual debugging
docker compose exec mcts poetry run test-runner all --coverage        # With coverage

# Custom test execution
docker compose exec mcts poetry run test-runner run tests/e2e/ -k "connection" -v
```

### Alternative: Direct pytest commands

```bash
# Unit tests only (fast)
docker compose exec mcts pytest -m "unit and not slow"
cd frontend && npm run test:unit

# Integration tests (with real services)
docker compose exec mcts pytest tests/integration/ -m integration

# E2E tests (full browser) - run from E2E directory
docker compose exec mcts bash -c "cd tests/e2e && pytest -m e2e"

# All tests
docker compose exec mcts pytest tests/
```

### Detailed Test Commands

#### Backend Tests

```bash
# Unit tests by category
poetry run pytest tests/backend/core/ -m "unit"          # C++ bindings
poetry run pytest tests/backend/api/ -m "unit"           # FastAPI logic

# Integration tests by category  
poetry run pytest tests/integration/ -m "websocket"      # WebSocket connections
poetry run pytest tests/integration/ -m "cors"           # CORS configuration
poetry run pytest tests/integration/ -m "connection"     # Connection handling

# Performance tests
poetry run pytest tests/ -m "performance" --benchmark-only
```

#### Frontend Tests

```bash
cd frontend

# Unit tests
npm run test:unit                    # Component tests
npm run test:unit -- --coverage     # With coverage

# Integration tests  
npm run test:integration            # Component interactions
```

#### E2E Tests

```bash
# Quick connection tests (run from e2e directory)
docker compose exec mcts bash -c "cd tests/e2e && pytest test_connection_scenarios.py -v"

# Network failure scenarios (run from e2e directory)
docker compose exec mcts bash -c "cd tests/e2e && pytest test_network_failures.py -v"

# All E2E with video recording (run from e2e directory)
docker compose exec mcts bash -c "cd tests/e2e && E2E_VIDEO=on pytest -m e2e -v"
```

## Test Environment Configuration

### E2E Test Configuration

E2E tests use Playwright with configuration located at `tests/e2e/playwright.config.py`. This configuration file includes:

- Browser settings (Chromium, Firefox, WebKit)
- Test timeouts and retry policies  
- Video recording and screenshot settings
- Web server startup configuration for backend and frontend

**Important**: E2E tests must be run from the `tests/e2e/` directory to properly locate the configuration:

```bash
# Correct way to run E2E tests
docker compose exec mcts bash -c "cd tests/e2e && pytest -m e2e"

# Incorrect - will not find playwright.config.py
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
| `REACT_APP_WS_URL` | Frontend WebSocket URL | `ws://localhost:8000/ws` | Frontend |

### Test Data Seeding

Tests use deterministic data seeding for consistency:

```python
from tests.fixtures.test_data_seeder import TestDataSeeder

# Seed backend with test data
async with TestDataSeeder("http://localhost:8001") as seeder:
    games = await seeder.seed_test_games(count=5)
    error_game = await seeder.create_error_scenario_game("blocked_move")
```

## Key Test Scenarios

### Connection Scenarios (E2E)

These tests catch the "disconnection" issues mentioned in requirements:

- ✅ **Successful connection on app load**
- ✅ **Backend unreachable shows disconnection UI**
- ✅ **Connection recovery after backend restart**
- ✅ **Wrong API URL configuration handling**
- ✅ **Network interruption during gameplay**
- ✅ **CORS-blocked request detection**
- ✅ **Multiple tabs connection handling**

### Network Failure Scenarios

- ✅ **WebSocket connection timeout**
- ✅ **Partial message delivery**
- ✅ **Protocol violations**
- ✅ **High latency conditions**
- ✅ **Rapid connect/disconnect cycles**
- ✅ **Message queuing during disconnects**

### API Configuration Tests

- ✅ **CORS headers validation**
- ✅ **Environment variable configuration**
- ✅ **Error response format consistency**
- ✅ **Concurrent request handling**

## Debugging Test Failures

### E2E Test Failures

When E2E tests fail, artifacts are saved to help debugging:

```bash
# Screenshots on failure
tests/e2e/screenshots/{test_name}.png

# Videos (if enabled)
tests/e2e/videos/{test_name}/

# Playwright traces (interactive debugging)
tests/e2e/traces/{test_name}.zip

# View trace in Playwright inspector
poetry run playwright show-trace tests/e2e/traces/{test_name}.zip
```

### Common Failure Patterns

#### "Connection Timeout" Errors

**Symptoms**: Tests fail with timeout connecting to services

**Solutions**:
```bash
# Check if services are running
curl http://localhost:8001/health     # Backend health
curl http://localhost:3001            # Frontend availability

# Increase timeouts for slower systems
E2E_TIMEOUT=60000 poetry run pytest tests/e2e/ -v

# Check Docker services
cd docker && docker compose ps
```

#### "WebSocket Connection Refused" Errors  

**Symptoms**: WebSocket tests fail with connection refused

**Solutions**:
```bash
# Verify WebSocket URL
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     http://localhost:8001/ws

# Check CORS configuration
curl -H "Origin: http://localhost:3001" \
     http://localhost:8001/health

# Use different ports for parallel test runs
MCTS_API_PORT=8003 poetry run pytest tests/integration/ -v
```

#### "Element Not Found" in E2E Tests

**Symptoms**: E2E tests can't find UI elements

**Solutions**:
```bash
# Check if data-testid attributes are present
poetry run pytest tests/e2e/ -v -s --headed  # Run with browser visible

# Verify frontend build includes test attributes
cd frontend && npm run build
grep -r "data-testid" build/static/js/

# Use explicit waits
await page.wait_for_selector('[data-testid="connection-status"]', timeout=10000)
```

### Performance Issues

```bash
# Run only fast tests during development
poetry run pytest -m "not slow" -v

# Profile test execution
poetry run pytest --durations=10 tests/

# Run tests in parallel (be careful with shared resources)
poetry run pytest -n auto tests/backend/
```

## CI/CD Integration

The CI pipeline runs tests in stages:

1. **Unit Tests** (fast feedback ~5 min)
2. **Integration Tests** (service validation ~10 min)  
3. **E2E Tests** (full scenarios ~15 min)
4. **Performance Tests** (nightly only ~30 min)

### CI Environment Variables

Set these in your CI system:

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

## Test Coverage Targets

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| Backend API | 85% | TBD |
| WebSocket handlers | 90% | TBD |
| Frontend components | 80% | TBD |
| Integration flows | 70% | TBD |

## Writing New Tests

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
    # ...

# Note: E2E tests should be run from the tests/e2e directory:
# docker compose exec mcts bash -c "cd tests/e2e && pytest test_new_feature.py -v"
```

### Adding Integration Tests

```python
# tests/integration/test_new_api.py
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
# Use existing fixtures for consistency
from tests.fixtures.game_data import TestGameData

def test_with_game_data():
    game_config = TestGameData.get_game_config("quick_human_vs_ai")
    moves = TestGameData.get_move_sequence("opening_moves")
    # ...
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

Mark flaky tests for investigation:

```python
@pytest.mark.quarantine
@pytest.mark.skip(reason="Flaky - investigating connection issues")
def test_flaky_scenario():
    pass
```

Run quarantined tests separately:
```bash
poetry run pytest -m quarantine -v
```

## Troubleshooting

### Port Conflicts

```bash
# Check what's using your test ports
lsof -i :8001 -i :3001 -i :8002 -i :3002

# Kill processes using test ports
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

# Check Docker logs
docker compose logs mcts
```

### Clean Test Environment

```bash
# Full reset
make clean-test-env

# Manual cleanup
rm -rf tests/e2e/screenshots/* tests/e2e/videos/* tests/e2e/traces/*
pkill -f pytest
pkill -f uvicorn
pkill -f serve
```

## Contributing Guidelines

1. **Add tests for new features** - especially connection-related code
2. **Update this documentation** when adding new test categories
3. **Use existing fixtures** instead of creating new test data
4. **Add appropriate markers** (`@pytest.mark.integration`, etc.)
5. **Test failure scenarios** - don't just test happy paths
6. **Consider flakiness** - use explicit waits and stable selectors

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright Python Documentation](https://playwright.dev/python/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Testing WebSockets](https://websockets.readthedocs.io/en/stable/topics/testing.html)