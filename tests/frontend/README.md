# Frontend Test Suite for Corridors Game

This directory contains comprehensive tests for the React frontend of the Corridors MCTS game. The test suite covers unit tests, integration tests, and end-to-end tests to ensure the frontend works correctly in isolation and when integrated with the backend API.

## Test Structure

```
tests/frontend/
├── components/           # Component unit tests
│   ├── GameBoard.test.tsx
│   ├── GameSettings.test.tsx
│   └── MoveHistory.test.tsx
├── services/            # Service layer tests
│   └── websocket.test.ts
├── store/              # State management tests
│   └── gameStore.test.ts
├── integration/        # Integration tests
│   ├── game-flow.test.tsx
│   └── component-interactions.test.tsx
├── e2e/               # End-to-end tests
│   └── game-e2e.test.tsx
├── utils/             # Test utilities
│   └── test-utils.tsx
├── mocks/             # Mock implementations
│   ├── websocket.mock.ts
│   ├── zustand.mock.ts
│   └── fileMock.js
├── jest.config.js     # Jest configuration
├── setupTests.ts      # Test setup
├── run-tests.sh       # Test runner script
└── README.md         # This file
```

## Test Categories

### Unit Tests (`components/`, `services/`, `store/`)

Test individual components and services in isolation:

- **GameBoard Component**: Tests board rendering, player movement, wall placement, hover effects, and accessibility
- **MoveHistory Component**: Tests move display, history navigation, replay functionality, and UI interactions  
- **GameSettings Component**: Tests mode selection, AI configuration, form validation, and game creation
- **WebSocket Service**: Tests connection management, event handling, error scenarios, and API calls
- **Game Store**: Tests state management, data persistence, and state transitions

### Integration Tests (`integration/`)

Test interactions between multiple components and services:

- **Game Flow**: Tests complete user journeys from settings to gameplay
- **Component Interactions**: Tests how components communicate and share state

### End-to-End Tests (`e2e/`)

Simulate real user interactions with the complete application:

- **Complete Game Sessions**: Full gameplay scenarios with WebSocket communication
- **Error Handling**: Connection failures and server error scenarios  
- **Performance**: Tests for responsive UI under various conditions

## Running Tests

### Prerequisites

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Ensure test dependencies are installed:
```bash
npm install --save-dev @testing-library/user-event @testing-library/jest-dom jest-environment-jsdom socket.io-mock msw
```

### Test Commands

#### Run All Tests
```bash
./run-tests.sh
# or
./run-tests.sh all
```

#### Run Specific Test Categories
```bash
./run-tests.sh unit          # Unit tests only
./run-tests.sh integration   # Integration tests only  
./run-tests.sh e2e          # E2E tests only
```

#### Development Modes
```bash
./run-tests.sh watch        # Watch mode for development
./run-tests.sh coverage     # Detailed coverage report
./run-tests.sh ci          # CI mode (non-interactive)
```

#### Run Individual Test Files
```bash
cd tests/frontend
npx jest components/GameBoard.test.tsx
npx jest --testNamePattern="handles player moves"
```

## Test Configuration

### Jest Configuration (`jest.config.js`)

- **Environment**: jsdom for DOM simulation
- **Coverage**: 80% threshold for branches, functions, lines, statements
- **Transforms**: Babel for TypeScript and React JSX
- **Mocks**: CSS modules and static assets
- **Timeout**: 10s default, 30s for E2E tests

### Setup (`setupTests.ts`)

Global test setup including:
- DOM APIs mocking (clipboard, localStorage, WebSocket)
- Console error filtering
- Canvas context mocking
- Global test timeout configuration

## Mock Strategy

### WebSocket Mocking (`mocks/websocket.mock.ts`)

Provides `MockWebSocket` class that simulates:
- Connection/disconnection events
- Message sending/receiving
- Connection state management
- Event handler registration

### State Management Mocking (`mocks/zustand.mock.ts`)

Mock Zustand store with:
- State persistence across renders
- Action simulation
- State reset capabilities
- Listener management

### Utility Functions (`utils/test-utils.tsx`)

Helper functions and mock data:
- Custom render function with providers
- Mock game states for various scenarios
- User event utilities
- Async testing helpers
- Performance measurement tools

## Coverage Goals

The test suite aims for comprehensive coverage:

- **Component Rendering**: All UI states and variations
- **User Interactions**: Click, hover, keyboard navigation
- **State Changes**: All store actions and state transitions  
- **Error Scenarios**: Network failures, invalid input, edge cases
- **Accessibility**: ARIA labels, keyboard navigation, focus management
- **Performance**: Large datasets, rapid interactions, memory usage

### Current Coverage Targets

- **Branches**: 80%
- **Functions**: 80% 
- **Lines**: 80%
- **Statements**: 80%

## Writing New Tests

### Component Tests

```typescript
import { render, screen } from '../utils/test-utils';
import { MyComponent } from '../../../frontend/src/components/MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
});
```

### Service Tests

```typescript  
import { myService } from '../../../frontend/src/services/myService';

describe('MyService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  it('performs action correctly', async () => {
    const result = await myService.performAction();
    expect(result).toBe(expectedValue);
  });
});
```

### Integration Tests

```typescript
import { render } from '../utils/test-utils';
import App from '../../../frontend/src/App';

describe('Feature Integration', () => {
  it('completes user flow', async () => {
    render(<App />);
    // Test complete user journey
  });
});
```

## Best Practices

### Test Organization
- Group related tests with `describe` blocks
- Use descriptive test names that explain the scenario
- Keep tests focused and atomic
- Use setup/teardown hooks appropriately

### Assertions
- Test behavior, not implementation details
- Use semantic queries (getByRole, getByText)
- Verify user-visible outcomes
- Test error conditions and edge cases

### Performance
- Mock external dependencies
- Use fake timers for time-based tests  
- Clean up resources after tests
- Avoid testing implementation details

### Accessibility
- Test keyboard navigation
- Verify ARIA labels and roles
- Check focus management
- Test screen reader compatibility

## Debugging Tests

### Common Issues

1. **Async Operations**: Use `waitFor` for async state updates
2. **DOM Cleanup**: Ensure components unmount properly
3. **Mock Leakage**: Reset mocks between tests
4. **Timing Issues**: Use fake timers or proper async/await

### Debugging Tools

```bash
# Run with debug info
npx jest --verbose

# Run single test with logging  
npx jest MyComponent.test.tsx --verbose

# Update snapshots
npx jest --updateSnapshot
```

## Continuous Integration

The test suite is designed for CI environments:

- **CI Mode**: `./run-tests.sh ci`
- **Coverage Reports**: Generates lcov and HTML reports
- **Exit Codes**: Proper failure handling for CI systems
- **Parallel Execution**: Jest runs tests in parallel by default

## Contributing

When adding new features:

1. Write tests for new components/functions
2. Update existing tests for modified behavior
3. Ensure coverage thresholds are maintained
4. Add integration tests for new user flows
5. Update this README if test structure changes

## Troubleshooting

### Common Problems

**Tests timeout**: Increase timeout in jest.config.js or use `jest.setTimeout()`

**Mock not working**: Check mock path and ensure proper import order

**Async test failures**: Use proper async/await and waitFor patterns

**Coverage too low**: Add tests for uncovered branches and error paths

### Getting Help

1. Check Jest documentation: https://jestjs.io/docs
2. React Testing Library guides: https://testing-library.com/docs/react-testing-library/intro
3. Review existing tests for patterns and examples