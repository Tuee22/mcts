# Frontend Test Suite

This directory contains comprehensive tests for the React frontend of the Corridors MCTS game.

## 🎯 Core Smoke Test

**File:** `core-smoke-test.test.js`

This is the **primary smoke test** that validates the entire frontend game flow:

### Test Coverage

1. **Game Settings Configuration** ✅
   - Difficulty level mapping (Easy/Medium/Hard/Expert)
   - MCTS iteration settings (100/1K/5K/10K)
   - AI configuration validation

2. **Game State Management** ✅
   - Player position tracking
   - Move history management
   - Wall placement logic
   - Turn switching
   - Game state updates

3. **Move History Navigation** ✅
   - Position viewing at any point in game
   - Forward/backward navigation
   - Current position restoration
   - Move notation display

4. **Complete Game Flow** ✅
   - Game initialization
   - Move execution
   - Game completion
   - Winner determination

5. **WebSocket Service Interface** ✅
   - Connection management
   - Game creation requests
   - Move transmission
   - AI move requests

### Key Features Tested

- **Difficulty Settings**: Verifies the mapping from UI difficulty to MCTS parameters
- **Game Progression**: Simulates a complete game with multiple moves and wall placements
- **History Navigation**: Tests the ability to view any previous board position
- **State Consistency**: Ensures game state remains consistent throughout play
- **API Interface**: Validates the WebSocket service contract

### Running the Smoke Test

```bash
# Run locally
cd /Users/matthewnowak/mcts/tests/frontend
npm test core-smoke-test.test.js

# Run in Docker container
docker exec docker-mcts-1 sh -c "cd /home/mcts/tests/frontend && npm test core-smoke-test.test.js"
```

### Expected Output

```
🎮 CORE FRONTEND SMOKE TEST RESULTS:
=====================================
✅ Game settings configuration: PASSED
✅ Game state management: PASSED
✅ Move history navigation: PASSED
✅ Complete game flow: PASSED
✅ WebSocket service interface: PASSED
=====================================
🎯 All core frontend functionality is working correctly!
🚀 The frontend is ready for integration with the backend API.
```

## Test Structure

The smoke test is designed to be:
- **Self-contained**: No external dependencies
- **Fast**: Completes in under 2 seconds
- **Comprehensive**: Covers all critical frontend functionality
- **Reliable**: Uses pure JavaScript logic without complex React component mocking

## Integration

This test serves as the **primary validation** that the frontend is working correctly before deployment or integration testing.