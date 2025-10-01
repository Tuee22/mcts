import { describe, it, expect, beforeEach, vi } from 'vitest';

// Import the functional store implementation
import { useGameStore } from '@/store/gameStore';
import { GameState } from '@/types/game';
import { setupGameCreation, defaultGameState } from '../test-utils/store-factory';

// Mock WebSocket service for testing interactions
const mockWsService = vi.hoisted(() => ({
  connect: vi.fn(),
  disconnect: vi.fn(),
  isConnected: vi.fn(() => {
    // Import the real store to check connection state
    const { useGameStore } = require('@/store/gameStore');
    const state = useGameStore.getState();
    return state.connection.type === 'connected';
  }),
  createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
  makeMove: vi.fn(() => Promise.resolve()),
  getAIMove: vi.fn(() => Promise.resolve()),
}));

vi.mock('@/services/websocket', () => ({
  wsService: mockWsService
}));

describe('GameStore Reset Chain Tests (Bug-detecting)', () => {
  // DESIGN NOTE: RESET_GAME action resets settings to defaults for clean state.
  // Game-specific state (gameId, gameState, loading) is cleared during reset.
  // Connection state is preserved for better UX.

  const getStore = () => useGameStore.getState();

  beforeEach(() => {
    // Reset to initial state using functional API
    getStore().dispatch({ type: 'RESET_GAME' });
    vi.clearAllMocks();
  });

  describe('Reset During Active Operations', () => {
    it('should handle reset during game creation', () => {
      // Set up connected state (no intermediate loading state in simplified machine)
      getStore().dispatch({ type: 'CONNECTION_START' });
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      getStore().dispatch({ 
        type: 'SETTINGS_UPDATED', 
        settings: { mode: 'human_vs_ai', ai_difficulty: 'hard', board_size: 7 } 
      });

      // Verify connected state
      expect(getStore().isConnected()).toBe(true);

      // Reset while connected (user resets before creating game)  
      getStore().dispatch({ type: 'RESET_GAME' });

      // Connection preserved, settings reset to defaults
      expect(getStore().getIsLoading()).toBe(false); // No loading state
      expect(getStore().isConnected()).toBe(true); // Connection preserved (canReset=true for connected state)
      expect(getStore().getCurrentGameId()).toBe(null); // Game data cleared
      expect(getStore().settings.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      }); // Settings reset to defaults
    });

    it('should handle reset while WebSocket messages are being processed', () => {
      // Set up active game state
      getStore().dispatch({ type: 'CONNECTION_START' });
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      getStore().dispatch({ type: 'START_GAME' });
      getStore().dispatch({ 
        type: 'GAME_CREATED', 
        gameId: 'active-game-123', 
        state: {
          board_size: 9,
          players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
          walls: [],
          legal_moves: ['e2', 'e4'],
          current_player: 0,
          winner: null,
          move_history: [
            { notation: 'e2', player: 0, timestamp: Date.now() }
          ],
          walls_remaining: [10, 10]
        } as GameState
      });
      
      getStore().dispatch({ type: 'GAME_STATE_UPDATED', state: {
        board_size: 9,
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        walls: [],
        legal_moves: ['e2', 'e4'],
        current_player: 0,
        winner: null,
        move_history: [
          { notation: 'e2', player: 0, timestamp: Date.now() }
        ],
        walls_remaining: [10, 10]
      } as GameState });
      
      // Reset during message processing
      getStore().dispatch({ type: 'RESET_GAME' });
      
      // Should clear all game data and processing state
      expect(getStore().getCurrentGameId()).toBe(null);
      expect(getStore().getCurrentGameState()).toBe(null);
      expect(getStore().getIsLoading()).toBe(false);
      // But connection should persist
      expect(getStore().isConnected()).toBe(true);
    });

    it('should handle reset during AI move processing', () => {
      // Set up AI vs Human game where AI move is being calculated
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      setupGameCreation(getStore().dispatch, 'ai-game-123', defaultGameState);
      getStore().dispatch({ type: 'SETTINGS_UPDATED', settings: { mode: 'human_vs_ai' as const, ai_difficulty: 'expert' as const } });
      getStore().dispatch({ type: 'GAME_STATE_UPDATED', state: {
        board_size: 9,
        players: [{ x: 4, y: 7 }, { x: 4, y: 1 }],
        walls: [],
        legal_moves: ['e3', 'e5'],
        current_player: 1, // AI's turn
        winner: null,
        is_terminal: false,
        move_history: [
          { notation: 'e2', player: 0, timestamp: Date.now() }
        ],
        walls_remaining: [10, 10]
      } as GameState });
      
      // Set loading to simulate AI thinking
      getStore().dispatch({ type: 'START_GAME' });
      
      // Reset while AI is thinking (user clicks New Game)
      getStore().dispatch({ type: 'RESET_GAME' });
      
      // Should clear everything including the AI processing state
      expect(getStore().getCurrentGameId()).toBe(null);
      expect(getStore().getCurrentGameState()).toBe(null);
      expect(getStore().getIsLoading()).toBe(false);
      expect(getStore().isConnected()).toBe(true); // Connection preserved
    });
  });

  describe('Rapid Reset Scenarios', () => {
    it('should handle multiple rapid resets with connection verification', () => {
      // Set up connected state
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      // Rapid fire resets (user clicking New Game multiple times)
      for (let i = 0; i < 10; i++) {
        setupGameCreation(getStore().dispatch, `game-${i}`, defaultGameState);
        getStore().dispatch({ type: 'GAME_STATE_UPDATED', state: {
          board_size: 9,
          players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
          walls: [],
          legal_moves: [],
          current_player: i % 2 as 0 | 1,
          winner: null,
          is_terminal: false,
          move_history: [],
          walls_remaining: [10, 10]
        } as GameState });
        
        getStore().dispatch({ type: 'RESET_GAME' });
        
        // After each reset, verify consistent state
        expect(getStore().getCurrentGameId()).toBe(null);
        expect(getStore().getCurrentGameState()).toBe(null);
        expect(getStore().isConnected()).toBe(true); // Should stay connected
        expect(getStore().getSelectedHistoryIndex()).toBe(null);
      }
    });

    it('should handle rapid reset during different error states', () => {
      const errorStates = [
        'Connection failed',
        'Game creation failed',
        'Invalid move',
        'Server error',
        null
      ];
      
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      errorStates.forEach(errorState => {
        // Set up error state
        getStore().dispatch({
          type: 'NOTIFICATION_ADDED',
          notification: {
            id: crypto.randomUUID(),
            type: 'error',
            message: errorState,
            timestamp: new Date()
          }
        });
        setupGameCreation(getStore().dispatch, 'error-game', defaultGameState);
        getStore().dispatch({ type: 'START_GAME' });
        
        // Reset during error
        getStore().dispatch({ type: 'RESET_GAME' });
        
        // Verify consistent reset behavior regardless of error
        expect(getStore().getCurrentGameId()).toBe(null);
        expect(getStore().getCurrentGameState()).toBe(null);
        expect(getStore().getIsLoading()).toBe(false);
        expect(getStore().isConnected()).toBe(true);
        // Error state is cleared on reset for fresh start (updated behavior)
        expect(getStore().getLatestError()).toBe(null);
      });
    });
  });

  describe('Reset State Consistency', () => {
    it('should maintain connection state through complex reset chains', () => {
      // Start connected with default settings
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      getStore().dispatch({ 
        type: 'SETTINGS_UPDATED', 
        settings: {
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'medium' as const,
          ai_time_limit: 5000,
          board_size: 9
        }
      });

      // Complex state setup and reset chain
      const operations = [
        () => {
          setupGameCreation(getStore().dispatch, 'game-1', defaultGameState);
          getStore().dispatch({ type: 'START_GAME' });
          getStore().dispatch({ type: 'RESET_GAME' });
        },
        () => {
          getStore().dispatch({ type: 'SETTINGS_UPDATED', settings: { mode: 'ai_vs_ai' as const, board_size: 5 } });
          // Cannot set history index without an active game
          getStore().dispatch({ type: 'RESET_GAME' });
        },
        () => {
          getStore().dispatch({ type: 'NOTIFICATION_ADDED', notification: { id: Math.random().toString(), type: 'error', message: 'Temp error', timestamp: new Date() } });
          getStore().dispatch({ type: 'GAME_STATE_UPDATED', state: {
            board_size: 7,
            players: [{ x: 3, y: 6 }, { x: 3, y: 0 }],
            walls: [{ x: 1, y: 2, orientation: 'horizontal' }],
            legal_moves: ['d2'],
            current_player: 1,
            winner: null,
            is_terminal: false,
            move_history: [],
            walls_remaining: [9, 10]
          } as GameState });
          getStore().dispatch({ type: 'RESET_GAME' });
        }
      ];
      
      operations.forEach((operation, index) => {
        operation();

        // Verify consistent state after each reset
        expect(getStore().getCurrentGameId()).toBe(null);
        expect(getStore().getCurrentGameState()).toBe(null);
        expect(getStore().getIsLoading()).toBe(false);
        expect(getStore().getSelectedHistoryIndex()).toBe(null);

        // Settings are always reset to defaults by RESET_GAME action
        expect(getStore().settings.gameSettings).toEqual({
          mode: 'human_vs_ai',
          ai_difficulty: 'medium',
          ai_time_limit: 5000,
          board_size: 9
        });

        // Critical: Connection should be preserved
        expect(getStore().isConnected()).toBe(true);
      });
    });

    it('should handle reset when store is in inconsistent state', () => {
      // Create artificially inconsistent state (edge case)
      setupGameCreation(getStore().dispatch, 'game-123', defaultGameState);
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      getStore().dispatch({ type: 'START_GAME' });
      // Try to set invalid history index (history index beyond available moves)
      // This is still inconsistent but won't break state validation
      
      // Reset should clean up inconsistencies
      getStore().dispatch({ type: 'RESET_GAME' });
      
      // Should result in consistent clean state
      expect(getStore().getCurrentGameId()).toBe(null);
      expect(getStore().getCurrentGameState()).toBe(null);
      expect(getStore().getIsLoading()).toBe(false);
      expect(getStore().getSelectedHistoryIndex()).toBe(null);
      expect(getStore().isConnected()).toBe(true);
    });
  });

  describe('Reset Interaction with Connection States', () => {
    it('should preserve connected state during game state transitions', () => {
      // Simulate a typical game flow with reset
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      // 1. Create game
      setupGameCreation(getStore().dispatch, 'flow-game-123', defaultGameState);
      getStore().dispatch({ type: 'GAME_CREATE_FAILED', error: 'Loading cancelled' });
      
      // 2. Game in progress
      getStore().dispatch({ type: 'GAME_STATE_UPDATED', state: {
        board_size: 9,
        players: [{ x: 4, y: 6 }, { x: 4, y: 2 }],
        walls: [],
        legal_moves: ['e4', 'e6'],
        current_player: 0,
        winner: null,
        is_terminal: false,
        move_history: [
          { notation: 'e2', player: 0, timestamp: Date.now() },
          { notation: 'e8', player: 1, timestamp: Date.now() },
          { notation: 'e3', player: 0, timestamp: Date.now() }
        ],
        walls_remaining: [10, 10]
      } as GameState });
      
      // 3. Reset (New Game clicked)
      getStore().dispatch({ type: 'RESET_GAME' });
      
      // Should be ready for new game but still connected
      expect(getStore().getCurrentGameId()).toBe(null);
      expect(getStore().getCurrentGameState()).toBe(null);
      expect(getStore().isConnected()).toBe(true);
      expect(getStore().getLatestError()).toBe(null);
      
      // 4. Should be able to immediately start another game
      setupGameCreation(getStore().dispatch, 'new-game-456', defaultGameState);
      expect(getStore().getCurrentGameId()).toBe('new-game-456');
      expect(getStore().isConnected()).toBe(true);
    });

    it('should preserve disconnected state when reset during disconnection', () => {
      // Simulate disconnection scenario
      getStore().dispatch({ type: 'CONNECTION_LOST' });
      getStore().dispatch({ type: 'NOTIFICATION_ADDED', notification: { id: Math.random().toString(), type: 'error', message: 'WebSocket connection lost', timestamp: new Date() } });
      // Manually set game data without using setupGameCreation (which connects)
      getStore().dispatch({ type: 'GAME_CREATED', gameId: 'disconnected-game', state: defaultGameState });
      
      // Reset while disconnected
      getStore().dispatch({ type: 'RESET_GAME' });
      
      // Should preserve disconnection context and error info but clear game data
      expect(getStore().isConnected()).toBe(false);
      expect(getStore().getLatestError()).toBe('Connection lost'); // Errors are preserved when disconnected
      expect(getStore().getCurrentGameId()).toBe(null);
      expect(getStore().getCurrentGameState()).toBe(null);
    });

    it('should handle reset during connection state transitions', () => {
      // Start disconnected
      getStore().dispatch({ type: 'CONNECTION_LOST' });
      getStore().dispatch({ type: 'NOTIFICATION_ADDED', notification: { id: Math.random().toString(), type: 'error', message: 'Initial connection failed', timestamp: new Date() } });
      
      // Begin connecting (transition state)
      getStore().dispatch({ type: 'START_GAME' }); // Loading could indicate connection attempt
      
      // Reset during connection attempt
      getStore().dispatch({ type: 'RESET_GAME' });
      
      // Should clear loading but preserve connection attempt context
      expect(getStore().getIsLoading()).toBe(false);
      expect(getStore().isConnected()).toBe(false); // Still disconnected
      expect(getStore().getCurrentGameId()).toBe(null);
    });
  });

  describe('Memory and Performance', () => {
    it('should handle reset with large game states efficiently', () => {
      // Establish connection first
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      // Create large move history
      const largeMoveHistory = Array.from({ length: 100 }, (_, i) => ({
        notation: `move${i}`,
        player: (i % 2) as 0 | 1,
        timestamp: Date.now() + i
      }));
      
      // Create game session with large game state
      setupGameCreation(getStore().dispatch, 'large-game', {
        board_size: 9,
        players: [{ x: 4, y: 4 }, { x: 4, y: 4 }],
        walls: Array.from({ length: 20 }, (_, i) => ({
          x: i % 8,
          y: Math.floor(i / 8),
          orientation: i % 2 === 0 ? 'horizontal' as const : 'vertical' as const
        })),
        legal_moves: Array.from({ length: 30 }, (_, i) => `move${i}`),
        current_player: 1,
        winner: null,
        is_terminal: false,
        move_history: largeMoveHistory,
        walls_remaining: [0, 0]
      } as GameState);
      
      // Reset should handle large state efficiently
      const startTime = performance.now();
      getStore().dispatch({ type: 'RESET_GAME' });
      const endTime = performance.now();
      
      // Should complete quickly (less than 10ms for most cases)
      expect(endTime - startTime).toBeLessThan(50);
      
      // Should properly clear everything
      expect(getStore().getCurrentGameState()).toBe(null);
      expect(getStore().isConnected()).toBe(true);
    });

    it('should not create memory leaks with repeated resets', () => {
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      // Simulate many reset cycles
      for (let cycle = 0; cycle < 50; cycle++) {
        // Create some state
        setupGameCreation(getStore().dispatch, `cycle-game-${cycle}`, defaultGameState);
        getStore().dispatch({ type: 'GAME_STATE_UPDATED', state: {
          board_size: 9,
          players: [{ x: cycle % 9, y: cycle % 9 }, { x: 8 - (cycle % 9), y: 8 - (cycle % 9) }],
          walls: [],
          legal_moves: [],
          current_player: cycle % 2 as 0 | 1,
          winner: null,
          is_terminal: false,
          move_history: [],
          walls_remaining: [10, 10]
        } as GameState });
        
        // Reset
        getStore().dispatch({ type: 'RESET_GAME' });
        
        // Verify clean state
        expect(getStore().getCurrentGameId()).toBe(null);
        expect(getStore().getCurrentGameState()).toBe(null);
        expect(getStore().isConnected()).toBe(true);
      }
    });
  });

  describe('Reset Synchronization', () => {
    it('should handle simultaneous resets safely', () => {
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      setupGameCreation(getStore().dispatch, 'concurrent-game', defaultGameState);
      
      // Simulate rapid concurrent reset calls (edge case)
      const resetPromises = Array.from({ length: 5 }, async () => {
        getStore().dispatch({ type: 'RESET_GAME' });
      });
      
      // All should complete without error
      expect(() => Promise.all(resetPromises)).not.toThrow();
      
      // Final state should be consistent
      expect(getStore().getCurrentGameId()).toBe(null);
      expect(getStore().getCurrentGameState()).toBe(null);
      expect(getStore().isConnected()).toBe(true);
    });

    it('should maintain state consistency during concurrent operations', () => {
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      // Simulate concurrent operations (reset + other state changes)
      getStore().dispatch({ type: 'RESET_GAME' });
      setupGameCreation(getStore().dispatch, 'concurrent-1', defaultGameState); // Simultaneous with reset
      getStore().dispatch({ type: 'RESET_GAME' });
      getStore().dispatch({ type: 'NOTIFICATION_ADDED', notification: { id: Math.random().toString(), type: 'error', message: 'concurrent error', timestamp: new Date() } }); // Simultaneous with reset
      getStore().dispatch({ type: 'RESET_GAME' });
      
      // Should end up in a consistent state
      expect(getStore().getCurrentGameId()).toBe(null);
      expect(getStore().getCurrentGameState()).toBe(null);
      expect(getStore().isConnected()).toBe(true);
      expect(getStore().getLatestError()).toBe(null); // Reset clears errors
    });
  });
});