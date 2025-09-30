/**
 * GameSettings component tests for E2E-compatible behavior.
 *
 * These tests verify the behavior that ensures settings are always accessible:
 * - Panel shows when no game exists and connected (immediate access)
 * - Toggle button shows when game exists or disconnected (consistent access)
 * - Settings are never completely inaccessible (E2E requirement)
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { GameSettings } from '@/components/GameSettings';

// Mock the game store first with vi.hoisted
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  // Create mock store inline to avoid import issues with hoisting
  const store = {
    // State properties
    connection: {
      type: 'connected' as const,
      clientId: 'test-client',
      since: new Date()
    },
    session: { type: 'no-game' as const },
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
    dispatch: vi.fn((action) => {
      // Simulate actual state updates for relevant actions
      if (action.type === 'SETTINGS_TOGGLED') {
        mockGameStore.ui.settingsExpanded = !mockGameStore.ui.settingsExpanded;
      } else if (action.type === 'START_GAME') {
        mockGameStore.isLoading = true;
        mockGameStore.isCreatingGame = true;
      }
    }),
    getSettingsUI: () => {
      // Replicate the actual getSettingsUIState logic
      const hasGame = mockGameStore.session && (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-ending' || mockGameStore.session.type === 'game-over');
      const connected = mockGameStore.connection.type === 'connected';
      
      // If settings are explicitly expanded, show panel
      if (mockGameStore.ui.settingsExpanded) {
        const isCreating = mockGameStore.isLoading && mockGameStore.isCreatingGame;
        const canStart = connected && !hasGame;
        return { type: 'panel-visible', canStartGame: canStart, isCreating };
      }
      
      // Otherwise, determine based on session state
      if (hasGame) {
        return {
          type: 'button-visible',
          enabled: connected
        };
      } else if (connected) {
        return {
          type: 'panel-visible',
          canStartGame: true,
          isCreating: mockGameStore.isLoading && mockGameStore.isCreatingGame
        };
      } else {
        return {
          type: 'button-visible',
          enabled: false
        };
      }
    },
    isConnected: vi.fn(() => mockGameStore.connection.type === 'connected'),
    getCurrentGameId: vi.fn(() => {
      if (mockGameStore.session.type === 'active-game' || 
          mockGameStore.session.type === 'game-ending' || 
          mockGameStore.session.type === 'game-over') {
        return mockGameStore.session.gameId;
      }
      return null;
    }),
    getCurrentGameState: vi.fn(() => null),
    canStartGame: vi.fn(() => {
      const connected = mockGameStore.connection.type === 'connected';
      const hasGame = mockGameStore.session && (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-ending' || mockGameStore.session.type === 'game-over');
      return connected && !hasGame;
    }),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => false),
    
    // Legacy compatibility
    gameId: null,
    gameState: null,
    gameSettings: { mode: 'human_vs_human', ai_difficulty: 'medium', ai_time_limit: 3000, board_size: 9 },
    isLoading: false,
    isCreatingGame: false,
    error: null,
    selectedHistoryIndex: null,
    // setGameId removed - use dispatch,
    // setGameState removed - use dispatch,
    setGameSettings: vi.fn(),
    // setIsConnected removed - use dispatch,
    // setIsLoading removed - use dispatch,
    // setIsCreatingGame removed - use dispatch,
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

const mockWsService = vi.hoisted(() => ({
  connect: vi.fn(() => Promise.resolve()),
  disconnect: vi.fn(),
  disconnectFromGame: vi.fn(),
  isConnected: vi.fn(() => mockGameStore.connection.type === 'connected'),
  createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
  makeMove: vi.fn(() => Promise.resolve()),
  getAIMove: vi.fn(() => Promise.resolve()),
  joinGame: vi.fn(),
  requestGameState: vi.fn(() => Promise.resolve()),
  connectToGame: vi.fn(),
}));

vi.mock('@/services/websocket', () => ({
  wsService: mockWsService
}));

// Import components and utilities
import { createUser } from '../utils/testHelpers';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';

describe('GameSettings - E2E Compatible Behavior', () => {
  let user: ReturnType<typeof createUser>;

  beforeEach(() => {
    vi.clearAllMocks();
    user = createUser();
    
    // Reset the game store state for each test
    mockGameStore.connection = { type: 'connected' as const, clientId: 'test-client', since: new Date() };
    mockGameStore.session = {
      gameId: null,
      gameState: null,
      createdAt: Date.now()
    };
    mockGameStore.ui.settingsExpanded = false;
    mockGameStore.isLoading = false;
    mockGameStore.isCreatingGame = false;
    mockGameStore.error = null;
    
    // Reset mock return values
    mockGameStore.isConnected.mockReturnValue(true);
    mockGameStore.getCurrentGameId.mockReturnValue(null);
    mockGameStore.getCurrentGameState.mockReturnValue(null);
    // Don't override getSettingsUI - let it use the dynamic function
  });

  describe('Initial render behavior', () => {
    it('should show settings panel when no game exists and connected', () => {
      render(<GameSettings />);

      // Should show the settings panel for immediate access
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByText('Game Mode')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Should NOT show the toggle button when panel is visible
      expect(screen.queryByText('⚙️ Game Settings')).not.toBeInTheDocument();
    });

    it('should show toggle button when no game exists but disconnected', () => {
      mockGameStore.connection = { type: 'disconnected' as const };
      mockGameStore.isConnected.mockReturnValue(false);

      render(<GameSettings />);

      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');
      expect(toggleButton).toHaveAttribute('data-testid', 'settings-toggle-button');

      // Should NOT show the settings panel when disconnected
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
      expect(screen.queryByTestId('start-game-button')).not.toBeInTheDocument();
    });

    it('should show toggle button when game exists', () => {
      mockGameStore.session = {
        type: 'active-game' as const,
        gameId: 'test-game-123',
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      };
      mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');

      render(<GameSettings />);

      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).not.toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Game Settings');

      // Should NOT show the settings panel when game exists
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
      expect(screen.queryByTestId('start-game-button')).not.toBeInTheDocument();
    });
  });

  describe('Toggle button interaction', () => {
    it('should expand to full settings panel when toggle button is clicked (game exists)', async () => {
      // Set up scenario where toggle button is shown (game exists)
      mockGameStore.session = {
        type: 'active-game' as const,
        gameId: 'test-game-123',
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      };
      mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');

      const { rerender } = render(<GameSettings />);

      // Initially should show only toggle button when game exists
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();

      // Click the toggle button
      await user.click(toggleButton);
      
      // Force a re-render to see the state change
      rerender(<GameSettings />);

      // Should now show the full settings panel
      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });

      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-ai')).toBeInTheDocument();
      expect(screen.getByTestId('mode-ai-vs-ai')).toBeInTheDocument();
    });

    it('should show cancel button when expanding from game-exists state', async () => {
      // Set up scenario where toggle button is shown (game exists)
      mockGameStore.session = {
        type: 'active-game' as const,
        gameId: 'test-game-123',
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      };
      mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');

      const { rerender } = render(<GameSettings />);

      // Click to expand
      await user.click(screen.getByText('⚙️ Game Settings'));
      
      // Force a re-render to see the state change
      rerender(<GameSettings />);

      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });

      // Should show cancel button when game exists
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });
  });

  describe('Different game states', () => {
    it('should still show toggle button when a game exists', () => {
      mockGameStore.session = {
        type: 'active-game' as const,
        gameId: 'test-game-123',
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      };
      mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');

      render(<GameSettings />);

      // Should show toggle button even when game exists
      expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
    });

    it('should show cancel button when expanding with existing game', async () => {
      mockGameStore.session = {
        type: 'active-game' as const,
        gameId: 'test-game-123',
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      };
      mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');

      const { rerender } = render(<GameSettings />);

      // Click to expand
      await user.click(screen.getByText('⚙️ Game Settings'));
      
      // Force a re-render to see the state change
      rerender(<GameSettings />);

      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });

      // Should show cancel button when game exists
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });
  });

  describe('E2E compatibility scenarios', () => {
    it('should match E2E test expectations for fresh page load', () => {
      // Simulate fresh page load - no game, connected
      render(<GameSettings />);

      // E2E tests expect immediate access to settings - panel should be visible
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });

    it('should match E2E test expectations for browser navigation scenario', () => {
      // Simulate after browser back navigation - should be same as fresh load
      render(<GameSettings />);

      // E2E tests expect immediate access after navigation
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });

    it('should provide consistent test selectors for E2E tests', () => {
      render(<GameSettings />);

      // E2E tests rely on these selectors being immediately present when no game exists
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-ai')).toBeInTheDocument();
      expect(screen.getByTestId('mode-ai-vs-ai')).toBeInTheDocument();
    });
  });

  describe('Connection state transitions', () => {
    it('should transition from panel to toggle button during disconnection', () => {
      const { rerender } = render(<GameSettings />);

      // Initially connected with no game - should show settings panel
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Simulate disconnection
      mockGameStore.connection = { type: 'disconnected' as const };
      mockGameStore.isConnected.mockReturnValue(false);

      rerender(<GameSettings />);

      // Should now show disabled toggle button instead of panel
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');

      // Should not show settings panel during disconnection
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
    });
  });

  describe('Game creation flow', () => {
    it('should start with settings panel before game creation', async () => {
      render(<GameSettings />);

      // Should start with settings panel visible (no game, connected)
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Click start game directly (no expansion needed)
      await user.click(screen.getByTestId('start-game-button'));

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'START_GAME' });
      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_human',
        ai_config: undefined,
        board_size: 9
      });
    });
  });
});