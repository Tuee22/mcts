# Test Coverage Guide

This document explains the comprehensive test coverage provided by the MCTS project's test suite.

## Test Structure Overview

The project uses a **unified test runner** (`poetry run test-all`) that ensures **every test file** in the repository is executed. The test suite is organized into clear categories for both comprehensive coverage and efficient subset execution.

## Test Categories

### 🧪 Unit Tests (`poetry run test-unit`)
- **Location**: `tests/backend/core/`, `tests/backend/api/`
- **Coverage**: Core MCTS algorithms, board logic, API endpoints, data models
- **Speed**: Fast (~10-30 seconds)
- **Purpose**: Test individual components in isolation

**Key Test Files:**
- `test_cpp_board_functions.py` - C++ board implementation tests
- `test_python_functions.py` - Python wrapper tests  
- `test_models.py` - Pydantic model validation
- `test_error_paths.py` - Error handling and edge cases

### 🔗 Integration Tests (`poetry run test-integration`)
- **Location**: `tests/integration/`
- **Coverage**: API configuration, WebSocket connections, CORS, network failures
- **Speed**: Medium (~30-60 seconds)
- **Purpose**: Test component interactions and system configuration

**Key Test Files:**
- `test_websocket_connection.py` - WebSocket protocol testing
- `test_api_configuration.py` - FastAPI server configuration
- `test_cors_configuration.py` - Cross-origin request handling
- `test_network_failures.py` - Network resilience testing

### ⚡ Benchmark Tests (`poetry run test-benchmarks`)
- **Location**: `tests/benchmarks/`
- **Coverage**: Performance characteristics, memory usage, stress testing
- **Speed**: Slow (~60+ seconds)
- **Purpose**: Ensure performance standards and identify regressions

**Key Test Files:**
- `test_benchmarks.py` - MCTS algorithm performance benchmarks

### 🛠️ Utility & Fixture Tests (`poetry run test-utils`)
- **Location**: `tests/utils/`, `tests/fixtures/`
- **Coverage**: Test infrastructure, data seeding, helper functions
- **Speed**: Fast (~5-15 seconds)  
- **Purpose**: Verify test tooling and data generation

**Key Test Files:**
- `test_helpers.py` - Test utility functions
- `test_data_seeder.py` - Test data generation
- `test_runner.py` - Test execution infrastructure

### ⚛️ Frontend Tests (`poetry run test-frontend`)
- **Location**: `tests/frontend/`, `frontend/src/`
- **Coverage**: React components, state management, UI interactions
- **Speed**: Medium (~20-45 seconds)
- **Purpose**: Test user interface and frontend logic

**Key Test Files:**
- `GameBoard.test.tsx` - Game board component tests
- `GameSettings.test.tsx` - Settings interface tests
- `gameStore.test.ts` - State management tests
- `websocket.test.ts` - Frontend WebSocket client tests

### 🌐 End-to-End Tests (`poetry run test-e2e`)
- **Location**: `tests/e2e/`
- **Coverage**: Full application workflows, browser automation, user scenarios
- **Speed**: Slowest (~90+ seconds)
- **Purpose**: Test complete user journeys and system integration

**Key Test Files:**
- `test_working_connection.py` - Basic connection workflows
- `test_connection_scenarios.py` - Complex connection patterns
- `test_browser_compatibility.py` - Cross-browser testing
- `test_network_failures_fixed.py` - Network resilience E2E tests

## Running Tests

### Complete Test Suite
```bash
# Run ALL tests - this is the comprehensive option
poetry run test-all
```

### Test Category Subsets
```bash
poetry run test-unit         # Unit tests only
poetry run test-integration  # Integration tests only  
poetry run test-benchmarks   # Benchmark tests only
poetry run test-python       # All Python tests (unit + integration + benchmarks + utils)
poetry run test-frontend     # Frontend tests only
poetry run test-e2e         # End-to-end tests only
```

### Convenience Runners
```bash
poetry run test-fast     # Excludes benchmarks and E2E (for development)
poetry run test-quick    # Unit tests only (fastest feedback)
```

### Advanced Options
```bash
# Run with coverage
poetry run test-all --coverage

# Run with verbose output
poetry run test-all --verbose

# Stop on first failure
poetry run test-all --fail-fast

# Skip specific categories
poetry run test-all --skip-benchmarks --skip-e2e
```

## Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.benchmark` - Performance benchmarks
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.performance` - Performance-critical tests
- `@pytest.mark.cpp` - C++ binding tests
- `@pytest.mark.python` - Pure Python tests
- `@pytest.mark.api` - API-related tests
- `@pytest.mark.websocket` - WebSocket tests

## Coverage Verification

The `poetry run test-all` command ensures **100% test discovery** by:

1. **Explicit Path Coverage**: Every test directory is explicitly included
2. **Marker-Based Filtering**: Tests are categorized to avoid duplication
3. **Comprehensive Reporting**: Shows results for each test category
4. **Fail-Safe Design**: Fails if any test directory is missing or inaccessible

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

This ensures you have complete visibility into test coverage and execution results.