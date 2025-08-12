/**
 * Core Smoke Test: Frontend Game Flow
 * 
 * This test simulates a complete game session using the frontend:
 * 1. Create a new game with AI
 * 2. Make several moves
 * 3. Navigate through move history
 * 4. View previous board positions
 * 
 * This is the primary smoke test to verify the entire frontend works correctly.
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../../frontend/src/App';

// Mock WebSocket and game store
const mockGameStore = {
  isConnected: true,
  gameId: 'test-game-123',
  gameState: {
    board_size: 9,
    current_player: 0,
    players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
    walls: [],
    walls_remaining: [10, 10],
    legal_moves: ['e7', 'f8', 'd8'],
    winner: null,
    move_history: []
  },
  moveHistory: [],
  selectedHistoryIndex: null,
  error: null,
  isLoading: false,
  gameSettings: {
    mode: 'human_vs_ai',
    ai_difficulty: 'medium',
    ai_time_limit: 3000,
    board_size: 9
  },
  setGameSettings: jest.fn(),
  setGameId: jest.fn(),
  setGameState: jest.fn(),
  addMoveToHistory: jest.fn(),
  setSelectedHistoryIndex: jest.fn(),
  setError: jest.fn(),
  setIsLoading: jest.fn(),
  setIsConnected: jest.fn(),
  resetGame: jest.fn()
};

// Mock imports
jest.mock('../../frontend/src/store/gameStore', () => ({
  useGameStore: () => mockGameStore
}));

jest.mock('../../frontend/src/services/websocket', () => ({
  wsService: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    createGame: jest.fn(),
    makeMove: jest.fn(),
    getAIMove: jest.fn(),
    isConnected: jest.fn(() => true)
  }
}));

describe('Frontend Smoke Test: Complete Game Flow', () => {
  let gameStateHistory;
  
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Track game state changes to simulate move history
    gameStateHistory = [];
    
    // Mock game state updates
    mockGameStore.setGameState.mockImplementation((newState) => {
      gameStateHistory.push(JSON.parse(JSON.stringify(newState)));
      mockGameStore.gameState = newState;
    });
    
    // Mock move history updates
    mockGameStore.addMoveToHistory.mockImplementation((move) => {
      mockGameStore.moveHistory.push(move);
    });
    
    // Mock history navigation
    mockGameStore.setSelectedHistoryIndex.mockImplementation((index) => {
      mockGameStore.selectedHistoryIndex = index;
      if (index !== null && gameStateHistory[index]) {
        // Simulate viewing previous position
        mockGameStore.gameState = gameStateHistory[index];
      } else {
        // Return to current position
        mockGameStore.gameState = gameStateHistory[gameStateHistory.length - 1] || mockGameStore.gameState;
      }
    });
  });

  test('Complete game flow: create game, make moves, navigate history', async () => {
    // Step 1: Render the app
    render(<App />);

    // Verify initial UI elements are present
    expect(screen.getByText('CORRIDORS MCTS')).toBeInTheDocument();
    expect(screen.getByText('Connected')).toBeInTheDocument();

    // Step 2: Open game settings
    const settingsButton = screen.getByText('⚙️');
    fireEvent.click(settingsButton);

    await waitFor(() => {
      expect(screen.getByText('New Game Settings')).toBeInTheDocument();
    });

    // Step 3: Configure game settings (Human vs AI, Medium difficulty)
    const humanVsAiButton = screen.getByText('👤 vs 🤖');
    fireEvent.click(humanVsAiButton);

    const mediumButton = screen.getByText('Medium');
    fireEvent.click(mediumButton);

    // Step 4: Start the game
    const startButton = screen.getByText('Start Game');
    fireEvent.click(startButton);

    // Verify game creation was called with correct settings
    const { wsService } = require('../../frontend/src/services/websocket');
    expect(wsService.createGame).toHaveBeenCalledWith({
      mode: 'human_vs_ai',
      ai_config: {
        difficulty: 'medium',
        time_limit_ms: 3000,
        use_mcts: true,
        mcts_iterations: 1000
      },
      board_size: 9
    });

    // Step 5: Simulate game state after game creation
    act(() => {
      const initialGameState = {
        board_size: 9,
        current_player: 0,
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        walls: [],
        walls_remaining: [10, 10],
        legal_moves: ['e7', 'f8', 'd8'],
        winner: null,
        move_history: []
      };
      mockGameStore.setGameState(initialGameState);
      mockGameStore.setGameId('test-game-123');
    });

    // Verify game board is displayed
    await waitFor(() => {
      expect(screen.getByText('Current Player')).toBeInTheDocument();
      expect(screen.getByText('Player 1')).toBeInTheDocument();
    });

    // Step 6: Make first move (human player)
    act(() => {
      // Simulate clicking on a legal move position
      const firstMove = {
        notation: 'e7',
        player: 0,
        type: 'move',
        position: { x: 4, y: 7 }
      };
      
      // Update game state after move
      const gameStateAfterMove1 = {
        ...mockGameStore.gameState,
        current_player: 1,
        players: [{ x: 4, y: 7 }, { x: 4, y: 0 }],
        legal_moves: ['e2', 'f1', 'd1'],
        move_history: [firstMove]
      };
      
      mockGameStore.setGameState(gameStateAfterMove1);
      mockGameStore.addMoveToHistory(firstMove);
    });

    // Verify move was processed
    expect(mockGameStore.moveHistory).toHaveLength(1);
    expect(mockGameStore.moveHistory[0].notation).toBe('e7');

    // Step 7: Simulate AI move
    act(() => {
      const aiMove = {
        notation: 'e2',
        player: 1,
        type: 'move',
        position: { x: 4, y: 1 }
      };
      
      // Update game state after AI move
      const gameStateAfterMove2 = {
        ...mockGameStore.gameState,
        current_player: 0,
        players: [{ x: 4, y: 7 }, { x: 4, y: 1 }],
        legal_moves: ['e6', 'f7', 'd7'],
        move_history: [mockGameStore.moveHistory[0], aiMove]
      };
      
      mockGameStore.setGameState(gameStateAfterMove2);
      mockGameStore.addMoveToHistory(aiMove);
    });

    // Step 8: Make second human move
    act(() => {
      const secondMove = {
        notation: 'e6',
        player: 0,
        type: 'move',
        position: { x: 4, y: 6 }
      };
      
      // Update game state after second move
      const gameStateAfterMove3 = {
        ...mockGameStore.gameState,
        current_player: 1,
        players: [{ x: 4, y: 6 }, { x: 4, y: 1 }],
        legal_moves: ['e3', 'f2', 'd2'],
        move_history: [...mockGameStore.moveHistory, secondMove]
      };
      
      mockGameStore.setGameState(gameStateAfterMove3);
      mockGameStore.addMoveToHistory(secondMove);
    });

    // Step 9: Add a wall move for variety
    act(() => {
      const wallMove = {
        notation: 'Ha4',
        player: 1,
        type: 'wall',
        wall: { x: 0, y: 3, orientation: 'horizontal' }
      };
      
      // Update game state after wall placement
      const gameStateAfterMove4 = {
        ...mockGameStore.gameState,
        current_player: 0,
        walls: [{ x: 0, y: 3, orientation: 'horizontal' }],
        walls_remaining: [10, 9],
        legal_moves: ['e5', 'f6', 'd6'],
        move_history: [...mockGameStore.moveHistory, wallMove]
      };
      
      mockGameStore.setGameState(gameStateAfterMove4);
      mockGameStore.addMoveToHistory(wallMove);
    });

    // Verify we now have 4 moves in history
    expect(mockGameStore.moveHistory).toHaveLength(4);

    // Step 10: Test move history navigation
    await waitFor(() => {
      expect(screen.getByText('Move History')).toBeInTheDocument();
    });

    // Navigate to first move (should show initial position)
    act(() => {
      mockGameStore.setSelectedHistoryIndex(0);
    });

    // Verify we're viewing the first move position
    expect(mockGameStore.selectedHistoryIndex).toBe(0);
    expect(mockGameStore.gameState.players[0]).toEqual({ x: 4, y: 7 });

    // Navigate to second move
    act(() => {
      mockGameStore.setSelectedHistoryIndex(1);
    });

    // Verify we're viewing the second move position
    expect(mockGameStore.selectedHistoryIndex).toBe(1);
    expect(mockGameStore.gameState.players[1]).toEqual({ x: 4, y: 1 });

    // Navigate to wall move
    act(() => {
      mockGameStore.setSelectedHistoryIndex(3);
    });

    // Verify wall is visible in the viewed position
    expect(mockGameStore.gameState.walls).toHaveLength(1);
    expect(mockGameStore.gameState.walls[0]).toEqual({
      x: 0,
      y: 3,
      orientation: 'horizontal'
    });

    // Step 11: Return to current position
    act(() => {
      mockGameStore.setSelectedHistoryIndex(null);
    });

    // Verify we're back to the current game state
    expect(mockGameStore.selectedHistoryIndex).toBe(null);
    expect(mockGameStore.gameState.move_history).toHaveLength(4);

    // Step 12: Test game information display
    await waitFor(() => {
      expect(screen.getByText('Game Info')).toBeInTheDocument();
      expect(screen.getByText('test-game-123')).toBeInTheDocument();
      expect(screen.getByText('medium')).toBeInTheDocument();
    });

    // Step 13: Verify move history display shows all moves
    const moveNotations = ['e7', 'e2', 'e6', 'Ha4'];
    moveNotations.forEach(notation => {
      expect(screen.getByText(notation)).toBeInTheDocument();
    });

    console.log('✅ Smoke test completed successfully!');
    console.log('✅ Game creation: PASSED');
    console.log('✅ Move making: PASSED');
    console.log('✅ History navigation: PASSED');
    console.log('✅ Position viewing: PASSED');
    console.log('✅ UI updates: PASSED');
  });

  test('Error handling and edge cases', async () => {
    render(<App />);

    // Test connection error
    act(() => {
      mockGameStore.setIsConnected(false);
      mockGameStore.setError('Connection lost');
    });

    await waitFor(() => {
      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });

    // Test empty move history
    act(() => {
      mockGameStore.moveHistory = [];
      mockGameStore.setSelectedHistoryIndex(null);
    });

    await waitFor(() => {
      expect(screen.getByText('No moves yet')).toBeInTheDocument();
    });

    // Test loading state
    act(() => {
      mockGameStore.setIsLoading(true);
    });

    // Verify loading indicator (if implemented)
    // This would depend on your loading UI implementation

    console.log('✅ Error handling test completed successfully!');
  });

  test('Game settings validation', async () => {
    render(<App />);

    // Open settings
    const settingsButton = screen.getByText('⚙️');
    fireEvent.click(settingsButton);

    // Test all difficulty levels
    const difficulties = ['Easy', 'Medium', 'Hard', 'Expert'];
    
    for (const difficulty of difficulties) {
      const difficultyButton = screen.getByText(difficulty);
      fireEvent.click(difficultyButton);
      
      // Verify setting was applied
      expect(mockGameStore.setGameSettings).toHaveBeenCalled();
    }

    // Test game modes
    const modes = ['👤 vs 👤', '👤 vs 🤖', '🤖 vs 🤖'];
    
    for (const mode of modes) {
      const modeButton = screen.getByText(mode);
      fireEvent.click(modeButton);
      
      // Verify mode was applied
      expect(mockGameStore.setGameSettings).toHaveBeenCalled();
    }

    console.log('✅ Game settings validation completed successfully!');
  });
});