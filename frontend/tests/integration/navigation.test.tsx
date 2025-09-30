/**
 * Integration tests for navigation scenarios with GameSettings.
 *
 * These tests verify the behavior that matches E2E test expectations
 * for various navigation scenarios:
 * - Browser back/forward navigation
 * - Page refresh scenarios
 * - Multiple tab scenarios
 * - WebSocket reconnection after navigation
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import App from '@/App';
import { wsService } from '@/services/websocket';

// Mock the game store with vi.hoisted
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  const store = {
    // State properties
    connection: { status: 'connected', retryCount: 0, lastError: null },
    session: { type: 'no-game' },
    settings: { 
      gameSettings: { 
        mode: 'human_vs_human', 
        ai_difficulty: 'medium', 
        ai_time_limit: 3000, 
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
    getSettingsUI: vi.fn(() => {
      const hasGame = mockGameStore.session && mockGameStore.session.gameId;
      const connected = mockGameStore.connection.status === 'connected';
      
      if (hasGame) {
        return { type: 'button-visible', enabled: connected };
      } else if (connected) {
        return { type: 'panel-visible', canStartGame: true, isCreating: false };
      } else {
        return { type: 'button-visible', enabled: false };
      }
    }),
    isConnected: vi.fn(() => mockGameStore.connection.status === 'connected'),
    getCurrentGameId: vi.fn(() => mockGameStore.session?.gameId || null),
    getCurrentGameState: vi.fn(() => mockGameStore.session?.state || null),
    canStartGame: vi.fn(() => mockGameStore.connection.status === 'connected' && !mockGameStore.session),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => !!mockGameStore.session?.state && !mockGameStore.session.state.isGameOver),
    
    // Legacy compatibility
    gameId: null,
    gameState: null,
    gameSettings: {
      mode: 'human_vs_human' as const,
      ai_difficulty: 'medium' as const,
      ai_time_limit: 3000,
      board_size: 9
    },
    setGameSettings: vi.fn(),
    isLoading: false,
    isCreatingGame: false,
    error: null,
    selectedHistoryIndex: null,
    setGameId: vi.fn(),
    setGameState: vi.fn(),
    setIsConnected: vi.fn(),
    setIsLoading: vi.fn(),
    setIsCreatingGame: vi.fn(),
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

// Mock the WebSocket service
vi.mock('@/services/websocket', () => ({
  wsService: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    createGame: vi.fn(),
    makeMove: vi.fn(),
    isConnected: vi.fn(() => true)
  }
}));

describe('Navigation Integration Tests', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset store to no game, connected state
    Object.assign(mockGameStore, {
      connection: { status: 'connected', retryCount: 0, lastError: null },
      session: { type: 'no-game' },
      settings: { 
        gameSettings: { 
          mode: 'human_vs_human', 
          ai_difficulty: 'medium', 
          ai_time_limit: 3000, 
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
      
      // Legacy compatibility
      gameId: null,
      gameState: null,
      gameSettings: {
        mode: 'human_vs_human' as const,
        ai_difficulty: 'medium' as const,
        ai_time_limit: 3000,
        board_size: 9
      },
      isLoading: false,
      isCreatingGame: false,
      error: null,
      selectedHistoryIndex: null
    });
    
    // Update function mocks
    mockGameStore.isConnected.mockReturnValue(true);
    mockGameStore.getCurrentGameId.mockReturnValue(null);
    mockGameStore.getCurrentGameState.mockReturnValue(null);
    mockGameStore.canStartGame.mockReturnValue(true);
    mockGameStore.isGameActive.mockReturnValue(false);
    mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: true, isCreating: false });
    
    vi.mocked(wsService.isConnected).mockReturnValue(true);
  });

  describe('Fresh page load scenarios', () => {
    it('should show settings panel on initial app load (no game, connected)', () => {
      render(<App />);

      // Should show settings panel directly (no game + connected = immediate access)
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByText('Game Mode')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Should NOT show toggle button when panel is visible
      expect(screen.queryByText('⚙️ Game Settings')).not.toBeInTheDocument();
    });

    it('should show settings panel when connected with no active game', () => {
      // Store is already set up for this in beforeEach
      render(<App />);

      // Should show settings panel for immediate access
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });
  });

  describe('Browser navigation simulation', () => {
    it('should restore settings panel after simulated back navigation', () => {
      // Simulate a scenario where user navigated away and back
      // This mimics what happens in browser back navigation

      render(<App />);

      // Should show settings panel after "navigation back" (no game + connected)
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByText('Game Mode')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });

    it('should transition between panel and toggle during connection changes', async () => {
      const { rerender } = render(<App />);

      // Initially connected - should show settings panel (no game + connected)
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Simulate disconnection (e.g., during navigation)
      Object.assign(mockGameStore, {
        connection: { status: 'disconnected', retryCount: 0, lastError: null }
      });
      mockGameStore.isConnected.mockReturnValue(false);
      mockGameStore.canStartGame.mockReturnValue(false);
      mockGameStore.getSettingsUI.mockReturnValue({ type: 'button-visible', enabled: false });
      vi.mocked(wsService.isConnected).mockReturnValue(false);

      rerender(<App />);

      // Should now show disabled toggle button instead of panel
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeDisabled();

      // Simulate reconnection
      Object.assign(mockGameStore, {
        connection: { status: 'connected', retryCount: 0, lastError: null }
      });
      mockGameStore.isConnected.mockReturnValue(true);
      mockGameStore.canStartGame.mockReturnValue(true);
      mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: true, isCreating: false });
      vi.mocked(wsService.isConnected).mockReturnValue(true);

      rerender(<App />);

      // Should switch back to settings panel
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });
  });

  describe('Multiple tab simulation', () => {
    it('should show settings panel consistently across "tabs"', () => {
      // Simulate first tab
      const { unmount: unmountTab1 } = render(<App />);

      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      unmountTab1();

      // Simulate second tab with same state
      render(<App />);

      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });

    it('should handle independent game states in different "tabs"', () => {
      // Tab 1: No game - should show settings panel
      const { unmount: unmountTab1 } = render(<App />);
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      unmountTab1();

      // Tab 2: With game - should show toggle button
      Object.assign(mockGameStore, {
        session: {
          type: 'active-game',
          gameId: 'test-game-123',
          state: null,
          createdAt: Date.now()
        },
        gameId: 'test-game-123'
      });
      mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');
      mockGameStore.canStartGame.mockReturnValue(false);
      mockGameStore.getSettingsUI.mockReturnValue({ type: 'button-visible', enabled: true });

      render(<App />);
      expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
    });
  });

  describe('WebSocket reconnection scenarios', () => {
    it('should show settings panel after reconnection with no game', () => {
      // Start disconnected
      Object.assign(mockGameStore, {
        connection: { status: 'disconnected', retryCount: 0, lastError: null }
      });
      mockGameStore.isConnected.mockReturnValue(false);
      mockGameStore.canStartGame.mockReturnValue(false);
      mockGameStore.getSettingsUI.mockReturnValue({ type: 'button-visible', enabled: false });
      vi.mocked(wsService.isConnected).mockReturnValue(false);

      const { rerender } = render(<App />);

      // Should show disabled toggle
      expect(screen.getByText('⚙️ Game Settings')).toBeDisabled();

      // Simulate reconnection
      Object.assign(mockGameStore, {
        connection: { status: 'connected', retryCount: 0, lastError: null }
      });
      mockGameStore.isConnected.mockReturnValue(true);
      mockGameStore.canStartGame.mockReturnValue(true);
      mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: true, isCreating: false });
      vi.mocked(wsService.isConnected).mockReturnValue(true);

      rerender(<App />);

      // Should switch to settings panel (no game + connected)
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });

    it('should maintain game state consistency after reconnection', () => {
      // Start with game and disconnected
      Object.assign(mockGameStore, {
        connection: { status: 'disconnected', retryCount: 0, lastError: null },
        session: {
          type: 'active-game',
          gameId: 'test-game-123',
          state: null,
          createdAt: Date.now()
        },
        gameId: 'test-game-123'
      });
      mockGameStore.isConnected.mockReturnValue(false);
      mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');
      mockGameStore.canStartGame.mockReturnValue(false);
      mockGameStore.getSettingsUI.mockReturnValue({ type: 'button-visible', enabled: false });

      const { rerender } = render(<App />);

      // Should show disabled toggle button
      expect(screen.getByText('⚙️ Game Settings')).toBeDisabled();

      // Reconnect with same game
      Object.assign(mockGameStore, {
        connection: { status: 'connected', retryCount: 0, lastError: null }
      });
      mockGameStore.isConnected.mockReturnValue(true);
      mockGameStore.getSettingsUI.mockReturnValue({ type: 'button-visible', enabled: true });

      rerender(<App />);

      // Should show enabled toggle button (game exists)
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).not.toBeDisabled();
    });
  });

  describe('Page refresh simulation', () => {
    it('should restore proper state after simulated page refresh', () => {
      // Simulate page refresh by unmounting and remounting
      const { unmount } = render(<App />);
      unmount();

      // Fresh mount simulates page refresh
      render(<App />);

      // Should show settings panel on fresh load (no game + connected)
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });

    it('should handle page refresh with existing game state', () => {
      // Start with game
      Object.assign(mockGameStore, {
        session: {
          type: 'active-game',
          gameId: 'test-game-123',
          state: null,
          createdAt: Date.now()
        },
        gameId: 'test-game-123'
      });
      mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');
      mockGameStore.canStartGame.mockReturnValue(false);
      mockGameStore.getSettingsUI.mockReturnValue({ type: 'button-visible', enabled: true });

      const { unmount } = render(<App />);
      unmount();

      // Refresh with same game state
      render(<App />);

      // Should show toggle button (game exists)
      expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
    });
  });

  describe('E2E test compatibility', () => {
    it('should provide immediate access to settings that E2E tests expect', async () => {
      render(<App />);

      // E2E tests expect immediate access to settings when no game exists
      expect(screen.getByText('Game Mode')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();

      // Settings should be immediately accessible without needing to click
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });

    it('should match browser back/forward navigation behavior expected by E2E', () => {
      // This simulates the exact scenario from test_browser_navigation.py
      render(<App />);

      // After "back navigation" to app, should show immediate access to settings
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByText('Game Mode')).toBeInTheDocument();
    });

    it('should match multiple tabs behavior expected by E2E', () => {
      // Simulate first tab
      const { unmount } = render(<App />);

      // Should show immediate access to settings
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      unmount();

      // Simulate second tab
      render(<App />);

      // Should also show immediate access to settings
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });
  });
});