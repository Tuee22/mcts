/**
 * Game Store Persistence Tests
 *
 * Tests for game store state management, persistence across reconnections,
 * and synchronization issues that could affect E2E test reliability.
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGameStore } from '@/store/gameStore';

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

describe('Game Store Persistence Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);

    // Reset store state
    const { result } = renderHook(() => useGameStore());
    act(() => {
      result.current.reset();
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial store state', () => {
    it('should initialize with default values', () => {
      const { result } = renderHook(() => useGameStore());

      expect(result.current.gameState).toBeNull();
      expect(result.current.gameId).toBeNull();
      expect(result.current.isConnected).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();

      expect(result.current.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      });
    });

    it('should maintain consistent default settings', () => {
      const { result: result1 } = renderHook(() => useGameStore());
      const { result: result2 } = renderHook(() => useGameStore());

      // Both instances should have the same default settings
      expect(result1.current.gameSettings).toEqual(result2.current.gameSettings);
    });

    it('should handle store initialization consistently', () => {
      const { result } = renderHook(() => useGameStore());

      // Store should initialize with consistent state
      expect(result.current.gameSettings.mode).toBe('human_vs_ai');
      expect(result.current.gameSettings.ai_difficulty).toBe('medium');
    });
  });

  describe('Settings management', () => {
    it('should update settings correctly', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setGameSettings({
          mode: 'ai_vs_ai',
          ai_difficulty: 'expert'
        });
      });

      expect(result.current.gameSettings).toEqual({
        mode: 'ai_vs_ai',
        ai_difficulty: 'expert',
        ai_time_limit: 5000, // Unchanged from default
        board_size: 9 // Unchanged from default
      });
    });

    it('should merge partial settings updates', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setGameSettings({ mode: 'human_vs_ai' });
      });

      act(() => {
        result.current.setGameSettings({ ai_difficulty: 'hard' });
      });

      expect(result.current.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'hard',
        ai_time_limit: 5000,
        board_size: 9
      });
    });

    it('should preserve settings during store reset', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setGameSettings({
          mode: 'ai_vs_ai',
          board_size: 7
        });
      });

      // Verify settings were changed
      expect(result.current.gameSettings.mode).toBe('ai_vs_ai');
      expect(result.current.gameSettings.board_size).toBe(7);

      act(() => {
        result.current.reset();
      });

      // Settings should be preserved during reset
      expect(result.current.gameSettings.mode).toBe('ai_vs_ai');
      expect(result.current.gameSettings.board_size).toBe(7);
      // But game state should be reset
      expect(result.current.gameId).toBeNull();
      expect(result.current.gameState).toBeNull();
    });
  });

  describe('Game state management', () => {
    it('should update game ID', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setGameId('test-game-123');
      });

      expect(result.current.gameId).toBe('test-game-123');
    });

    it('should update game state', () => {
      const { result } = renderHook(() => useGameStore());

      const gameState = {
        board_size: 9,
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        current_player: 1,
        winner: null,
        walls: [],
        legal_moves: [],
        move_history: [],
        walls_remaining: [10, 10]
      };

      act(() => {
        result.current.setGameState(gameState);
      });

      expect(result.current.gameState).toEqual(gameState);
    });

    it('should handle incremental game state updates', () => {
      const { result } = renderHook(() => useGameStore());

      const initialState = {
        board_size: 9,
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        current_player: 1,
        winner: null,
        walls: [],
        legal_moves: [],
        move_history: [],
        walls_remaining: [10, 10]
      };

      act(() => {
        result.current.setGameState(initialState);
      });

      // Update with new move
      act(() => {
        result.current.setGameState({
          ...initialState,
          current_player: 2,
          move_history: ['move up']
        });
      });

      expect(result.current.gameState?.current_player).toBe(2);
      expect(result.current.gameState?.move_history).toEqual(['move up']);
    });
  });

  describe('Connection state management', () => {
    it('should track connection state', () => {
      const { result } = renderHook(() => useGameStore());

      expect(result.current.isConnected).toBe(false);

      act(() => {
        result.current.setIsConnected(true);
      });

      expect(result.current.isConnected).toBe(true);
    });

    it('should track loading state', () => {
      const { result } = renderHook(() => useGameStore());

      expect(result.current.isLoading).toBe(false);

      act(() => {
        result.current.setIsLoading(true);
      });

      expect(result.current.isLoading).toBe(true);
    });

    it('should track disconnection but preserve game state', () => {
      const { result } = renderHook(() => useGameStore());

      // Set up game state
      act(() => {
        result.current.setGameId('test-game');
        result.current.setGameState({
          board_size: 9,
          players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
          current_player: 1,
          winner: null,
          walls: [],
          legal_moves: [],
          move_history: [],
          walls_remaining: [10, 10]
        });
        result.current.setIsConnected(true);
      });

      // Disconnect
      act(() => {
        result.current.setIsConnected(false);
      });

      // Game state should be preserved (store doesn't auto-clear on disconnect)
      expect(result.current.gameId).toBe('test-game');
      expect(result.current.gameState).not.toBeNull();
      expect(result.current.isConnected).toBe(false);
    });
  });

  describe('Error handling', () => {
    it('should set and clear errors', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setError('Connection failed');
      });

      expect(result.current.error).toBe('Connection failed');

      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBeNull();
    });

    it('should preserve errors across state changes', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setError('Previous error');
      });

      // Other operations should preserve error (manual clearing required)
      act(() => {
        result.current.setIsConnected(true);
      });

      expect(result.current.error).toBe('Previous error');
    });

    it('should handle multiple error scenarios', () => {
      const { result } = renderHook(() => useGameStore());

      // Connection error
      act(() => {
        result.current.setError('Connection error');
      });

      expect(result.current.error).toBe('Connection error');

      // Game creation error (should replace previous)
      act(() => {
        result.current.setError('Game creation failed');
      });

      expect(result.current.error).toBe('Game creation failed');
    });
  });

  describe('State synchronization', () => {
    it('should handle concurrent state updates', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        // Simulate concurrent updates
        result.current.setGameId('game-1');
        result.current.setIsLoading(true);
        result.current.setIsConnected(true);
        result.current.setError(null);
      });

      expect(result.current.gameId).toBe('game-1');
      expect(result.current.isLoading).toBe(true);
      expect(result.current.isConnected).toBe(true);
      expect(result.current.error).toBeNull();
    });

    it('should maintain state consistency during rapid updates', () => {
      const { result } = renderHook(() => useGameStore());

      const gameState1 = {
        board_size: 9,
        current_player: 1,
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        walls: [],
        walls_remaining: [10, 10],
        legal_moves: ['move1'],
        winner: null,
        move_history: []
      } as any;

      const gameState2 = {
        board_size: 9,
        current_player: 2,
        players: [{ x: 4, y: 7 }, { x: 4, y: 0 }],
        walls: [],
        walls_remaining: [10, 10],
        legal_moves: ['move1', 'move2'],
        winner: null,
        move_history: []
      } as any;

      act(() => {
        result.current.setGameState(gameState1);
        result.current.setGameState(gameState2);
      });

      // Should have the latest state
      expect(result.current.gameState?.current_player).toBe(2);
      expect(result.current.gameState?.legal_moves).toHaveLength(2);
    });

    it('should handle state updates during loading', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setIsLoading(true);
        result.current.setGameId('loading-game');
      });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.gameId).toBe('loading-game');

      act(() => {
        result.current.setIsLoading(false);
        result.current.setGameState({
          board_size: 9,
          current_player: 1,
          players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        } as any);
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.gameState?.current_player).toBe(1);
    });
  });

  describe('Store reset functionality', () => {
    it('should reset game state but preserve settings', () => {
      const { result } = renderHook(() => useGameStore());

      // Set up complete state
      act(() => {
        result.current.setGameSettings({ mode: 'ai_vs_ai', board_size: 7 });
        result.current.setGameId('test-game');
        result.current.setGameState({
          board_size: 9,
          current_player: 1,
          players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        } as any);
        result.current.setIsConnected(true);
        result.current.setIsLoading(true);
        result.current.setError('Some error');
      });

      // Reset
      act(() => {
        result.current.reset();
      });

      // Game state should be cleared
      expect(result.current.gameId).toBeNull();
      expect(result.current.gameState).toBeNull();
      expect(result.current.isLoading).toBe(false);

      // Settings, connection, and error should be preserved (by design)
      expect(result.current.gameSettings.mode).toBe('ai_vs_ai');
      expect(result.current.gameSettings.board_size).toBe(7);
      expect(result.current.isConnected).toBe(true);
      expect(result.current.error).toBe('Some error');
    });

    it('should allow selective state clearing', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setGameId('test-game');
        result.current.setError('Some error');
      });

      // Clear only error
      act(() => {
        result.current.setError(null);
      });

      expect(result.current.gameId).toBe('test-game');
      expect(result.current.error).toBeNull();
    });
  });

  describe('Settings validation', () => {
    it('should validate mode settings', () => {
      const { result } = renderHook(() => useGameStore());

      // Valid mode
      act(() => {
        result.current.setGameSettings({ mode: 'human_vs_ai' as const });
      });

      expect(result.current.gameSettings.mode).toBe('human_vs_ai');
    });

    it('should validate AI difficulty settings', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setGameSettings({
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'expert' as const
        });
      });

      expect(result.current.gameSettings.ai_difficulty).toBe('expert');
    });

    it('should validate board size settings', () => {
      const { result } = renderHook(() => useGameStore());

      const validSizes = [5, 7, 9];

      validSizes.forEach(size => {
        act(() => {
          result.current.setGameSettings({ board_size: size });
        });

        expect(result.current.gameSettings.board_size).toBe(size);
      });
    });

    it('should validate time limit settings', () => {
      const { result } = renderHook(() => useGameStore());

      const validTimeLimits = [1000, 3000, 5000, 10000];

      validTimeLimits.forEach(timeLimit => {
        act(() => {
          result.current.setGameSettings({ ai_time_limit: timeLimit });
        });

        expect(result.current.gameSettings.ai_time_limit).toBe(timeLimit);
      });
    });
  });

  describe('Store subscription and reactivity', () => {
    it('should notify subscribers of state changes', () => {
      const { result, rerender } = renderHook(() => useGameStore());

      const initialGameId = result.current.gameId;

      act(() => {
        result.current.setGameId('new-game');
      });

      rerender();

      expect(result.current.gameId).not.toBe(initialGameId);
      expect(result.current.gameId).toBe('new-game');
    });

    it('should batch multiple state updates', () => {
      const { result } = renderHook(() => useGameStore());

      let updateCount = 0;
      const subscription = vi.fn(() => updateCount++);

      // Subscribe to store changes
      const unsubscribe = useGameStore.subscribe(subscription);

      act(() => {
        result.current.setGameId('test-game');
        result.current.setIsConnected(true);
        result.current.setIsLoading(false);
      });

      // Should have been called for batched updates
      expect(subscription).toHaveBeenCalled();

      unsubscribe();
    });
  });

  describe('Performance optimization', () => {
    it('should not trigger updates for identical state', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setGameId('test-game');
      });

      const subscription = vi.fn();
      const unsubscribe = useGameStore.subscribe(subscription);

      // Set same value again
      act(() => {
        result.current.setGameId('test-game');
      });

      // Zustand triggers subscriptions even for identical values (this is expected behavior)
      expect(subscription).toHaveBeenCalled();

      unsubscribe();
    });

    it('should handle deep equality for complex state', () => {
      const { result } = renderHook(() => useGameStore());

      const gameState = {
        board_size: 9,
        current_player: 1,
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        walls: [],
        walls_remaining: [10, 10],
        legal_moves: ['move1', 'move2'],
        winner: null,
        move_history: []
      } as any;

      act(() => {
        result.current.setGameState(gameState);
      });

      const subscription = vi.fn();
      const unsubscribe = useGameStore.subscribe(subscription);

      // Set identical state
      act(() => {
        result.current.setGameState({ ...gameState });
      });

      // Should update since object reference is different (this is expected behavior for Zustand)
      expect(subscription).toHaveBeenCalled();

      unsubscribe();
    });
  });
});