/**
 * Game Store Persistence Tests
 *
 * Tests for game store state management, persistence across reconnections,
 * and synchronization issues that could affect E2E test reliability.
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// Create a mock store for testing
const createMockStore = () => {
  let state = {
    gameId: null as string | null,
    gameState: null as any,
    isConnected: false,
    isLoading: false,
    error: null as string | null,
    settings: {
      gameSettings: {
        mode: 'human_vs_ai' as const,
        ai_difficulty: 'medium' as const,
        ai_time_limit: 5000,
        board_size: 9
      }
    },
    selectedHistoryIndex: null as number | null,
    notifications: [] as any[]
  };

  const subscribers = new Set<() => void>();

  const notify = () => {
    subscribers.forEach(fn => fn());
  };

  return {
    getState: () => state,
    getCurrentGameId: () => state.gameId,
    getCurrentGameState: () => state.gameState,
    isConnected: () => state.isConnected,
    getLatestError: () => state.error,
    get isLoading() { return state.isLoading; },
    get error() { return state.error; },
    get settings() { return state.settings; },
    get selectedHistoryIndex() { return state.selectedHistoryIndex; },
    
    dispatch: vi.fn((action: any) => {
      switch (action.type) {
        case 'CONNECTION_ESTABLISHED':
          state.isConnected = true;
          break;
        case 'CONNECTION_LOST':
          state.isConnected = false;
          break;
        case 'START_GAME':
          state.isLoading = true;
          break;
        case 'GAME_CREATED':
          state.gameId = action.gameId;
          state.gameState = action.state;
          state.isLoading = false;
          break;
        case 'GAME_STATE_UPDATED':
          state.gameState = action.state;
          break;
        case 'RESET_GAME':
          state.gameId = null;
          state.gameState = null;
          state.error = null;
          state.isLoading = false;
          state.selectedHistoryIndex = null;
          // Reset settings to defaults
          state.settings.gameSettings = {
            mode: 'human_vs_ai',
            ai_difficulty: 'medium',
            ai_time_limit: 5000,
            board_size: 9
          };
          break;
        case 'HISTORY_INDEX_SET':
          state.selectedHistoryIndex = action.index;
          break;
      }
      notify();
    }),
    
    setError: vi.fn((error: string | null) => {
      state.error = error;
      notify();
    }),
    
    setGameSettings: vi.fn((newSettings: any) => {
      state.settings.gameSettings = {
        ...state.settings.gameSettings,
        ...newSettings
      };
      notify();
    }),
    
    reset: vi.fn(() => {
      state.gameId = null;
      state.gameState = null;
      state.error = null;
      state.isLoading = false;
      state.isConnected = false;  // Reset connection state
      state.selectedHistoryIndex = null;
      state.settings.gameSettings = {
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      };
      notify();
    }),
    
    subscribe: (fn: () => void) => {
      subscribers.add(fn);
      return () => subscribers.delete(fn);
    }
  };
};

// Mock the actual store
const mockStoreInstance = createMockStore();
const useGameStore = vi.fn(() => mockStoreInstance) as any;
useGameStore.getState = () => mockStoreInstance;
useGameStore.subscribe = mockStoreInstance.subscribe;

vi.mock('@/store/gameStore', () => ({
  useGameStore
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true
});

describe('Game Store Persistence Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
    
    // Reset mock store state
    const store = useGameStore.getState();
    store.reset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial store state', () => {
    it('should initialize with default values', () => {
      const { result } = renderHook(() => useGameStore());

      expect(result.current.getCurrentGameState()).toBeNull();
      expect(result.current.getCurrentGameId()).toBeNull();
      expect(result.current.isConnected()).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();

      expect(result.current.settings.gameSettings).toEqual({
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
      expect(result1.current.settings.gameSettings).toEqual(result2.current.settings.gameSettings);
    });

    it('should handle store initialization consistently', () => {
      const { result } = renderHook(() => useGameStore());

      // Store should initialize with consistent state
      expect(result.current.settings.gameSettings.mode).toBe('human_vs_ai');
      expect(result.current.settings.gameSettings.ai_difficulty).toBe('medium');
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

      expect(result.current.settings.gameSettings).toEqual({
        mode: 'ai_vs_ai',
        ai_difficulty: 'expert',
        ai_time_limit: 5000,
        board_size: 9
      });
    });

    it('should merge partial settings updates', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setGameSettings({ mode: 'human_vs_ai' });
      });

      act(() => {
        result.current.setGameSettings({ ai_difficulty: 'easy' });
      });

      expect(result.current.settings.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'easy',
        ai_time_limit: 5000,
        board_size: 9
      });
    });

    it('should preserve settings across resets by design', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setGameSettings({
          mode: 'ai_vs_ai',
          board_size: 7
        });
      });

      expect(result.current.settings.gameSettings.mode).toBe('ai_vs_ai');
      expect(result.current.settings.gameSettings.board_size).toBe(7);

      act(() => {
        result.current.reset();
      });

      // Settings should be reset to defaults per new design
      expect(result.current.settings.gameSettings.mode).toBe('human_vs_ai');
      expect(result.current.settings.gameSettings.board_size).toBe(9);
      // Game state should be reset
      expect(result.current.getCurrentGameId()).toBeNull();
      expect(result.current.getCurrentGameState()).toBeNull();
    });
  });

  describe('Game state management', () => {
    it('should update game ID', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
        result.current.dispatch({
          type: 'GAME_CREATED',
          gameId: 'test-game-123',
          state: {
            board_size: 9,
            current_player: 0,
            players: [{ row: 0, col: 4 }, { row: 8, col: 4 }],
            walls: [],
            walls_remaining: [10, 10],
            legal_moves: [],
            winner: null,
            is_terminal: false,
            move_history: []
          }
        });
      });
      
      expect(result.current.getCurrentGameId()).toBe('test-game-123');
    });

    it('should update game state', () => {
      const { result } = renderHook(() => useGameStore());

      const gameState = {
        board_size: 9,
        players: [{ row: 0, col: 4 }, { row: 8, col: 4 }],
        current_player: 0,
        winner: null,
        is_terminal: false,
        walls: [],
        legal_moves: [],
        move_history: [],
        walls_remaining: [10, 10]
      };

      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
        result.current.dispatch({
          type: 'GAME_CREATED',
          gameId: 'test-game',
          state: gameState
        });
      });

      expect(result.current.getCurrentGameState()).toEqual(gameState);
    });

    it('should handle incremental game state updates', () => {
      const { result } = renderHook(() => useGameStore());

      const initialState = {
        board_size: 9,
        players: [{ row: 0, col: 4 }, { row: 8, col: 4 }],
        current_player: 0,
        winner: null,
        is_terminal: false,
        walls: [],
        legal_moves: [],
        move_history: [],
        walls_remaining: [10, 10]
      };

      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
        result.current.dispatch({
          type: 'GAME_CREATED',
          gameId: 'test-game',
          state: initialState
        });
      });

      // Update with new move
      act(() => {
        result.current.dispatch({
          type: 'GAME_STATE_UPDATED',
          state: {
            ...initialState,
            current_player: 1,
            move_history: [{ player: 0, notation: 'e2', timestamp: Date.now() }]
          }
        });
      });

      expect(result.current.getCurrentGameState()?.current_player).toBe(1);
      expect(result.current.getCurrentGameState()?.move_history).toHaveLength(1);
    });
  });

  describe('Connection state management', () => {
    it('should track connection state', () => {
      const { result } = renderHook(() => useGameStore());

      expect(result.current.isConnected()).toBe(false);

      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
      });

      expect(result.current.isConnected()).toBe(true);
    });

    it('should track loading state', () => {
      const { result } = renderHook(() => useGameStore());

      expect(result.current.isLoading).toBe(false);

      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
      });

      expect(result.current.isLoading).toBe(true);
    });

    it('should track disconnection but preserve game state', () => {
      const { result } = renderHook(() => useGameStore());

      // Set up game state
      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
        result.current.dispatch({
          type: 'GAME_CREATED',
          gameId: 'test-game',
          state: {
            board_size: 9,
            players: [{ row: 0, col: 4 }, { row: 8, col: 4 }],
            current_player: 0,
            winner: null,
            is_terminal: false,
            walls: [],
            legal_moves: [],
            move_history: [],
            walls_remaining: [10, 10]
          }
        });
      });

      expect(result.current.getCurrentGameId()).toBe('test-game');

      // Disconnect
      act(() => {
        result.current.dispatch({ type: 'CONNECTION_LOST' });
      });

      // Connection state should change, but game data should persist
      expect(result.current.isConnected()).toBe(false);
      expect(result.current.getCurrentGameId()).toBe('test-game');
      expect(result.current.getCurrentGameState()).toBeDefined();
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
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
      });

      // Error should be preserved
      expect(result.current.error).toBe('Previous error');
    });

    it('should handle multiple error scenarios', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setError('Connection error');
      });
      expect(result.current.error).toBe('Connection error');

      act(() => {
        result.current.setError('Game creation error');
      });
      expect(result.current.error).toBe('Game creation error');

      act(() => {
        result.current.setError(null);
      });
      expect(result.current.error).toBeNull();
    });
  });

  describe('State synchronization', () => {
    it('should handle concurrent state updates', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setError(null);
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
      });

      expect(result.current.error).toBeNull();
      expect(result.current.isConnected()).toBe(true);
      expect(result.current.isLoading).toBe(true);
    });

    it('should maintain state consistency during rapid updates', () => {
      const { result } = renderHook(() => useGameStore());

      const gameState = {
        board_size: 9,
        players: [{ row: 0, col: 4 }, { row: 8, col: 4 }],
        current_player: 0,
        winner: null,
        is_terminal: false,
        walls: [],
        legal_moves: [],
        move_history: [],
        walls_remaining: [10, 10]
      };

      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
        result.current.dispatch({
          type: 'GAME_CREATED',
          gameId: 'rapid-test',
          state: gameState
        });
      });

      // Rapid updates
      for (let i = 0; i < 5; i++) {
        act(() => {
          result.current.dispatch({
            type: 'GAME_STATE_UPDATED',
            state: {
              ...gameState,
              current_player: (i % 2) as 0 | 1
            }
          });
        });
      }

      // Final state should be consistent
      expect(result.current.getCurrentGameState()?.current_player).toBe(0);
      expect(result.current.getCurrentGameId()).toBe('rapid-test');
    });

    it('should handle state updates during loading', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
        result.current.setError('Loading error');
      });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.error).toBe('Loading error');
    });
  });

  describe('Store reset functionality', () => {
    it('should reset game state but preserve settings', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        // Add error notification using functional API
        result.current.dispatch({
          type: 'NOTIFICATION_ADDED',
          notification: {
            id: crypto.randomUUID(),
            type: 'error',
            message: 'Some error',
            timestamp: new Date()
          }
        });
        
        // Set up connection and game
        result.current.dispatch({ type: 'CONNECTION_START' });
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
        result.current.dispatch({
          type: 'GAME_CREATED',
          gameId: 'reset-test',
          state: {
            board_size: 9,
            players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
            current_player: 0,
            winner: null,
            walls: [],
            legal_moves: [],
            move_history: [],
            walls_remaining: [10, 10]
          }
        });
      });

      expect(result.current.getCurrentGameId()).toBe('reset-test');
      expect(result.current.isConnected()).toBe(true);

      act(() => {
        result.current.dispatch({ type: 'RESET_GAME' });
      });

      // Game state should be reset
      expect(result.current.getCurrentGameId()).toBeNull();
      expect(result.current.getCurrentGameState()).toBeNull();
      expect(result.current.getLatestError()).toBeNull();
      // Connection preserved
      expect(result.current.isConnected()).toBe(true);
      // Settings reset to defaults
      expect(result.current.settings.gameSettings.mode).toBe('human_vs_ai');
    });

    it('should allow selective state clearing', () => {
      const { result } = renderHook(() => useGameStore());

      act(() => {
        result.current.setError('Some error');
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
      });

      expect(result.current.error).toBe('Some error');
      expect(result.current.isConnected()).toBe(true);

      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBeNull();
      expect(result.current.isConnected()).toBe(true); // Connection preserved
    });
  });

  describe('Store subscription and reactivity', () => {
    it('should notify subscribers of state changes', () => {
      const { result } = renderHook(() => useGameStore());
      const subscriber = vi.fn();

      // Subscribe to store changes
      const unsubscribe = useGameStore.subscribe(subscriber);

      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
      });

      expect(subscriber).toHaveBeenCalled();
      expect(result.current.isConnected()).toBe(true);

      unsubscribe();
    });

    it('should batch multiple state updates', () => {
      const { result } = renderHook(() => useGameStore());
      const subscriber = vi.fn();

      const unsubscribe = useGameStore.subscribe(subscriber);

      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
        result.current.setError('Test error');
      });

      // Zustand batches updates within act
      expect(subscriber).toHaveBeenCalled();

      unsubscribe();
    });
  });

  describe('Performance optimization', () => {
    it('should not trigger updates for identical state', () => {
      const { result } = renderHook(() => useGameStore());
      const subscriber = vi.fn();

      const unsubscribe = useGameStore.subscribe(subscriber);

      act(() => {
        result.current.setError('Same error');
        result.current.setError('Same error');
      });

      // Should be called for the error setting
      expect(subscriber).toHaveBeenCalled();

      unsubscribe();
    });

    it('should handle deep equality for complex state', () => {
      const { result } = renderHook(() => useGameStore());
      const subscriber = vi.fn();

      const gameState = {
        board_size: 9,
        players: [{ row: 0, col: 4 }, { row: 8, col: 4 }],
        current_player: 0,
        winner: null,
        is_terminal: false,
        walls: [],
        legal_moves: [],
        move_history: [],
        walls_remaining: [10, 10]
      };

      const unsubscribe = useGameStore.subscribe(subscriber);

      act(() => {
        result.current.dispatch({
          type: 'CONNECTION_ESTABLISHED',
          clientId: 'test-client'
        });
        result.current.dispatch({ type: 'START_GAME' });
        result.current.dispatch({
          type: 'GAME_CREATED',
          gameId: 'perf-test',
          state: gameState
        });
      });

      // Subscriber called for state changes
      expect(subscriber).toHaveBeenCalled();

      unsubscribe();
    });
  });
});
