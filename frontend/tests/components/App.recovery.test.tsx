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

// Mock the game store
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  const store = {
    gameId: null,
    gameState: null,
    gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
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

  const useGameStoreMock = vi.fn(() => store);
  useGameStoreMock.getState = vi.fn(() => store);
  
  return {
    mockGameStore: store,
    mockUseGameStore: useGameStoreMock
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

describe.skip('App Connection Recovery Tests', () => {
  let user: ReturnType<typeof createUser>;

  beforeEach(() => {
    vi.clearAllMocks();
    user = createUser();
    
    // Reset mock store to initial state
    Object.assign(mockGameStore, {
      gameId: null,
      gameState: null,
      gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
      isConnected: false,
      isLoading: false,
      error: null,
      selectedHistoryIndex: null
    });
  });

  describe('Auto-Reconnection After Network Recovery', () => {
    it('should auto-connect on mount', () => {
      render(<App />);
      
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should handle successful auto-reconnection', async () => {
      render(<App />);
      
      // Simulate initial connection failure
      mockGameStore.isConnected = false;
      mockGameStore.error = 'Initial connection failed';
      
      // Component should show disconnected state
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
      
      // Simulate auto-reconnection success
      act(() => {
        mockGameStore.isConnected = true;
        mockGameStore.error = null;
      });
      
      // Should update to connected state
      await waitFor(() => {
        expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      });
    });

    it('should maintain connection state through component re-renders', async () => {
      mockGameStore.isConnected = true;
      
      const { rerender } = render(<App />);
      
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      
      // Force re-render
      rerender(<App />);
      
      // Connection state should persist
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    it('should recover connection without losing current game state', async () => {
      // Set up active game
      mockGameStore.gameId = 'recovery-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.isConnected = false; // Start disconnected
      
      render(<App />);
      
      // Should show disconnected game state
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
      
      // Reconnect
      act(() => {
        mockGameStore.isConnected = true;
        mockGameStore.error = null;
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      });
      
      // Game should still be active
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      expect(mockGameStore.gameId).toBe('recovery-game-123');
    });
  });

  describe('State Restoration After Page Refresh', () => {
    it('should handle mount with existing game state', () => {
      // Simulate refreshed page with persisted game state
      mockGameStore.gameId = 'persisted-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.isConnected = true;
      
      render(<App />);
      
      // Should immediately show the game
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      
      // WebSocket should attempt to connect
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should handle mount with disconnected state after refresh', () => {
      // Simulate refresh where connection was lost
      mockGameStore.gameId = 'persisted-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.isConnected = false;
      mockGameStore.error = 'Connection lost';
      
      render(<App />);
      
      // Should show game but with disconnected state
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
      
      // Should attempt reconnection
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should clear stale error states on successful reconnection', async () => {
      // Start with stale error
      mockGameStore.isConnected = false;
      mockGameStore.error = 'Old connection error';
      
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
      mockGameStore.gameId = 'lifecycle-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.isConnected = true;
      
      const { unmount } = render(<App />);
      
      // Game should be displayed
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      
      // Clean up connections on unmount
      unmount();
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });
  });

  describe('Multiple Game Creation Attempts During Unstable Connection', () => {
    it('should handle game creation during connection instability', async () => {
      // Start connected
      mockGameStore.isConnected = true;
      
      render(<App />);
      
      // Open settings and try to create game
      const settingsButton = screen.getByRole('button', { name: /game settings/i });
      await user.click(settingsButton);
      
      const startGameButton = screen.getByTestId('start-game-button');
      
      // Mock connection instability during game creation
      mockWebSocketService.createGame.mockImplementation(async () => {
        // Simulate temporary disconnection during creation
        mockGameStore.isConnected = false;
        await new Promise(resolve => setTimeout(resolve, 100));
        mockGameStore.isConnected = true;
        return { gameId: 'unstable-game-123' };
      });
      
      await user.click(startGameButton);
      
      expect(mockWebSocketService.createGame).toHaveBeenCalled();
    });

    it('should prevent multiple game creation attempts during loading', async () => {
      mockGameStore.isConnected = true;
      
      render(<App />);
      
      const settingsButton = screen.getByRole('button', { name: /game settings/i });
      await user.click(settingsButton);
      
      // Set loading state
      mockGameStore.isLoading = true;
      
      // Force re-render to reflect loading state
      await user.click(settingsButton);
      await user.click(settingsButton);
      
      const startGameButton = screen.getByTestId('start-game-button');
      expect(startGameButton).toBeDisabled();
      expect(startGameButton).toHaveTextContent('Starting...');
      
      // Multiple clicks should not trigger multiple calls
      await user.click(startGameButton);
      await user.click(startGameButton);
      
      // Should only be called once (if at all, since button is disabled)
      expect(mockWebSocketService.createGame).not.toHaveBeenCalled();
    });
  });

  describe('Connection Recovery During Game Play', () => {
    it('should handle connection loss during active game', async () => {
      // Set up active game
      mockGameStore.gameId = 'active-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.isConnected = true;
      
      render(<App />);
      
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      
      // Simulate connection loss during game
      act(() => {
        mockGameStore.isConnected = false;
        mockGameStore.error = 'Connection lost during game';
      });
      
      // Should show error and disconnected state but keep game visible
      await waitFor(() => {
        expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
      });
      
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      expect(mockToast.error).toHaveBeenCalledWith(
        'Connection lost during game',
        expect.objectContaining({
          duration: 4000
        })
      );
    });

    it('should allow continuing game after connection recovery', async () => {
      // Start with disconnected game
      mockGameStore.gameId = 'recovery-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.isConnected = false;
      
      render(<App />);
      
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
      
      // Recover connection
      act(() => {
        mockGameStore.isConnected = true;
        mockGameStore.error = null;
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      });
      
      // Game should still be playable
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      
      // New Game button should be functional
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
      
      render(<App />);
      
      for (const errorMessage of errorScenarios) {
        // Simulate different error conditions
        act(() => {
          mockGameStore.error = errorMessage;
        });
        
        const { rerender } = render(<App />);
        rerender(<App />);
        
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
      mockGameStore.error = 'Persistent connection error';
      
      const { rerender } = render(<App />);
      
      // First render should show error
      expect(mockToast.error).toHaveBeenCalledTimes(1);
      expect(mockGameStore.setError).toHaveBeenCalledWith(null);
      
      vi.clearAllMocks();
      
      // Re-render with no error should not show toast
      mockGameStore.error = null;
      rerender(<App />);
      
      expect(mockToast.error).not.toHaveBeenCalled();
    });

    it('should handle error recovery without page refresh', async () => {
      // Start with error state
      mockGameStore.isConnected = false;
      mockGameStore.error = 'Connection failed';
      
      render(<App />);
      
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');
      
      // Clear error and reconnect
      act(() => {
        mockGameStore.isConnected = true;
        mockGameStore.error = null;
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      });
      
      // Should be back to normal functioning
      const settingsButton = screen.getByRole('button', { name: /game settings/i });
      expect(settingsButton).toBeEnabled();
    });
  });

  describe('Performance During Connection Changes', () => {
    it('should not cause memory leaks during frequent connection changes', async () => {
      render(<App />);
      
      // Simulate frequent connection state changes
      for (let i = 0; i < 20; i++) {
        act(() => {
          mockGameStore.isConnected = i % 2 === 0;
          mockGameStore.error = i % 2 === 0 ? null : `Error ${i}`;
        });
        
        await waitFor(() => {
          expect(screen.getByTestId('connection-text')).toHaveTextContent(
            i % 2 === 0 ? 'Connected' : 'Disconnected'
          );
        });
      }
      
      // Should remain responsive
      expect(screen.getByTestId('app-main')).toBeInTheDocument();
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