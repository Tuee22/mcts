# Test Command Reference

## Quick Reference

All tests must be run inside the Docker container per project requirements.

### Using Poetry Test Runner

```bash
# Complete test suite
docker compose exec mcts poetry run test-runner all

# Specific test suites
docker compose exec mcts poetry run test-runner unit        # Unit tests
docker compose exec mcts poetry run test-runner integration  # Integration tests  
docker compose exec mcts poetry run test-runner e2e          # E2E tests
docker compose exec mcts poetry run test-runner quick        # Fast tests only
docker compose exec mcts poetry run test-runner connection   # Connection tests

# With options
docker compose exec mcts poetry run test-runner unit -v --no-slow
docker compose exec mcts poetry run test-runner e2e --headed --video
docker compose exec mcts poetry run test-runner all --coverage
```

### Direct pytest Commands

```bash
# Unit tests
docker compose exec mcts pytest tests/backend/ -m "unit"

# Integration tests
docker compose exec mcts pytest tests/integration/ -m "integration"

# E2E tests (run from e2e directory)
docker compose exec mcts bash -c "cd tests/e2e && pytest -m e2e"

# All tests
docker compose exec mcts pytest tests/

# Specific markers
docker compose exec mcts pytest tests/ -m "websocket"
docker compose exec mcts pytest tests/ -m "cors"
docker compose exec mcts pytest tests/ -m "connection"
```

## Test Runner Commands

The test runner (`poetry run test-runner`) provides these commands:

- `all` - Run complete test suite
- `unit` - Run unit tests only
- `integration` - Run integration tests
- `e2e` - Run end-to-end tests
- `quick` - Run fast tests for quick feedback
- `connection` - Run connection-specific tests
- `websocket` - Run WebSocket tests
- `cors` - Run CORS tests
- `performance` - Run performance benchmarks
- `run` - Custom test execution with options

## Frontend Tests

Frontend tests run separately using npm:

```bash
# Unit tests
cd frontend && npm run test:unit

# All frontend tests
cd frontend && npm test
```

## Shell Aliases (Optional)

Add to your shell configuration for convenience:

```bash
alias mcts-test='docker compose exec mcts poetry run test-runner'
alias mcts-test-all='docker compose exec mcts poetry run test-runner all'
alias mcts-test-quick='docker compose exec mcts poetry run test-runner quick'
```