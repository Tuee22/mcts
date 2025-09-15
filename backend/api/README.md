# Corridors Game API

A comprehensive FastAPI-based REST API for the Corridors board game with Monte Carlo Tree Search (MCTS) AI support. The API supports player vs player, player vs machine, and machine vs machine game modes with real-time updates via WebSockets.

## Features

### Game Modes
- **Player vs Player (PvP)**: Human players compete against each other
- **Player vs Machine (PvM)**: Human player against MCTS AI
- **Machine vs Machine (MvM)**: Two AI agents compete (useful for testing/analysis)

### Core Capabilities
- **Stateful Game Management**: Persistent game sessions with move history
- **MCTS AI Integration**: Configurable AI with various MCTS parameters
- **Real-time Updates**: WebSocket support for live game state updates
- **Position Analysis**: AI-powered position evaluation and move suggestions
- **Matchmaking System**: Queue-based matchmaking for PvP games
- **Move Validation**: Server-side validation of all moves

## Architecture

### Components

1. **FastAPI Server** (`server.py`)
   - RESTful endpoints for game management
   - WebSocket endpoints for real-time communication
   - Comprehensive error handling and validation

2. **Game Manager** (`game_manager.py`)
   - Manages game sessions and state
   - Integrates with MCTS C++ backend
   - Handles AI move processing
   - Implements game rules and validation

3. **WebSocket Manager** (`websocket_manager.py`)
   - Manages WebSocket connections
   - Broadcasts game events to connected clients
   - Handles connection lifecycle

4. **Data Models** (`models.py`)
   - Pydantic models for request/response validation
   - Game state representation
   - Player and move tracking

## API Endpoints

### Game Management

#### Create Game
```http
POST /games
{
  "player1_type": "human",
  "player2_type": "machine",
  "player1_name": "Alice",
  "player2_name": "AI Bot",
  "settings": {
    "mcts_settings": {
      "min_simulations": 10000,
      "use_puct": false
    }
  }
}
```

#### Get Game State
```http
GET /games/{game_id}
```

#### List Games
```http
GET /games?status=in_progress&player_id=xxx
```

### Game Play

#### Make Move
```http
POST /games/{game_id}/moves
{
  "player_id": "player-uuid",
  "action": "*(4,1)"  // Move to position (4,1)
}
```

Move format:
- `*(X,Y)`: Move token to position (X,Y)
- `H(X,Y)`: Place horizontal wall at intersection (X,Y)
- `V(X,Y)`: Place vertical wall at intersection (X,Y)

#### Get Legal Moves
```http
GET /games/{game_id}/legal-moves
```

#### Get Board Display
```http
GET /games/{game_id}/board?flip=false
```

### AI Analysis

#### Analyze Position
```http
GET /games/{game_id}/analysis?depth=10000
```

#### Get Move Hint
```http
POST /games/{game_id}/hint
{
  "player_id": "player-uuid",
  "simulations": 5000
}
```

### WebSocket Connection

Connect to receive real-time updates:
```javascript
ws://localhost:8000/games/{game_id}/ws
```

Message types:
- `move`: Move notification
- `game_state`: Full game state update
- `player_connected/disconnected`: Connection events
- `game_ended`: Game completion notification

## Installation & Setup

### Prerequisites
- Python 3.12+
- C++ compiler with C++11 support

### Installation

1. Build the C++ MCTS library:
```bash
cd backend/core
scons
```

2. Install Python dependencies with Poetry:
```bash
poetry install
```

3. Run the server:
```bash
# Development mode with auto-reload
poetry run api-dev

# Or production mode
poetry run api-server

# Or using uvicorn directly
poetry run uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

## Configuration

### MCTS Settings

Configure AI behavior through `MCTSSettings`:

- `c`: Exploration parameter (default: 0.158)
- `min_simulations`: Minimum simulations before move (default: 10000)
- `max_simulations`: Maximum simulations cap (default: 10000)
- `use_rollout`: Use random rollouts vs heuristic evaluation
- `use_puct`: Use AlphaZero-style PUCT formula
- `decide_using_visits`: Choose moves by visit count vs value

### Game Settings

- `time_limit_seconds`: Optional time control per player
- `allow_hints`: Enable/disable hint requests
- `allow_analysis`: Enable/disable position analysis

## Usage Examples

### Start a PvP Game
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/games",
        json={
            "player1_type": "human",
            "player2_type": "human",
            "player1_name": "Alice",
            "player2_name": "Bob"
        }
    )
    game = response.json()
    game_id = game["game_id"]
```

### Make a Move
```python
response = await client.post(
    f"http://localhost:8000/games/{game_id}/moves",
    json={
        "player_id": player_id,
        "action": "*(4,1)"
    }
)
```

### WebSocket Client
```python
import websockets
import json

async with websockets.connect(f"ws://localhost:8000/games/{game_id}/ws") as ws:
    # Receive initial state
    message = await ws.recv()
    state = json.loads(message)
    
    # Listen for updates
    async for message in ws:
        data = json.loads(message)
        if data["type"] == "move":
            print(f"Move made: {data['data']['move']['action']}")
```

## Testing

### Unit Tests
```bash
poetry run pytest tests/test_api.py
```

### Load Testing
```bash
locust -f tests/load_test.py --host http://localhost:8000
```

## Production Deployment

### Docker
```dockerfile
FROM python:3.12
# Build C++ components
# Install Python dependencies
# Run with gunicorn/uvicorn
```

### Scaling Considerations
- Use Redis for session storage in multi-instance deployments
- Implement connection pooling for database
- Use message queue for AI move processing
- Deploy behind reverse proxy (nginx/traefik)

## Security

- Input validation on all endpoints
- Rate limiting for API calls
- Authentication/authorization (implement as needed)
- CORS configuration for web clients
- WebSocket origin validation

## Monitoring

- Health check endpoint: `GET /health`
- Metrics: Active games, connected clients
- Logging: Structured logging with appropriate levels
- OpenTelemetry support (optional)

## License

See main project LICENSE file.