# Corridors Game Frontend

A React TypeScript frontend for the Corridors board game, featuring real-time gameplay with WebSocket communication to the MCTS backend.

## Features

- **Interactive Game Board**: Visual representation of the 9x9 Corridors board with drag-and-drop piece movement
- **Real-time Multiplayer**: WebSocket connection for live game updates
- **Game Modes**: Human vs Human, Human vs AI, and AI vs AI gameplay
- **Move History**: Complete game history with move notation
- **Connection Management**: Automatic reconnection with connection status indicators
- **Responsive Design**: Optimized for desktop and mobile devices

## Architecture

### Components

- **GameBoard** (`src/components/GameBoard.tsx`): Interactive board with piece positioning and wall placement
- **GameSettings** (`src/components/GameSettings.tsx`): Game configuration (players, difficulty, mode)
- **MoveHistory** (`src/components/MoveHistory.tsx`): Displays chronological list of game moves

### State Management

- **Zustand Store** (`src/store/gameStore.ts`): Global state management for game data, connection status, and UI state
- **WebSocket Service** (`src/services/websocket.ts`): Handles real-time communication with backend API

### Type Safety

- **Game Types** (`src/types/game.ts`): TypeScript interfaces for game state, moves, positions, and walls
- Full type coverage with strict TypeScript configuration

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Running MCTS backend server (see main README.md)
- Docker (recommended for development)

### Development Setup

**Option 1: Docker Development (Recommended)**

```bash
# Start the full development environment
cd docker
docker compose up -d

# Application will be available at http://localhost:8000
# Serves both frontend and API from single server
# WebSocket at ws://localhost:8000/ws
```

**Option 2: Local Development**

```bash
# Build frontend first
npm run build

# Start backend server (from project root)
cd ..
poetry run server

# Application available at http://localhost:8000
```

The application will be available at [http://localhost:8000](http://localhost:8000).

## Environment Configuration

The frontend now uses relative URLs and runs from the same server as the backend. No environment variables are needed for URL configuration in the single-server architecture.

## Available Scripts

### `npm start`
Runs the app in development mode with hot reloading.

### `npm test`
Launches the test runner for component and service tests.

### `npm run build`
Builds the app for production. In the Docker container, builds are created in `/opt/mcts/frontend-build/build/`.

### `npm run eject`
⚠️ **One-way operation** - Ejects from Create React App configuration.

## Backend Integration

### WebSocket Communication

The frontend connects to the backend WebSocket server for:

- **Real-time game updates**: Board state, move notifications
- **Connection status**: Automatic reconnection with exponential backoff  
- **Game events**: Start, end, player turns, moves

### REST API Endpoints

- `POST /games` - Create new game
- `GET /games/{game_id}` - Get game state
- `POST /games/{game_id}/moves` - Make a move
- `GET /health` - Backend health check

### Same-Origin Architecture

The frontend and backend run from the same server, eliminating CORS concerns. All requests are same-origin.

## Game Rules Integration

The frontend implements the complete Corridors game rules:

- **Board**: 9x9 grid with player starting positions
- **Movement**: Players can move to adjacent cells or jump over opponents  
- **Walls**: Players can place horizontal or vertical walls to block paths
- **Victory**: First player to reach the opposite side wins
- **Wall Limits**: Each player starts with 10 walls

## Testing

### Unit Tests

```bash
# Run component tests
npm test

# With coverage
npm test -- --coverage
```

### E2E Tests

End-to-end tests are located in the main project's `tests/e2e/` directory and run via Docker:

```bash
# Run E2E tests (from project root)
cd docker && docker compose up -d
docker compose exec mcts pytest tests/e2e/
```

### Test Structure

- **Component Tests**: React Testing Library for UI components
- **Service Tests**: WebSocket service and API integration
- **Integration Tests**: Full user workflows with backend
- **Mock Service Worker**: API mocking for isolated testing

## Build and Deployment

### Production Build

```bash
# Create optimized production build
npm run build

# Serve static files (example)
npx serve -s build -l 3000
```

### Docker Production

```bash
# Build production image (includes both frontend and backend)
cd docker && docker compose build

# Run container (single port for entire application)
docker compose up -d

# Application available at http://localhost:8000
```

## Development Guidelines

### Code Style

- **TypeScript**: Strict mode enabled with full type coverage
- **ESLint**: Standard React/TypeScript configuration
- **Prettier**: Automatic code formatting
- **CSS Modules**: Component-scoped styling

### Component Patterns

- **Functional Components**: React hooks for state and effects
- **Custom Hooks**: Reusable logic for WebSocket, game state
- **Type-safe Props**: All component props fully typed
- **Error Boundaries**: Graceful error handling

### Performance Considerations

- **Memoization**: React.memo for expensive re-renders
- **Code Splitting**: Lazy loading for route-based splitting
- **WebSocket Optimization**: Connection pooling and message throttling

## Troubleshooting

### Connection Issues

```bash
# Check application status (frontend and backend together)
curl http://localhost:8000/health

# Verify WebSocket endpoint
wscat -c ws://localhost:8000/ws
```

### Build Issues

```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear React scripts cache
npm start -- --reset-cache
```

### Docker Issues

```bash
# Rebuild frontend container
docker compose build frontend
docker compose up -d frontend
```

## Contributing

1. Follow existing TypeScript/React patterns
2. Add tests for new components and services
3. Update this README for new features
4. Ensure Docker development environment works
5. Test WebSocket functionality with backend

## Related Documentation

- **Main Project**: [../README.md](../README.md) - Full project setup and architecture
- **Backend API**: [../backend/api/README.md](../backend/api/README.md) - API endpoints and WebSocket events
- **Testing Guide**: [../tests/README.md](../tests/README.md) - Comprehensive testing documentation