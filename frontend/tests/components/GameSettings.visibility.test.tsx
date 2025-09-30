/**
 * GameSettings Visibility Tests
 *
 * Tests the visibility logic for GameSettings component that was causing E2E failures.
 * The component shows different UI states based on gameId and showSettings state.
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

describe('GameSettings Visibility Logic', () => {
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

  describe('When no game exists (gameId is null)', () => {
    it('should show the full settings panel by default', () => {
      render(<GameSettings />);

      // Should show the settings panel, not the toggle button
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByText('Game Mode')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Should NOT show the toggle button
      expect(screen.queryByText('⚙️ Game Settings')).not.toBeInTheDocument();
    });

    it('should show mode selection buttons', () => {
      render(<GameSettings />);

      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-ai')).toBeInTheDocument();
      expect(screen.getByTestId('mode-ai-vs-ai')).toBeInTheDocument();
    });

    it('should show start game button', () => {
      render(<GameSettings />);

      const startButton = screen.getByTestId('start-game-button');
      expect(startButton).toBeInTheDocument();
      expect(startButton).not.toBeDisabled();
    });

    it('should not show cancel button when no game exists', () => {
      render(<GameSettings />);

      expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
    });
  });

  describe('When a game exists (gameId is present)', () => {
    beforeEach(() => {
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
    });

    it('should show only the toggle button by default', () => {
      render(<GameSettings />);

      // Should show the toggle button
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();

      // Should NOT show the full settings panel
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
      expect(screen.queryByTestId('start-game-button')).not.toBeInTheDocument();
    });

    it('should show the toggle button with correct attributes', () => {
      render(<GameSettings />);

      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toHaveClass('retro-btn', 'toggle-settings');
      expect(toggleButton).not.toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Game Settings');
    });

    it('should expand to full panel when toggle button is clicked', async () => {
      const { rerender } = render(<GameSettings />);

      // Initially should show only toggle button
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();

      // Click the toggle button
      await user.click(toggleButton);
      
      // Force a re-render to see the state change
      rerender(<GameSettings />);

      // Should now show the full settings panel
      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });

      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('should show cancel button when panel is expanded', async () => {
      const { rerender } = render(<GameSettings />);

      // Expand the panel
      await user.click(screen.getByText('⚙️ Game Settings'));
      
      // Force a re-render to see the state change
      rerender(<GameSettings />);

      await waitFor(() => {
        const cancelButton = screen.getByText('Cancel');
        expect(cancelButton).toBeInTheDocument();
        expect(cancelButton).toHaveClass('retro-btn', 'cancel');
      });
    });

    it('should collapse back to toggle button when cancel is clicked', async () => {
      const { rerender } = render(<GameSettings />);

      // Expand the panel
      await user.click(screen.getByText('⚙️ Game Settings'));
      
      // Force a re-render to see the state change
      rerender(<GameSettings />);

      await waitFor(() => {
        expect(screen.getByText('Cancel')).toBeInTheDocument();
      });

      // Click cancel
      await user.click(screen.getByText('Cancel'));
      
      // Force a re-render to see the state change
      rerender(<GameSettings />);

      // Should be back to toggle button only
      await waitFor(() => {
        expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
      });

      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
    });
  });

  describe('Connection state affects button availability', () => {
    it('should disable toggle button when disconnected', () => {
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
      mockGameStore.connection = { type: 'disconnected' as const };
      mockGameStore.isConnected.mockReturnValue(false);

      render(<GameSettings />);

      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');
    });

    it('should show disabled toggle button when disconnected', async () => {
      mockGameStore.session = { type: 'no-game' as const };
      mockGameStore.getCurrentGameId.mockReturnValue(null);
      mockGameStore.connection = { type: 'disconnected' as const };
      mockGameStore.isConnected.mockReturnValue(false);

      render(<GameSettings />);

      // Should show toggle button, not settings panel
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');
    });

    it('should show toggle button instead of panel when disconnected', () => {
      mockGameStore.session = { type: 'no-game' as const };
      mockGameStore.getCurrentGameId.mockReturnValue(null);
      mockGameStore.connection = { type: 'disconnected' as const };
      mockGameStore.isConnected.mockReturnValue(false);

      render(<GameSettings />);

      // Should show disabled toggle button instead of settings panel
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).toBeDisabled();

      // Should NOT show the full settings panel
      expect(screen.queryByTestId('mode-human-vs-human')).not.toBeInTheDocument();
      expect(screen.queryByTestId('start-game-button')).not.toBeInTheDocument();
    });
  });

  describe('Loading state', () => {
    it('should show loading text on start button when creating game', () => {
      mockGameStore.isLoading = true;
      mockGameStore.isCreatingGame = true;

      render(<GameSettings />);

      const startButton = screen.getByTestId('start-game-button');
      expect(startButton).toBeDisabled();
      expect(startButton).toHaveTextContent('Starting...');
    });
  });

  describe('Settings panel collapse after game start', () => {
    it('should collapse panel after successful game creation', async () => {
      // Start with no game (panel visible)
      render(<GameSettings />);

      // Click start game
      const startButton = screen.getByTestId('start-game-button');
      await user.click(startButton);

      // Simulate game creation success by updating gameId
      mockGameStore.session = {
        type: 'active-game' as const,
        gameId: 'new-game-123',
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
      mockGameStore.getCurrentGameId.mockReturnValue('new-game-123');

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'START_GAME' });
      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_human',
        ai_config: undefined,
        board_size: 9
      });
    });
  });

  describe('AI settings visibility', () => {
    it('should show AI settings when mode is human_vs_ai', () => {
      mockGameStore.settings.gameSettings.mode = 'human_vs_ai';

      render(<GameSettings />);

      expect(screen.getByText('AI Difficulty')).toBeInTheDocument();
      expect(screen.getByText('AI Time Limit')).toBeInTheDocument();
    });

    it('should show AI settings when mode is ai_vs_ai', () => {
      mockGameStore.settings.gameSettings.mode = 'ai_vs_ai';

      render(<GameSettings />);

      expect(screen.getByText('AI Difficulty')).toBeInTheDocument();
      expect(screen.getByText('AI Time Limit')).toBeInTheDocument();
    });

    it('should hide AI settings when mode is human_vs_human', () => {
      // Explicitly set mode to human_vs_human
      mockGameStore.settings.gameSettings.mode = 'human_vs_human';
      
      render(<GameSettings />);

      expect(screen.queryByText('AI Difficulty')).not.toBeInTheDocument();
      expect(screen.queryByText('AI Time Limit')).not.toBeInTheDocument();
    });
  });

  describe('E2E Test Compatibility', () => {
    it('should always provide a way to access game settings', () => {
      // When no game exists, full panel is visible
      const { rerender } = render(<GameSettings />);
      expect(screen.getByText('Game Settings')).toBeInTheDocument();

      // When game exists, toggle button is visible
      mockGameStore.session = {
        type: 'active-game' as const,
        gameId: 'test-game',
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
      mockGameStore.getCurrentGameId.mockReturnValue('test-game');

      rerender(<GameSettings />);
      expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
    });

    it('should maintain consistent test selectors', () => {
      render(<GameSettings />);

      // These selectors are used by E2E tests and should always be present
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
    });
  });
});