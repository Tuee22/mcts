// Mock Zustand store for testing
import { act } from '@testing-library/react';
import { vi } from 'vitest';

// Create a mock store factory
export const createMockStore = <T>(initialState: T) => {
  let state = { ...initialState };
  const listeners: Array<() => void> = [];

  const mockStore = {
    getState: () => state,
    setState: (newState: Partial<T> | ((state: T) => Partial<T>)) => {
      act(() => {
        if (typeof newState === 'function') {
          state = { ...state, ...newState(state) };
        } else {
          state = { ...state, ...newState };
        }
        listeners.forEach(listener => listener());
      });
    },
    subscribe: (listener: () => void) => {
      listeners.push(listener);
      return () => {
        const index = listeners.indexOf(listener);
        if (index >= 0) {
          listeners.splice(index, 1);
        }
      };
    },
    destroy: () => {
      listeners.length = 0;
    }
  };

  return mockStore;
};

// Mock game store state
export const mockGameStoreState = {
  gameId: null,
  gameState: null,
  gameSettings: {
    mode: 'human_vs_ai' as const,
    ai_difficulty: 'medium' as const,
    ai_time_limit: 5000,
    board_size: 9
  },
  isConnected: false,
  isLoading: false,
  error: null,
  selectedHistoryIndex: null,
  
  setGameId: vi.fn(),
  setGameState: vi.fn(),
  setGameSettings: vi.fn(),
  setIsConnected: vi.fn(),
  setIsLoading: vi.fn(),
  setError: vi.fn(),
  setSelectedHistoryIndex: vi.fn(),
  addMoveToHistory: vi.fn(),
  reset: vi.fn()
};

// Create a mock store instance
export const mockGameStore = createMockStore(mockGameStoreState);

// Helper to reset all mocks
export const resetMockStore = () => {
  Object.keys(mockGameStoreState).forEach(key => {
    const value = mockGameStoreState[key as keyof typeof mockGameStoreState];
    if (typeof value === 'function' && vi.isMockFunction(value)) {
      value.mockClear();
    }
  });
  
  mockGameStore.setState({
    gameId: null,
    gameState: null,
    gameSettings: {
      mode: 'human_vs_ai' as const,
      ai_difficulty: 'medium' as const,
      ai_time_limit: 5000,
      board_size: 9
    },
    isConnected: false,
    isLoading: false,
    error: null,
    selectedHistoryIndex: null
  });
};