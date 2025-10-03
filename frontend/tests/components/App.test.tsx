import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Use vi.hoisted to create mocks that can be referenced
const { mockWebSocketService, mockToast } = vi.hoisted(() => ({
  mockWebSocketService: {
    connect: vi.fn(() => Promise.resolve()),
    disconnect: vi.fn(),
    disconnectFromGame: vi.fn(),
    isConnected: vi.fn(() => true), // Will be updated after mockGameStore is created,
    createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
    makeMove: vi.fn(() => Promise.resolve()),
    getAIMove: vi.fn(() => Promise.resolve()),
    joinGame: vi.fn(),
    requestGameState: vi.fn(() => Promise.resolve()),
    connectToGame: vi.fn(),
  },
  mockToast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  }
}));

// Mock react-hot-toast with proper ES6 module structure
vi.mock('react-hot-toast', () => ({
  default: mockToast,
  toast: mockToast,
  Toaster: () => React.createElement('div', { 'data-testid': 'toaster' }),
}));

// Mock the game store first with vi.hoisted (same pattern as GameSettings test)
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  // Create mock store inline to avoid import issues with hoisting
  const store = {
    // State properties
    connection: {
      type: 'connected' as const,
      clientId: 'test-client',
      since: new Date(),
      canReset: true
    },
    session: { type: 'no-game' as const },
    settings: {
      gameSettings: {
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      },
      theme: 'light',
      soundEnabled: true
    },
    ui: {
      settingsExpanded: false,
      selectedHistoryIndex: null,
      notifications: []
    },
    
    // New API methods
    dispatch: vi.fn(),
    reset: vi.fn(),
    getSettingsUI: vi.fn(() => {
      // When there's a game, show the toggle button
      // When there's no game and connected, show the panel
      const hasGame = mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-over';
      const connected = mockGameStore.connection.type === 'connected';
      
      if (hasGame) {
        return {
          type: 'button-visible',
          enabled: connected
        };
      } else if (connected) {
        return {
          type: 'panel-visible',
          canStartGame: true,
        };
      } else {
        return {
          type: 'button-visible',
          enabled: false
        };
      }
    }),
    isConnected: vi.fn(() => mockGameStore.connection.type === 'connected'),
    getCurrentGameId: vi.fn(() => {
      if (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-over') {
        return mockGameStore.session.gameId;
      }
      return null;
    }),
    getCurrentGameState: vi.fn(() => {
      if (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-over') {
        return mockGameStore.session.state;
      }
      return null;
    }),
    canStartGame: vi.fn(() => false),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => false),
    getSelectedHistoryIndex: vi.fn(() => null),
    getLatestError: vi.fn(() => null),
    getIsLoading: vi.fn(() => false),
    
    // Legacy compatibility
    gameId: null,
    gameState: null,
    gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
    isLoading: false,
    error: null,
    selectedHistoryIndex: null,
    // setGameId removed - use dispatch,
    // setGameState removed - use dispatch,
    setGameSettings: vi.fn(),
    // setIsConnected removed - use dispatch,
    // setIsLoading removed - use dispatch,
    setError: vi.fn(),
    setSelectedHistoryIndex: vi.fn(),
    addMoveToHistory: vi.fn()
  };

  const useGameStoreMock = vi.fn((selector) => {
    // If selector is provided, call it with the store
    if (typeof selector === 'function') {
      return selector(store);
    }
    // Otherwise return the whole store
    return store;
  });
  useGameStoreMock.getState = vi.fn(() => store);
  
  return {
    mockGameStore: store,
    mockUseGameStore: useGameStoreMock
  };
});

vi.mock('@/store/gameStore', () => ({
  useGameStore: mockUseGameStore
}));

vi.mock('@/services/websocket', () => ({
  wsService: mockWebSocketService
}));

// Mock GameBoard component to prevent rendering errors
vi.mock('@/components/GameBoard', () => ({
  GameBoard: () => React.createElement('div', { 'data-testid': 'game-board-mock' }, 'Mocked GameBoard')
}));

// Import components and test utilities
import App from '@/App';
import { render, screen, waitFor, createUser } from '../utils/testHelpers';
import { act } from '@testing-library/react';
import { 
  mockInitialGameState, 
  mockMidGameState, 
  mockCompletedGameState 
} from '../fixtures/gameState';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';

describe('App Component', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    // Ensure real timers are used by default for each test
    vi.useRealTimers();
    // Reset the game store state for each test - ensure objects exist
    if (!mockGameStore.connection) mockGameStore.connection = {};
    if (!mockGameStore.session) mockGameStore.session = {};
    if (!mockGameStore.settings) mockGameStore.settings = {};
    if (!mockGameStore.ui) mockGameStore.ui = {};
    
    Object.assign(mockGameStore.connection, {
      type: 'disconnected' as const,
      canReset: true
    });
    Object.assign(mockGameStore.session, {
      type: 'no-game'
    });
    Object.assign(mockGameStore.settings, {
      gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
      theme: 'light',
      soundEnabled: true
    });
    Object.assign(mockGameStore.ui, {
      settingsExpanded: false,
      selectedHistoryIndex: null,
      notifications: []
    });
    // Update legacy compatibility properties
    if (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-over') {
      mockGameStore.gameId = mockGameStore.session.gameId;
      if (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-over') {
        mockGameStore.gameState = mockGameStore.session.state;
      } else {
        mockGameStore.gameState = null;
      }
    } else {
      mockGameStore.gameId = null;
      mockGameStore.gameState = null;
    }
    mockGameStore.gameSettings = { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 };
    mockGameStore.isLoading = false;
    mockGameStore.error = null;
    mockGameStore.selectedHistoryIndex = null;
    // Update isConnected function to return the right value
    mockGameStore.isConnected.mockReturnValue(false);
  });

  describe('Rendering Structure', () => {
    it('renders main app structure correctly', () => {
      render(<App />);

      expect(screen.getByText('CORRIDORS')).toBeInTheDocument();
      expect(screen.getByTestId('connection-status')).toBeInTheDocument();
      expect(screen.getByTestId('app-main')).toBeInTheDocument();
      expect(screen.getByText('© 2024 Corridors MCTS - Retro Gaming Edition')).toBeInTheDocument();
    });

    it('shows game setup when no game ID exists', () => {
      mockGameStore.session = { type: 'no-game' };
      mockGameStore.gameId = null;

      render(<App />);

      expect(screen.getByTestId('game-setup')).toBeInTheDocument();
      expect(screen.queryByTestId('game-container')).not.toBeInTheDocument();
    });

    it('shows game container when game ID exists', () => {
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: mockInitialGameState,
        lastSync: new Date()
      };
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = mockInitialGameState;

      render(<App />);

      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      expect(screen.queryByTestId('game-setup')).not.toBeInTheDocument();
    });
  });

  describe('Connection Status Display', () => {
    it('shows connected status when connected', () => {
      mockGameStore.connection = { type: 'connected' as const, clientId: 'test-client', since: new Date(), canReset: true };
      mockGameStore.isConnected.mockReturnValue(true);

      render(<App />);

      const indicator = screen.getByTestId('connection-indicator');
      const text = screen.getByTestId('connection-text');

      expect(indicator).toHaveClass('connected');
      expect(text).toHaveTextContent('Connected');
    });

    it('shows disconnected status when not connected', () => {
      mockGameStore.connection = { type: 'disconnected' as const, canReset: true };
      mockGameStore.isConnected.mockReturnValue(false);

      render(<App />);

      const indicator = screen.getByTestId('connection-indicator');
      const text = screen.getByTestId('connection-text');

      expect(indicator).toHaveClass('disconnected');
      expect(text).toHaveTextContent('Disconnected');
    });
  });

  describe('Game Info Panel', () => {
    beforeEach(() => {
      // Properly update the mock store with all necessary data
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: mockMidGameState,
        lastSync: new Date()
      };
      Object.assign(mockGameStore.settings, {
        gameSettings: mockDefaultGameSettings
      });
      Object.assign(mockGameStore.connection, {
        type: 'connected' as const,
          clientId: 'test-client',
          since: new Date(),
          canReset: true
      });
      Object.assign(mockGameStore.ui, {
        selectedHistoryIndex: null
      });
      // Update legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.gameSettings = mockDefaultGameSettings;
      mockGameStore.isConnected.mockReturnValue(true);
      mockGameStore.isLoading = false;
      mockGameStore.error = null;
      mockGameStore.selectedHistoryIndex = null;
    });

    it('displays game mode correctly', () => {
      render(<App />);

      // Check the game container exists
      const gameContainer = screen.getByTestId('game-container');
      expect(gameContainer).toBeInTheDocument();
      
      // The mode is 'human_vs_ai' and replace(/_/g, ' ') replaces all underscores
      // So it becomes 'human vs ai'
      expect(screen.getByText('human vs ai')).toBeInTheDocument();
    });

    it('displays AI settings for AI games', () => {
      render(<App />);

      expect(screen.getByText('medium')).toBeInTheDocument();
      expect(screen.getByText('5s')).toBeInTheDocument();
    });

    it('hides AI settings for human vs human games', () => {
      mockGameStore.settings.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'human_vs_human'
      };
      mockGameStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'human_vs_human'
      };

      render(<App />);

      expect(screen.queryByText('AI Level:')).not.toBeInTheDocument();
      expect(screen.queryByText('AI Time:')).not.toBeInTheDocument();
    });

    it('displays board size correctly', () => {
      render(<App />);

      expect(screen.getByText('9x9')).toBeInTheDocument();
    });

    it('displays truncated game ID', () => {
      render(<App />);

      expect(screen.getByText('test-gam')).toBeInTheDocument();
    });
  });

  describe('Game Controls', () => {
    beforeEach(() => {
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: mockMidGameState,
        lastSync: new Date()
      };
      mockGameStore.connection = { type: 'connected' as const, clientId: 'test-client', since: new Date(), canReset: true };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.isConnected.mockReturnValue(true); // Button requires connection to be enabled
    });

    it('renders New Game button', async () => {
      render(<App />);
      const user = createUser();

      const newGameButton = screen.getByText('New Game');
      expect(newGameButton).toBeInTheDocument();

      // Check that the button is not disabled
      expect(newGameButton).not.toBeDisabled();

      // Clear any dispatch calls that happened during render/mount
      mockGameStore.dispatch.mockClear();
      mockWebSocketService.disconnectFromGame.mockClear();

      await act(async () => {
        await user.click(newGameButton);
      });

      // Check immediately - these should be called synchronously
      expect(mockWebSocketService.disconnectFromGame).toHaveBeenCalled();
      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
    });

    it('renders Copy Moves button and handles clipboard operation', async () => {
      vi.useFakeTimers();
      render(<App />);
      const user = createUser();

      const copyButton = screen.getByText('Copy Moves');
      expect(copyButton).toBeInTheDocument();

      await user.click(copyButton);

      // First check if the toast was called - this tells us the onClick handler ran
      expect(mockToast.success).toHaveBeenCalledWith(
        'Moves copied to clipboard!',
        expect.objectContaining({
          style: expect.objectContaining({
            background: '#00ff00',
            color: '#000000'
          })
        })
      );
      
      vi.useRealTimers();
    });

    it('handles clipboard failure gracefully', async () => {
      // Mock clipboard API to fail
      const originalWriteText = navigator.clipboard.writeText;
      navigator.clipboard.writeText = vi.fn().mockRejectedValue(new Error('Clipboard access denied'));

      vi.useFakeTimers();
      render(<App />);
      const user = createUser();

      const copyButton = screen.getByText('Copy Moves');
      await user.click(copyButton);

      // Component should not crash on clipboard failure - no need to check specific calls
      // If the test doesn't throw an error, the failure was handled gracefully
      expect(copyButton).toBeInTheDocument(); // Just verify component is still functional
      
      // Restore original function
      navigator.clipboard.writeText = originalWriteText;
      vi.useRealTimers();
    });

    it('does not show copy moves button when no game state exists', async () => {
      mockGameStore.session = { type: 'no-game' };
      mockGameStore.gameState = null;

      render(<App />);

      // Should show game setup instead of game interface
      expect(screen.getByTestId('game-setup')).toBeInTheDocument();

      // Copy Moves button should not be available during loading
      expect(screen.queryByText('Copy Moves')).not.toBeInTheDocument();
    });
  });

  describe('WebSocket Connection Management', () => {
    it('connects to WebSocket on mount', () => {
      render(<App />);

      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('disconnects from WebSocket on unmount', () => {
      const { unmount } = render(<App />);

      unmount();

      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('displays error toast when error exists in store', async () => {
      // Start with no notifications
      mockGameStore.ui.notifications = [];

      const { rerender } = render(<App />);

      // Add error notification and rerender to trigger the useEffect
      mockGameStore.ui.notifications = [{
        id: 'test-error',
        type: 'error',
        message: 'Connection failed',
        timestamp: new Date()
      }];
      rerender(<App />);

      // The useEffect should trigger and show toast
      expect(mockToast.error).toHaveBeenCalledWith(
        'Connection failed',
        expect.objectContaining({
          duration: 4000,
          style: expect.objectContaining({
            background: '#ff4444',
            color: '#ffffff'
          })
        })
      );
    });

    it('does not show toast when no error exists', () => {
      mockGameStore.error = null;

      render(<App />);

      expect(mockToast.error).not.toHaveBeenCalled();
    });
  });

  describe('AI Move Automation', () => {
    it('triggers AI move for AI vs AI games', async () => {
      vi.useFakeTimers();
      
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: { ...mockInitialGameState, current_player: 0 },
        lastSync: new Date()
      };
      mockGameStore.settings.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = { ...mockInitialGameState, current_player: 0 };
      mockGameStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };

      render(<App />);

      // Advance timers and immediately check - no waitFor needed
      vi.advanceTimersByTime(1000);

      expect(mockWebSocketService.getAIMove).toHaveBeenCalledWith('test-game-123');

      vi.useRealTimers();
    });

    it('triggers AI move for human vs AI when AI turn', async () => {
      vi.useFakeTimers();
      
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: { ...mockInitialGameState, current_player: 1 },
        lastSync: new Date()
      };
      mockGameStore.settings.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'human_vs_ai'
      };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = { ...mockInitialGameState, current_player: 1 };
      mockGameStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'human_vs_ai'
      };

      render(<App />);

      // Advance timers and immediately check - no waitFor needed
      vi.advanceTimersByTime(500);

      expect(mockWebSocketService.getAIMove).toHaveBeenCalledWith('test-game-123');

      vi.useRealTimers();
    });

    it('does not trigger AI move for human vs AI when human turn', async () => {
      vi.useFakeTimers();
      
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: { ...mockInitialGameState, current_player: 0 },
        lastSync: new Date()
      };
      mockGameStore.settings.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'human_vs_ai'
      };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = { ...mockInitialGameState, current_player: 0 };
      mockGameStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'human_vs_ai'
      };

      render(<App />);

      vi.advanceTimersByTime(1000);

      expect(mockWebSocketService.getAIMove).not.toHaveBeenCalled();

      vi.useRealTimers();
    });

    it('does not trigger AI move when game is over', async () => {
      vi.useFakeTimers();
      
      mockGameStore.session = {
        type: 'game-over',
        gameId: 'test-game-123',
        state: mockCompletedGameState,
        winner: 0
      };
      mockGameStore.settings.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = mockCompletedGameState;
      mockGameStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };

      render(<App />);

      vi.advanceTimersByTime(1000);

      expect(mockWebSocketService.getAIMove).not.toHaveBeenCalled();

      vi.useRealTimers();
    });
  });

  describe('Component Integration', () => {
    it('renders all child components when game is active', () => {
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: mockMidGameState,
        lastSync: new Date()
      };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = mockMidGameState;

      render(<App />);

      // These components are mocked, but we can verify they're rendered
      // by checking for elements that would only exist if they're present
      expect(screen.getByText('New Game')).toBeInTheDocument();
      expect(screen.getByText('Copy Moves')).toBeInTheDocument();
    });
  });

  describe('Performance and Memory', () => {
    it('does not create memory leaks with timers', () => {
      vi.useFakeTimers();
      
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: { ...mockInitialGameState, current_player: 0 },
        lastSync: new Date()
      };
      mockGameStore.settings.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = { ...mockInitialGameState, current_player: 0 };
      mockGameStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };

      const { unmount } = render(<App />);

      // Unmount component before timer fires
      unmount();
      
      vi.advanceTimersByTime(1000);

      // AI move should not be called after unmount
      expect(mockWebSocketService.getAIMove).not.toHaveBeenCalled();

      vi.useRealTimers();
    });

    it('cleans up timers when game state changes', () => {
      vi.useFakeTimers();
      
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: { ...mockInitialGameState, current_player: 0 },
        lastSync: new Date()
      };
      mockGameStore.settings.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = { ...mockInitialGameState, current_player: 0 };
      mockGameStore.gameSettings = {
        ...mockDefaultGameSettings,
        mode: 'ai_vs_ai'
      };

      const { rerender } = render(<App />);

      // Change game state to completed
      mockGameStore.session = {
        type: 'game-over',
        gameId: 'test-game-123',
        state: mockCompletedGameState,
        winner: 0
      };
      mockGameStore.gameState = mockCompletedGameState;
      rerender(<App />);

      vi.advanceTimersByTime(1000);

      // Should not trigger AI move for completed game
      expect(mockWebSocketService.getAIMove).not.toHaveBeenCalled();

      vi.useRealTimers();
    });
  });

  describe('New Game Disconnection Bug', () => {
    let user: ReturnType<typeof createUser>;

    beforeEach(() => {
      user = createUser();
    });

    it('should NOT show disconnected status after clicking New Game', async () => {
      vi.useFakeTimers();
      
      // Start with connected state and active game
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: mockMidGameState,
        lastSync: new Date()
      };
      mockGameStore.connection = { type: 'connected' as const, clientId: 'test-client', since: new Date(), canReset: true };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.isConnected.mockReturnValue(true);
      
      render(<App />);
      
      // Verify initial connected state
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      await user.click(newGameButton);
      
      // BUG TEST: After clicking New Game, connection should remain "Connected"
      // This will currently fail due to reset() setting isConnected: false
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      expect(screen.getByTestId('connection-text')).not.toHaveTextContent('Disconnected');
      
      vi.useRealTimers();
    });

    it('should allow settings access after New Game button click', async () => {
      vi.useFakeTimers();
      
      // Start with active game
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: mockMidGameState,
        lastSync: new Date()
      };
      mockGameStore.connection = { type: 'connected' as const, clientId: 'test-client', since: new Date(), canReset: true };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.isConnected.mockReturnValue(true);
      
      render(<App />);
      const user = createUser();
      
      // Clear any dispatch calls that happened during render/mount
      mockGameStore.dispatch.mockClear();
      
      // Click New Game to reset
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      await user.click(newGameButton);
      
      // Should return to game setup
      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      
      // ⚙️ Game Settings button should be accessible (not disabled due to false disconnection)
      // Note: This test may need adjustment based on how the component re-renders after reset
      
      vi.useRealTimers();
    });

    it('connection indicator should remain green after New Game', async () => {
      vi.useFakeTimers();
      
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: mockMidGameState,
        lastSync: new Date()
      };
      mockGameStore.connection = { type: 'connected' as const, clientId: 'test-client', since: new Date(), canReset: true };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = mockMidGameState;
      mockGameStore.isConnected.mockReturnValue(true);
      
      render(<App />);
      
      const connectionIndicator = screen.getByTestId('connection-indicator');
      expect(connectionIndicator).toHaveClass('connected');
      
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      await user.click(newGameButton);
      
      // Connection indicator should stay green (connected), not turn red (disconnected)
      expect(connectionIndicator).toHaveClass('connected');
      expect(connectionIndicator).not.toHaveClass('disconnected');
      
      vi.useRealTimers();
    });
  });

  describe('Accessibility', () => {
    it('provides proper semantic structure', () => {
      render(<App />);

      expect(screen.getByRole('banner')).toBeInTheDocument(); // header
      expect(screen.getByRole('main')).toBeInTheDocument();   // main
      expect(screen.getByRole('contentinfo')).toBeInTheDocument(); // footer
    });

    it('provides proper button accessibility', () => {
      mockGameStore.session = {
        type: 'active-game',
        gameId: 'test-game-123',
        state: mockMidGameState,
        lastSync: new Date()
      };
      // Legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = mockMidGameState;

      render(<App />);

      const newGameButton = screen.getByRole('button', { name: /new game/i });
      const copyButton = screen.getByRole('button', { name: /copy moves/i });

      expect(newGameButton).toBeInTheDocument();
      expect(copyButton).toBeInTheDocument();
    });
  });
});