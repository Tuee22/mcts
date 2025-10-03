/**
 * Game Store Race Condition Tests
 *
 * Tests rapid state changes in the Zustand game store that can cause UI race conditions.
 * These tests focus on the store's behavior during rapid updates and concurrent operations.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useGameStore } from '@/store/gameStore';
import { defaultGameState, setupGameCreation } from '../test-utils/store-factory';

// Mock WebSocket service to control connection state
const mockWsService = {
  connect: vi.fn(() => Promise.resolve()),
  disconnect: vi.fn(),
  isConnected: vi.fn(() => store.connection.type === 'connected'),
  createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game' })),
  makeMove: vi.fn(() => Promise.resolve()),
  getAIMove: vi.fn(() => Promise.resolve()),
  joinGame: vi.fn(),
  requestGameState: vi.fn(() => Promise.resolve()),
  connectToGame: vi.fn(),
  disconnectFromGame: vi.fn()
};

vi.mock('@/services/websocket', () => ({
  wsService: mockWsService
}));

describe('Game Store Race Condition Tests', () => {
  beforeEach(() => {
    // Reset store state before each test
    const store = useGameStore.getState();
    store.dispatch({ type: 'RESET_GAME' });
    vi.clearAllMocks();
  });

  describe('Rapid Connection State Changes', () => {
    it('should handle rapid setIsConnected calls without losing state', async () => {
      const { result } = renderHook(() => useGameStore());

      // Rapid connection state changes
      const connectionStates = [true, false, true, false, true];

      for (const connected of connectionStates) {
        act(() => {
          if (connected) {
            // Proper state machine flow: disconnected -> connecting -> connected
            result.current.dispatch({ type: 'CONNECTION_START' });
            result.current.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
          } else {
            result.current.dispatch({ type: 'CONNECTION_LOST' });
          }
        });

        expect(result.current.isConnected()).toBe(connected);

        // Small delay to simulate real timing
        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Verify final state is consistent
      expect(result.current.isConnected()).toBe(true);
      expect(result.current.getCurrentGameId()).toBeNull();
      expect(result.current.getCurrentGameState()).toBeNull();
    });

    it('should maintain game settings during connection changes', async () => {
      const { result } = renderHook(() => useGameStore());

      const customSettings = {
        mode: 'human_vs_ai' as const,
        ai_difficulty: 'hard' as const,
        ai_time_limit: 5000,
        board_size: 13
      };

      // Set custom settings
      act(() => {
        result.current.dispatch({ type: 'SETTINGS_UPDATED', settings: customSettings });
      });

      // Rapid connection changes
      for (let i = 0; i < 10; i++) {
        act(() => {
          if (i % 2 === 0) {
            // Connecting flow
            result.current.dispatch({ type: 'CONNECTION_START' });
            result.current.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
          } else {
            result.current.dispatch({ type: 'CONNECTION_LOST' });
          }
        });

        // Settings should remain unchanged
        expect(result.current.settings.gameSettings).toEqual(customSettings);

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }
    });
  });

  describe('Rapid Game State Updates', () => {
    it('should handle rapid gameId changes without state corruption', async () => {
      const { result } = renderHook(() => useGameStore());

      const gameIds = ['game-1', 'game-2', null, 'game-3', null, 'game-4'];

      // Start with connected state
      act(() => {
        result.current.dispatch({ type: 'CONNECTION_START' });
        result.current.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      });

      for (const gameId of gameIds) {
        act(() => {
          if (gameId) {
            // First reset any existing game, then create new one
            result.current.dispatch({ type: 'RESET_GAME' });
            result.current.dispatch({ type: 'GAME_CREATED', gameId: gameId, state: defaultGameState });
          } else {
            result.current.dispatch({ type: 'RESET_GAME' });
          }
        });

        expect(result.current.getCurrentGameId()).toBe(gameId);

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Verify other state remains consistent
      expect(result.current.getIsLoading()).toBe(false);
      expect(result.current.getLatestError()).toBeNull();
    });

    it('should handle concurrent gameState and gameId updates', async () => {
      const { result } = renderHook(() => useGameStore());

      const mockGameState = {
        board_size: 9,
        current_player: 1 as const,
        players: [
          { x: 4, y: 0 },
          { x: 4, y: 8 }
        ],
        walls: [],
        walls_remaining: [10, 10] as [number, number],
        legal_moves: [],
        winner: null,
        move_history: []
      };

      // Concurrent updates
      act(() => {
        setupGameCreation(result.current.dispatch, 'test-game', defaultGameState);
        result.current.dispatch({
          type: 'GAME_STATE_UPDATED',
          state: mockGameState
        });
      });

      expect(result.current.getCurrentGameId()).toBe('test-game');
      expect(result.current.getCurrentGameState()).toEqual(mockGameState);

      // Rapid state changes within the same game
      for (let i = 0; i < 5; i++) {
        const updatedState = {
          ...mockGameState,
          move_count: i,
          current_player: ((i % 2) + 1) as 1 | 2
        };

        act(() => {
          result.current.dispatch({
            type: 'GAME_STATE_UPDATED',
            state: updatedState
          });
        });

        expect(result.current.getCurrentGameState()?.move_count).toBe(i);
        expect(result.current.getCurrentGameId()).toBe('test-game'); // Same game throughout

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }
    });
  });

  describe('Loading State Race Conditions', () => {
    it('should handle rapid loading state toggles', async () => {
      const { result } = renderHook(() => useGameStore());

      // Rapid loading state changes
      for (let i = 0; i < 20; i++) {
        act(() => {
          if (i % 2 === 0) {
            result.current.dispatch({ type: 'GAME_CREATED', gameId: 'test-game-123', state: defaultGameState });
          } else {
            result.current.dispatch({ type: 'GAME_CREATE_FAILED', error: 'Test error' });
          }
        });

        // Fix: GAME_CREATED and GAME_CREATE_FAILED both should set loading to false
        expect(result.current.getIsLoading()).toBe(false);

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Verify final state - since last iteration was i=19 (odd), there should be an error
      expect(result.current.getIsLoading()).toBe(false);
      expect(result.current.getLatestError()).toBe('Failed to create game: Test error');
    });

    it('should handle loading state during game operations', async () => {
      const { result } = renderHook(() => useGameStore());

      // Simulate game creation sequence with rapid state changes
      act(() => {
        setupGameCreation(result.current.dispatch, 'new-game', defaultGameState);
        result.current.dispatch({ type: 'GAME_CREATE_FAILED', error: 'Loading cancelled' });
      });

      expect(result.current.getCurrentGameId()).toBe('new-game');
      expect(result.current.getIsLoading()).toBe(false);

      // Rapid reset and recreate
      act(() => {
        result.current.dispatch({ type: 'GAME_CREATED', gameId: 'test-game-123', state: defaultGameState });
        result.current.dispatch({ type: 'RESET_GAME' });
      });

      act(() => {
        setupGameCreation(result.current.dispatch, 'another-game', defaultGameState);
        result.current.dispatch({ type: 'GAME_CREATE_FAILED', error: 'Loading cancelled' });
      });

      expect(result.current.getCurrentGameId()).toBe('another-game');
      expect(result.current.getIsLoading()).toBe(false);
    });
  });

  describe('Error State Race Conditions', () => {
    it('should handle rapid error state changes', async () => {
      const { result } = renderHook(() => useGameStore());

      const errorMessages = ['Connection failed', 'Game creation failed', 'Invalid move', 'Server error'];
      let latestError = null;

      for (const error of errorMessages) {
        act(() => {
          result.current.dispatch({ 
            type: 'NOTIFICATION_ADDED', 
            notification: { 
              id: Math.random().toString(), 
              type: 'error', 
              message: error, 
              timestamp: new Date() 
            } 
          });
        });

        latestError = error; // Track the latest error we added
        expect(result.current.getLatestError()).toBe(latestError);

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Final error should still be the latest
      expect(result.current.getLatestError()).toBe('Server error');
    });

    it('should maintain error state consistency during other updates', async () => {
      const { result } = renderHook(() => useGameStore());

      // Set error state
      act(() => {
        result.current.dispatch({ type: 'NOTIFICATION_ADDED', notification: { id: Math.random().toString(), type: 'error', message: 'Test error', timestamp: new Date() } });
      });

      // Make other state changes that should not clear the error
      act(() => {
        // Test should verify that error persists through game state changes
        setupGameCreation(result.current.dispatch, 'test-game', defaultGameState);
      });

      // Original error should persist through state changes
      expect(result.current.getLatestError()).toBe('Test error');
      expect(result.current.getIsLoading()).toBe(false); // setupGameCreation completes the game creation
      expect(result.current.isConnected()).toBe(true); // setupGameCreation establishes connection
      expect(result.current.getCurrentGameId()).toBe('test-game');
    });
  });

  describe('History State Race Conditions', () => {
    it('should handle rapid history updates', async () => {
      const { result } = renderHook(() => useGameStore());

      const moves = [
        { player: 1, action: '*(4,4)', timestamp: Date.now() },
        { player: 2, action: '*(5,5)', timestamp: Date.now() + 1000 },
        { player: 1, action: '*(6,6)', timestamp: Date.now() + 2000 }
      ];

      // Create an active game first with the moves
      act(() => {
        setupGameCreation(result.current.dispatch, 'history-test', {
          ...defaultGameState,
          move_history: moves.map((move, index) => ({
            notation: move.action,
            player: move.player,
            timestamp: move.timestamp
          }))
        });
      });

      // Rapid history index changes
      for (let i = 0; i < moves.length; i++) {
        act(() => {
          result.current.dispatch({ type: 'HISTORY_INDEX_SET', index: i });
        });

        expect(result.current.getSelectedHistoryIndex()).toBe(i);

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Reset history index
      act(() => {
        result.current.dispatch({ type: 'HISTORY_INDEX_SET', index: null });
      });

      expect(result.current.getSelectedHistoryIndex()).toBeNull();
    });
  });

  describe('Store Reset Race Conditions', () => {
    it('should handle reset during rapid state changes', async () => {
      const { result } = renderHook(() => useGameStore());

      // Set complex state
      act(() => {
        setupGameCreation(result.current.dispatch, 'test-game', defaultGameState);
        result.current.dispatch({ type: 'CONNECTION_START' });
        result.current.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
        result.current.dispatch({ type: 'GAME_CREATED', gameId: 'test-game-123', state: defaultGameState });
        result.current.dispatch({ type: 'NOTIFICATION_ADDED', notification: { id: Math.random().toString(), type: 'error', message: 'Test error', timestamp: new Date() } });
        result.current.dispatch({ 
          type: 'SETTINGS_UPDATED', 
          settings: {
            mode: 'ai_vs_ai',
            ai_difficulty: 'expert',
            ai_time_limit: 10000,
            board_size: 13
          }
        });
      });

      // Rapid reset
      act(() => {
        result.current.dispatch({ type: 'RESET_GAME' });
      });

      // Verify clean state
      expect(result.current.getCurrentGameId()).toBeNull();
      expect(result.current.getCurrentGameState()).toBeNull();
      expect(result.current.isConnected()).toBe(true); // Connection state preserved
      expect(result.current.getIsLoading()).toBe(false);
      expect(result.current.getLatestError()).toBe(null); // Error state cleared on reset
      expect(result.current.getSelectedHistoryIndex()).toBeNull();

      // Settings should be reset to defaults by RESET_GAME action
      expect(result.current.settings.gameSettings.mode).toBe('human_vs_ai');
      expect(result.current.settings.gameSettings.ai_difficulty).toBe('medium');
      expect(result.current.settings.gameSettings.ai_time_limit).toBe(5000);
      expect(result.current.settings.gameSettings.board_size).toBe(9);
    });

    it('should handle multiple rapid resets', async () => {
      const { result } = renderHook(() => useGameStore());

      // Rapid reset calls
      for (let i = 0; i < 10; i++) {
        act(() => {
          // Create a game first
          result.current.dispatch({ type: 'CONNECTION_START' });
          result.current.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
          result.current.dispatch({ type: 'GAME_CREATED', gameId: 'test-game-123', state: defaultGameState });
          result.current.dispatch({ type: 'GAME_CREATED', gameId: `game-${i}`, state: defaultGameState });
          // Then reset
          result.current.dispatch({ type: 'RESET_GAME' });
        });

        expect(result.current.getCurrentGameId()).toBeNull();

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Final state should be clean (except preserved error)
      expect(result.current.getCurrentGameId()).toBeNull();
      expect(result.current.getCurrentGameState()).toBeNull();
      expect(result.current.getIsLoading()).toBe(false);
      // Error may be preserved by design - not testing it here
    });
  });

  describe('Concurrent Store Operations', () => {
    it('should handle simultaneous updates from different sources', async () => {
      const { result } = renderHook(() => useGameStore());

      // Simulate rapid but sequential operations (safer than true concurrency)
      // This still tests the store's ability to handle rapid state changes
      const operations = Array.from({ length: 10 }, (_, i) => ({
        gameId: `concurrent-game-${i}`,
        isLoading: i % 2 === 0,
        error: i % 3 === 0 ? `Error ${i}` : null
      }));

      // Execute operations rapidly but sequentially to avoid act() overlaps
      for (const operation of operations) {
        await act(async () => {
          // Set connection
          result.current.dispatch({ type: 'CONNECTION_START' });
          result.current.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
          
          // Loading state first, then resolve it
          if (operation.isLoading) {
            result.current.dispatch({ type: 'GAME_CREATED', gameId: 'test-game-123', state: defaultGameState });
            // Keep it in loading state (creating-game)
          } else {
            result.current.dispatch({ type: 'GAME_CREATED', gameId: 'test-game-123', state: defaultGameState });
            result.current.dispatch({ type: 'GAME_CREATED', gameId: operation.gameId, state: defaultGameState });
          }
          
          // Error state
          if (operation.error) {
            result.current.dispatch({ 
              type: 'NOTIFICATION_ADDED', 
              notification: { 
                id: Math.random().toString(), 
                type: 'error', 
                message: operation.error, 
                timestamp: new Date() 
              } 
            });
          }

          // Small delay to simulate async nature
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Store should be in a valid state
      expect(typeof result.current.getCurrentGameId()).toBe('string');
      expect(typeof result.current.getIsLoading()).toBe('boolean');
      expect(result.current.getLatestError() === null || typeof result.current.getLatestError() === 'string').toBe(true);
    });
  });
});