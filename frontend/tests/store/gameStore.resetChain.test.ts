import { describe, it, expect, beforeEach, vi } from 'vitest';

// Import the actual implementation to test real behavior
import { useGameStore } from '@/store/gameStore';
import { setupGameCreation, defaultGameState } from '../test-utils/store-factory';
import { GameState } from '@/types/game';

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
  // DESIGN NOTE: reset() preserves user settings by design for better UX.
  // Users expect their game mode/difficulty preferences to persist when starting new games.
  // Only game-specific state (gameId, gameState, loading) is cleared during reset.

  const getStore = () => useGameStore.getState();

  beforeEach(() => {
    // Reset to initial state
    getStore().reset();
    vi.clearAllMocks();
  });

  describe('Reset During Active Operations', () => {
    it('should handle reset during game creation (loading state)', () => {
      // Set up loading state as if game creation is in progress
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      getStore().dispatch({ type: 'START_GAME' });
      getStore().setGameSettings({ mode: 'human_vs_ai', ai_difficulty: 'hard', board_size: 7 });

      // Verify loading state
      expect(getStore().isLoading).toBe(true);
      expect(getStore().isConnected()).toBe(true);

      // Reset during loading (user clicks New Game while creation in progress)
      getStore().reset();

      // Loading should be cleared, connection preserved per new functional design
      expect(getStore().isLoading).toBe(false); // Loading cleared
      expect(getStore().isConnected()).toBe(true); // Connection preserved (canReset=true for connected state)
      expect(getStore().gameId).toBe(null); // Game data cleared
      expect(getStore().settings.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'hard',
        ai_time_limit: 5000,
        board_size: 7
      }); // Settings preserved during reset (by design for UX)
    });

    it('should handle reset while WebSocket messages are being processed', () => {
      // Set up active game state
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      setupGameCreation(getStore().dispatch, 'active-game-123', defaultGameState);
      getStore().dispatch({ type: 'GAME_STATE_UPDATED', state: {
        board_size: 9,
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        walls: [],
        legal_moves: ['e2', 'e4'],
        current_player: 0,
        winner: null,
        is_terminal: false,
        move_history: [
          { notation: 'e2', player: 0, timestamp: Date.now() }
        ],
        walls_remaining: [10, 10]
      } as GameState });
      
      // Simulate WebSocket message processing (like receiving game state updates)
      getStore().dispatch({ type: 'START_GAME' }); // Simulating processing state
      
      // Reset during message processing
      getStore().reset();
      
      // Should clear all game data and processing state
      expect(getStore().gameId).toBe(null);
      expect(getStore().gameState).toBe(null);
      expect(getStore().isLoading).toBe(false);
      // But connection should persist
      expect(getStore().isConnected()).toBe(true);
    });

    it('should handle reset during AI move processing', () => {
      // Set up AI vs Human game where AI move is being calculated
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      setupGameCreation(getStore().dispatch, 'ai-game-123', defaultGameState);
      getStore().setGameSettings({ mode: 'human_vs_ai', ai_difficulty: 'expert' });
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
      getStore().reset();
      
      // Should clear everything including the AI processing state
      expect(getStore().gameId).toBe(null);
      expect(getStore().gameState).toBe(null);
      expect(getStore().isLoading).toBe(false);
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
        
        getStore().reset();
        
        // After each reset, verify consistent state
        expect(getStore().gameId).toBe(null);
        expect(getStore().gameState).toBe(null);
        expect(getStore().isConnected()).toBe(true); // Should stay connected
        expect(getStore().selectedHistoryIndex).toBe(null);
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
        getStore().setError(errorState);
        setupGameCreation(getStore().dispatch, 'error-game', defaultGameState);
        getStore().dispatch({ type: 'START_GAME' });
        
        // Reset during error
        getStore().reset();
        
        // Verify consistent reset behavior regardless of error
        expect(getStore().gameId).toBe(null);
        expect(getStore().gameState).toBe(null);
        expect(getStore().isLoading).toBe(false);
        expect(getStore().isConnected()).toBe(true);
        // Error state is cleared on reset for fresh start (updated behavior)
        expect(getStore().error).toBe(null);
      });
    });
  });

  describe('Reset State Consistency', () => {
    it('should maintain connection state through complex reset chains', () => {
      // Start connected with default settings
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      getStore().setGameSettings({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      });

      // Complex state setup and reset chain
      const operations = [
        () => {
          setupGameCreation(getStore().dispatch, 'game-1', defaultGameState);
          getStore().dispatch({ type: 'START_GAME' });
          getStore().reset();
        },
        () => {
          getStore().setGameSettings({ mode: 'ai_vs_ai', board_size: 5 });
          // Cannot set history index without an active game
          getStore().reset();
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
          getStore().reset();
        }
      ];
      
      operations.forEach((operation, index) => {
        operation();

        // Verify consistent state after each reset
        expect(getStore().gameId).toBe(null);
        expect(getStore().gameState).toBe(null);
        expect(getStore().isLoading).toBe(false);
        expect(getStore().selectedHistoryIndex).toBe(null);

        // Settings expectations change based on which operation was run
        if (index === 0) {
          // After operation 1: no settings changes, should be defaults
          expect(getStore().settings.gameSettings).toEqual({
            mode: 'human_vs_ai',
            ai_difficulty: 'medium',
            ai_time_limit: 5000,
            board_size: 9
          });
        } else {
          // After operations 2 & 3: settings were changed in operation 2 and preserved
          expect(getStore().settings.gameSettings).toEqual({
            mode: 'ai_vs_ai',
            ai_difficulty: 'medium',
            ai_time_limit: 5000,
            board_size: 5
          });
        }

        // Critical: Connection should be preserved
        expect(getStore().isConnected()).toBe(true);
      });
    });

    it('should handle reset when store is in inconsistent state', () => {
      // Create artificially inconsistent state (edge case)
      setupGameCreation(getStore().dispatch, 'game-123', defaultGameState);
      getStore().dispatch({ type: 'GAME_STATE_UPDATED', state: null }); // Game ID without state
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      getStore().dispatch({ type: 'START_GAME' });
      getStore().dispatch({ type: 'HISTORY_INDEX_SET', index: 5 }); // History index without game state
      
      // Reset should clean up inconsistencies
      getStore().reset();
      
      // Should result in consistent clean state
      expect(getStore().gameId).toBe(null);
      expect(getStore().gameState).toBe(null);
      expect(getStore().isLoading).toBe(false);
      expect(getStore().selectedHistoryIndex).toBe(null);
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
      getStore().reset();
      
      // Should be ready for new game but still connected
      expect(getStore().gameId).toBe(null);
      expect(getStore().gameState).toBe(null);
      expect(getStore().isConnected()).toBe(true);
      expect(getStore().error).toBe(null);
      
      // 4. Should be able to immediately start another game
      setupGameCreation(getStore().dispatch, 'new-game-456', defaultGameState);
      expect(getStore().gameId).toBe('new-game-456');
      expect(getStore().isConnected()).toBe(true);
    });

    it('should preserve disconnected state when reset during disconnection', () => {
      // Simulate disconnection scenario
      getStore().dispatch({ type: 'CONNECTION_LOST' });
      getStore().dispatch({ type: 'NOTIFICATION_ADDED', notification: { id: Math.random().toString(), type: 'error', message: 'WebSocket connection lost', timestamp: new Date() } });
      setupGameCreation(getStore().dispatch, 'disconnected-game', defaultGameState);
      
      // Reset while disconnected
      getStore().reset();
      
      // Should preserve disconnection context but clear game data and errors
      expect(getStore().isConnected()).toBe(false);
      expect(getStore().error).toBe(null); // Errors are cleared on reset
      expect(getStore().gameId).toBe(null);
      expect(getStore().gameState).toBe(null);
    });

    it('should handle reset during connection state transitions', () => {
      // Start disconnected
      getStore().dispatch({ type: 'CONNECTION_LOST' });
      getStore().dispatch({ type: 'NOTIFICATION_ADDED', notification: { id: Math.random().toString(), type: 'error', message: 'Initial connection failed', timestamp: new Date() } });
      
      // Begin connecting (transition state)
      getStore().dispatch({ type: 'START_GAME' }); // Loading could indicate connection attempt
      
      // Reset during connection attempt
      getStore().reset();
      
      // Should clear loading but preserve connection attempt context
      expect(getStore().isLoading).toBe(false);
      expect(getStore().isConnected()).toBe(false); // Still disconnected
      expect(getStore().gameId).toBe(null);
    });
  });

  describe('Memory and Performance', () => {
    it('should handle reset with large game states efficiently', () => {
      // Create large move history
      const largeMoveHistory = Array.from({ length: 100 }, (_, i) => ({
        notation: `move${i}`,
        player: (i % 2) as 0 | 1,
        timestamp: Date.now() + i
      }));
      
      // Create game state with large history
      getStore().dispatch({ type: 'GAME_STATE_UPDATED', state: {
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
      } as GameState });
      
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      // Reset should handle large state efficiently
      const startTime = performance.now();
      getStore().reset();
      const endTime = performance.now();
      
      // Should complete quickly (less than 10ms for most cases)
      expect(endTime - startTime).toBeLessThan(50);
      
      // Should properly clear everything
      expect(getStore().gameState).toBe(null);
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
        getStore().reset();
        
        // Verify clean state
        expect(getStore().gameId).toBe(null);
        expect(getStore().gameState).toBe(null);
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
        getStore().reset();
      });
      
      // All should complete without error
      expect(() => Promise.all(resetPromises)).not.toThrow();
      
      // Final state should be consistent
      expect(getStore().gameId).toBe(null);
      expect(getStore().gameState).toBe(null);
      expect(getStore().isConnected()).toBe(true);
    });

    it('should maintain state consistency during concurrent operations', () => {
      getStore().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      // Simulate concurrent operations (reset + other state changes)
      getStore().reset();
      setupGameCreation(getStore().dispatch, 'concurrent-1', defaultGameState); // Simultaneous with reset
      getStore().reset();
      getStore().dispatch({ type: 'NOTIFICATION_ADDED', notification: { id: Math.random().toString(), type: 'error', message: 'concurrent error', timestamp: new Date() } }); // Simultaneous with reset
      getStore().reset();
      
      // Should end up in a consistent state
      expect(getStore().gameId).toBe(null);
      expect(getStore().gameState).toBe(null);
      expect(getStore().isConnected()).toBe(true);
      expect(getStore().error).toBe(null); // Reset clears errors
    });
  });
});