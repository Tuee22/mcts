/**
 * Game Store Race Condition Tests
 *
 * Tests rapid state changes in the Zustand game store that can cause UI race conditions.
 * These tests focus on the store's behavior during rapid updates and concurrent operations.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useGameStore } from '@/store/gameStore';

// Mock WebSocket service to control connection state
const mockWsService = {
  connect: vi.fn(() => Promise.resolve()),
  disconnect: vi.fn(),
  isConnected: vi.fn(() => true),
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
    store.reset();
    vi.clearAllMocks();
  });

  describe('Rapid Connection State Changes', () => {
    it('should handle rapid setIsConnected calls without losing state', async () => {
      const { result } = renderHook(() => useGameStore());

      // Rapid connection state changes
      const connectionStates = [true, false, true, false, true];

      for (const connected of connectionStates) {
        act(() => {
          result.current.setIsConnected(connected);
        });

        expect(result.current.isConnected).toBe(connected);

        // Small delay to simulate real timing
        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Verify final state is consistent
      expect(result.current.isConnected).toBe(true);
      expect(result.current.gameId).toBeNull();
      expect(result.current.gameState).toBeNull();
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
        result.current.setGameSettings(customSettings);
      });

      // Rapid connection changes
      for (let i = 0; i < 10; i++) {
        act(() => {
          result.current.setIsConnected(i % 2 === 0);
        });

        // Settings should remain unchanged
        expect(result.current.gameSettings).toEqual(customSettings);

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

      for (const gameId of gameIds) {
        act(() => {
          result.current.setGameId(gameId);
        });

        expect(result.current.gameId).toBe(gameId);

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Verify other state remains consistent
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
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
        result.current.setGameId('test-game');
        result.current.setGameState(mockGameState);
      });

      expect(result.current.gameId).toBe('test-game');
      expect(result.current.gameState).toEqual(mockGameState);

      // Rapid state changes
      for (let i = 0; i < 5; i++) {
        const updatedState = {
          ...mockGameState,
          move_count: i,
          current_player: (i % 2) + 1
        };

        act(() => {
          result.current.setGameState(updatedState);
          result.current.setGameId(`game-${i}`);
        });

        expect(result.current.gameState?.move_count).toBe(i);
        expect(result.current.gameId).toBe(`game-${i}`);

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
          result.current.setIsLoading(i % 2 === 0);
        });

        expect(result.current.isLoading).toBe(i % 2 === 0);

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Verify final state
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should handle loading state during game operations', async () => {
      const { result } = renderHook(() => useGameStore());

      // Simulate game creation sequence with rapid state changes
      act(() => {
        result.current.setIsLoading(true);
      });

      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 5));
      });

      act(() => {
        result.current.setGameId('new-game');
        result.current.setIsLoading(false);
      });

      expect(result.current.gameId).toBe('new-game');
      expect(result.current.isLoading).toBe(false);

      // Rapid reset and recreate
      act(() => {
        result.current.setIsLoading(true);
        result.current.setGameId(null);
      });

      act(() => {
        result.current.setGameId('another-game');
        result.current.setIsLoading(false);
      });

      expect(result.current.gameId).toBe('another-game');
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('Error State Race Conditions', () => {
    it('should handle rapid error state changes', async () => {
      const { result } = renderHook(() => useGameStore());

      const errors = [
        'Connection failed',
        'Game creation failed',
        null,
        'Invalid move',
        null,
        'Server error'
      ];

      for (const error of errors) {
        act(() => {
          result.current.setError(error);
        });

        expect(result.current.error).toBe(error);

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Clear error
      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBeNull();
    });

    it('should maintain error state consistency during other updates', async () => {
      const { result } = renderHook(() => useGameStore());

      // Set error state
      act(() => {
        result.current.setError('Test error');
      });

      // Make other state changes
      act(() => {
        result.current.setIsLoading(true);
        result.current.setIsConnected(false);
        result.current.setGameId('test-game');
      });

      // Error should persist until explicitly cleared
      expect(result.current.error).toBe('Test error');
      expect(result.current.isLoading).toBe(true);
      expect(result.current.isConnected).toBe(false);
      expect(result.current.gameId).toBe('test-game');
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

      // Rapid move additions
      for (const move of moves) {
        act(() => {
          result.current.addMoveToHistory(move);
        });

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Rapid history index changes
      for (let i = 0; i < moves.length; i++) {
        act(() => {
          result.current.setSelectedHistoryIndex(i);
        });

        expect(result.current.selectedHistoryIndex).toBe(i);

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Reset history index
      act(() => {
        result.current.setSelectedHistoryIndex(null);
      });

      expect(result.current.selectedHistoryIndex).toBeNull();
    });
  });

  describe('Store Reset Race Conditions', () => {
    it('should handle reset during rapid state changes', async () => {
      const { result } = renderHook(() => useGameStore());

      // Set complex state
      act(() => {
        result.current.setGameId('test-game');
        result.current.setIsConnected(true);
        result.current.setIsLoading(true);
        result.current.setError('Test error');
        result.current.setGameSettings({
          mode: 'ai_vs_ai',
          ai_difficulty: 'expert',
          ai_time_limit: 10000,
          board_size: 13
        });
      });

      // Rapid reset
      act(() => {
        result.current.reset();
      });

      // Verify clean state
      expect(result.current.gameId).toBeNull();
      expect(result.current.gameState).toBeNull();
      expect(result.current.isConnected).toBe(true); // Connection state preserved
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe('Test error'); // Error state preserved by design
      expect(result.current.selectedHistoryIndex).toBeNull();

      // Settings should be preserved (not reset) by design
      expect(result.current.gameSettings.mode).toBe('ai_vs_ai');
      expect(result.current.gameSettings.ai_difficulty).toBe('expert');
      expect(result.current.gameSettings.ai_time_limit).toBe(10000);
      expect(result.current.gameSettings.board_size).toBe(13);
    });

    it('should handle multiple rapid resets', async () => {
      const { result } = renderHook(() => useGameStore());

      // Rapid reset calls
      for (let i = 0; i < 10; i++) {
        act(() => {
          result.current.setGameId(`game-${i}`);
          result.current.reset();
        });

        expect(result.current.gameId).toBeNull();

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      // Final state should be clean (except preserved error)
      expect(result.current.gameId).toBeNull();
      expect(result.current.gameState).toBeNull();
      expect(result.current.isLoading).toBe(false);
      // Error may be preserved by design - not testing it here
    });
  });

  describe('Concurrent Store Operations', () => {
    it('should handle simultaneous updates from different sources', async () => {
      const { result } = renderHook(() => useGameStore());

      // Simulate concurrent operations (like multiple components updating store)
      const operations = Array.from({ length: 10 }, (_, i) => async () => {
        act(() => {
          result.current.setGameId(`concurrent-game-${i}`);
          result.current.setIsLoading(i % 2 === 0);
          result.current.setError(i % 3 === 0 ? `Error ${i}` : null);
        });

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, Math.random() * 5));
        });
      });

      // Execute all operations concurrently
      await Promise.all(operations.map(op => op()));

      // Store should be in a valid state
      expect(typeof result.current.gameId).toBe('string');
      expect(typeof result.current.isLoading).toBe('boolean');
      expect(result.current.error === null || typeof result.current.error === 'string').toBe(true);
    });
  });
});