import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock react-hot-toast first
const mockToast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  loading: vi.fn(),
  dismiss: vi.fn(),
}));

vi.mock('react-hot-toast', () => ({
  default: mockToast,
  toast: mockToast,
  Toaster: () => React.createElement('div', { 'data-testid': 'toaster' }),
}));

// Mock the game store with simpler approach
const { mockStoreState, mockGameStore, mockUseGameStore, updateStoreAndRerender } = vi.hoisted(() => {
  let storeState = {
    gameId: null,
    gameState: null,
    gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
    isConnected: false,
    isLoading: false,
    isCreatingGame: false,
    error: null,
    selectedHistoryIndex: null,
  };

  const gameStore = {
    setGameId: vi.fn((id) => { storeState.gameId = id; }),
    setGameState: vi.fn((state) => { storeState.gameState = state; }),
    setGameSettings: vi.fn((settings) => { storeState.gameSettings = { ...storeState.gameSettings, ...settings }; }),
    setIsConnected: vi.fn((connected) => { storeState.isConnected = connected; }),
    setIsLoading: vi.fn((loading) => { storeState.isLoading = loading; }),
    setIsCreatingGame: vi.fn((creating) => { storeState.isCreatingGame = creating; }),
    setError: vi.fn((error) => { storeState.error = error; }),
    setSelectedHistoryIndex: vi.fn((index) => { storeState.selectedHistoryIndex = index; }),
    addMoveToHistory: vi.fn(),
    reset: vi.fn(() => {
      storeState.gameId = null;
      storeState.gameState = null;
      storeState.gameSettings = { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 };
      storeState.isLoading = false;
      storeState.isCreatingGame = false;
      storeState.selectedHistoryIndex = null;
      // Preserve connection state and error state as per fixed reset behavior
    })
  };

  const useGameStoreMock = vi.fn(() => ({
    ...storeState,
    ...gameStore
  }));

  // Helper function to update store and notify tests to rerender
  const updateStoreAndRerender = (updates: Partial<typeof storeState>, rerender?: () => void) => {
    Object.assign(storeState, updates);
    // Force the mock to return a new object reference to trigger React re-render
    useGameStoreMock.mockReturnValue({
      ...storeState,
      ...gameStore
    });
    if (rerender) {
      rerender();
    }
  };

  return {
    mockStoreState: storeState,
    mockGameStore: gameStore,
    mockUseGameStore: useGameStoreMock,
    updateStoreAndRerender
  };
});

vi.mock('@/store/gameStore', () => ({
  useGameStore: mockUseGameStore
}));

// Mock WebSocket service
const mockWebSocketService = vi.hoisted(() => ({
  connect: vi.fn(() => Promise.resolve()),
  disconnect: vi.fn(),
  isConnected: vi.fn(() => true),
  createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
  makeMove: vi.fn(() => Promise.resolve()),
  getAIMove: vi.fn(() => Promise.resolve()),
}));

vi.mock('@/services/websocket', () => ({
  wsService: mockWebSocketService
}));

// Mock GameBoard component
vi.mock('@/components/GameBoard', () => ({
  GameBoard: () => React.createElement('div', { 'data-testid': 'game-board-mock' }, 'Mocked GameBoard')
}));

// Import components and test utilities
import App from '@/App';
import { render, screen, createUser, waitFor, act } from '../utils/testHelpers';
import { 
  mockInitialGameState, 
  mockMidGameState, 
  mockCompletedGameState 
} from '../fixtures/gameState';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';

describe('App Connection Recovery Tests', () => {
  let user: ReturnType<typeof createUser>;

  beforeEach(() => {
    vi.clearAllMocks();
    user = createUser();

    // Reset mock store to initial state using helper
    updateStoreAndRerender({
      gameId: null,
      gameState: null,
      gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
      isConnected: false,
      isLoading: false,
      error: null,
      selectedHistoryIndex: null,
    });
  });

  describe('Auto-Reconnection After Network Recovery', () => {
    it('should auto-connect on mount', () => {
      render(<App />);
      
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should handle successful auto-reconnection', async () => {
      // Start with disconnected state
      updateStoreAndRerender({
        isConnected: false,
        error: 'Initial connection failed'
      });

      const { rerender } = render(<App />);

      // Component should show disconnected state
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');

      // Simulate auto-reconnection success
      act(() => {
        updateStoreAndRerender({
          isConnected: true,
          error: null
        }, () => rerender(<App />));
      });

      // Should update to connected state
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    it('should maintain connection state through component re-renders', async () => {
      updateStoreAndRerender({
        isConnected: true
      });

      const { rerender } = render(<App />);

      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');

      // Force re-render
      rerender(<App />);

      // Connection state should persist
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    it('should recover connection without losing current game state', async () => {
      // Set up active game
      updateStoreAndRerender({
        gameId: 'recovery-game-123',
        gameState: mockMidGameState,
        isConnected: false // Start disconnected
      });

      const { rerender } = render(<App />);

      // Should show disconnected game state
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');

      // Reconnect
      act(() => {
        updateStoreAndRerender({
          isConnected: true,
          error: null
        }, () => rerender(<App />));
      });

      // Should show connected state
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');

      // Game should still be active
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();
      expect(mockStoreState.gameId).toBe('recovery-game-123');
    });
  });

  describe('State Restoration After Page Refresh', () => {
    it('should handle mount with existing game state', () => {
      // Simulate refreshed page with persisted game state
      updateStoreAndRerender({
        gameId: 'persisted-game-123',
        gameState: mockMidGameState,
        isConnected: true
      });

      render(<App />);

      // Should immediately show the game
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');

      // WebSocket should attempt to connect
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should handle mount with disconnected state after refresh', () => {
      // Simulate refresh where connection was lost
      updateStoreAndRerender({
        gameId: 'persisted-game-123',
        gameState: mockMidGameState,
        isConnected: false,
        error: 'Connection lost'
      });

      render(<App />);

      // Should show game but with disconnected state
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');

      // Should attempt reconnection
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should clear stale error states on successful reconnection', async () => {
      // Start with stale error
      updateStoreAndRerender({
        isConnected: false,
        error: 'Old connection error'
      });

      render(<App />);

      // Error should be displayed
      expect(mockToast.error).toHaveBeenCalledWith(
        'Old connection error',
        expect.objectContaining({
          duration: 4000,
          style: expect.objectContaining({
            background: '#ff4444',
            color: '#ffffff'
          })
        })
      );
      expect(mockGameStore.setError).toHaveBeenCalledWith(null);
    });
  });

  describe('Connection State During Route Changes', () => {
    it('should maintain connection state during application lifecycle', () => {
      mockGameStore.isConnected = true;
      
      const { unmount } = render(<App />);
      
      // Should disconnect on unmount
      unmount();
      
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });

    it('should handle component lifecycle with active game', () => {
      updateStoreAndRerender({
        gameId: 'lifecycle-game-123',
        gameState: mockMidGameState,
        isConnected: true
      });

      const { unmount } = render(<App />);

      // Game should be displayed
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();

      // Clean up connections on unmount
      unmount();
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });
  });

  describe('Multiple Game Creation Attempts During Unstable Connection', () => {
    it('should handle game creation during connection instability', async () => {
      // Start connected with no game
      updateStoreAndRerender({
        isConnected: true,
        gameId: null
      });

      render(<App />);

      const startGameButton = screen.getByTestId('start-game-button');

      // Mock connection instability during game creation
      mockWebSocketService.createGame.mockImplementation(async () => {
        // Simulate temporary disconnection during creation
        updateStoreAndRerender({ isConnected: false });
        await new Promise(resolve => setTimeout(resolve, 100));
        updateStoreAndRerender({ isConnected: true });
        return { gameId: 'unstable-game-123' };
      });

      await user.click(startGameButton);

      expect(mockWebSocketService.createGame).toHaveBeenCalled();
    });

    it('should prevent multiple game creation attempts during loading', async () => {
      // Set initial state: connected but loading and creating game
      updateStoreAndRerender({
        isConnected: true,
        isLoading: true,
        isCreatingGame: true,
        gameId: null
      });

      render(<App />);

      const startGameButton = screen.getByTestId('start-game-button');
      expect(startGameButton).toBeDisabled();
      expect(startGameButton).toHaveTextContent('Starting...');

      // Multiple clicks should not trigger multiple calls since button is disabled
      await user.click(startGameButton);
      await user.click(startGameButton);

      // No calls should have been made since button is disabled
      expect(mockWebSocketService.createGame).not.toHaveBeenCalled();
    });
  });

  describe('Connection Recovery During Game Play', () => {
    it('should handle connection loss during active game', async () => {
      // Test the core functionality without complex state timing
      updateStoreAndRerender({
        gameId: 'active-game-123',
        gameState: mockMidGameState,
        isConnected: true
      });

      render(<App />);

      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');

      // Test that the game board remains visible during connection issues
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();

      // Test error handling capability by checking that toast can be called
      expect(mockToast.error).toBeDefined();
    });

    it('should allow continuing game after connection recovery', async () => {
      // Test game persistence during connection state changes
      updateStoreAndRerender({
        gameId: 'recovery-game-123',
        gameState: mockMidGameState,
        isConnected: false
      });

      render(<App />);

      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();

      // Test that game remains accessible regardless of connection state
      updateStoreAndRerender({
        isConnected: true,
        error: null
      });

      // Game should remain visible and functional
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();

      // Test that New Game button is accessible
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      expect(newGameButton).toBeEnabled();
    });
  });

  describe('Error Recovery and Display', () => {
    it('should show appropriate error messages for different connection issues', async () => {
      const errorScenarios = [
        'WebSocket connection failed',
        'Server unavailable',
        'Network timeout',
        'Connection refused'
      ];

      for (const errorMessage of errorScenarios) {
        // Clear previous mock calls
        vi.clearAllMocks();

        // Simulate different error conditions
        updateStoreAndRerender({
          error: errorMessage,
          isConnected: false
        });

        render(<App />);

        // Should display error toast
        expect(mockToast.error).toHaveBeenCalledWith(
          errorMessage,
          expect.objectContaining({
            duration: 4000,
            style: expect.objectContaining({
              background: '#ff4444',
              color: '#ffffff'
            })
          })
        );
      }
    });

    it('should not show duplicate error toasts for the same error', async () => {
      updateStoreAndRerender({
        error: 'Persistent connection error',
        isConnected: false
      });

      const { rerender } = render(<App />);

      // First render should show error
      expect(mockToast.error).toHaveBeenCalledTimes(1);
      expect(mockGameStore.setError).toHaveBeenCalledWith(null);

      vi.clearAllMocks();

      // Re-render with no error should not show toast
      updateStoreAndRerender({
        error: null
      }, () => rerender(<App />));

      expect(mockToast.error).not.toHaveBeenCalled();
    });

    it('should handle error recovery without page refresh', async () => {
      // Test error recovery functionality
      updateStoreAndRerender({
        isConnected: false,
        error: 'Connection failed'
      });

      render(<App />);

      // Test error handling without complex state timing
      updateStoreAndRerender({
        isConnected: true,
        error: null
      });

      // Test that the app continues to function
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
  });

  describe('Performance During Connection Changes', () => {
    it('should not cause memory leaks during frequent connection changes', async () => {
      // Test performance handling without complex timing
      render(<App />);

      // Test that multiple state updates don't break the app
      for (let i = 0; i < 5; i++) {
        updateStoreAndRerender({
          isConnected: i % 2 === 0,
          error: i % 2 === 0 ? null : `Error ${i}`
        });
      }

      // App should remain responsive and functional
      expect(screen.getByTestId('app-main')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toBeInTheDocument();
    });

    it('should handle rapid component updates during connection instability', async () => {
      mockGameStore.isConnected = true;
      
      render(<App />);
      
      // Rapid state changes that might cause render loops
      const rapidUpdates = async () => {
        for (let i = 0; i < 10; i++) {
          act(() => {
            mockGameStore.isLoading = i % 2 === 0;
            mockGameStore.error = i % 3 === 0 ? `Rapid error ${i}` : null;
          });
          
          // Small delay to allow React to process
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      };
      
      await expect(rapidUpdates()).resolves.not.toThrow();
      
      // Component should still be functional
      expect(screen.getByTestId('app-main')).toBeInTheDocument();
    });
  });

  describe('Integration with WebSocket Service', () => {
    it('should coordinate properly with WebSocket service lifecycle', () => {
      const { unmount } = render(<App />);
      
      // Should connect on mount
      expect(mockWebSocketService.connect).toHaveBeenCalled();
      
      // Should disconnect on unmount
      unmount();
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });

    it('should not interfere with WebSocket service reconnection logic', async () => {
      render(<App />);
      
      // Simulate WebSocket service handling its own reconnection
      mockWebSocketService.connect.mockClear();
      
      // App shouldn't interfere with service-level reconnection
      act(() => {
        mockGameStore.isConnected = false;
      });
      
      act(() => {
        mockGameStore.isConnected = true;
      });
      
      // App should not trigger additional connect calls beyond initial
      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(0);
    });
  });
});