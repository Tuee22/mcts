import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the game store first with vi.hoisted (same pattern as other tests)
// Mock the game store first with vi.hoisted
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
    session: {
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
    },
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
    getSettingsUI: vi.fn(() => {
      // When there's a game, show the toggle button
      // When there's no game and connected, show the panel
      const hasGame = mockGameStore.session && (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-over');
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
    getCurrentGameId: vi.fn(() => 'test-game-123'),
    getCurrentGameState: vi.fn(() => null),
    canStartGame: vi.fn(() => false),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => false),
    
    // Legacy compatibility
    gameId: 'test-game-123',
    gameState: null,
    gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
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
  wsService: {
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
  }
}));

// Import components and utilities
import { GameSettings } from '@/components/GameSettings';
import { render, screen, createUser } from '../utils/testHelpers';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';

describe('GameSettings Component', () => {

  beforeEach(() => {
    vi.clearAllMocks();

    // Reset the game store state for each test
    mockGameStore.connection = { type: 'connected' as const, clientId: 'test-client', since: new Date(), canReset: true };
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
    mockGameStore.isLoading = false;
    mockGameStore.error = null;
    
    // Reset mock return values
    mockGameStore.isConnected.mockReturnValue(true);
    mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');
    mockGameStore.getCurrentGameState.mockReturnValue(null);
    mockGameStore.canStartGame.mockReturnValue(false);
  });

  // Helper function to expand settings panel (assumes component is already rendered with toggle button)
  const expandSettings = async () => {
    const user = createUser();
    const toggleButton = screen.getByRole('button', { name: /game settings/i });
    await user.click(toggleButton);
  };

  describe('Basic Rendering', () => {
    it('renders game settings panel when no game is active', () => {
      // When gameId is null, settings panel should be shown directly
      mockGameStore.session = { type: 'no-game' as const };
      mockGameStore.getCurrentGameId.mockReturnValue(null);
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'panel-visible',
        canStartGame: true,
      });
      render(<GameSettings />);

      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByText('Game Mode')).toBeInTheDocument();
    });

    it('renders game settings toggle button when game is active', () => {
      // Set up active game state to show toggle button instead of panel
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
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'button-visible',
        enabled: true
      });

      render(<GameSettings />);

      const toggleButton = screen.getByRole('button', { name: /game settings/i });
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).toHaveTextContent('⚙️ Game Settings');
    });

    it('expands settings panel when clicked', async () => {
      // Set up active game state to show toggle button first
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
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'button-visible',
        enabled: true
      });

      render(<GameSettings />);
      const user = createUser();

      const toggleButton = screen.getByRole('button', { name: /game settings/i });
      await user.click(toggleButton);
      
      // Dispatch should be called to toggle settings
      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'SETTINGS_TOGGLED' });
    });

    it('renders all game mode options directly', () => {
      // When gameId is null, settings panel shows directly (no need to expand)
      mockGameStore.session = { type: 'no-game' as const };
      mockGameStore.getCurrentGameId.mockReturnValue(null);
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'panel-visible',
        canStartGame: true,
      });
      render(<GameSettings />);

      // Use test IDs for reliable element selection
      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-ai')).toBeInTheDocument();
      expect(screen.getByTestId('mode-ai-vs-ai')).toBeInTheDocument();

      // Check text content
      expect(screen.getByText('Human vs Human')).toBeInTheDocument();
      expect(screen.getByText('Human vs AI')).toBeInTheDocument();
      expect(screen.getByText('AI vs AI')).toBeInTheDocument();
    });

    it('renders difficulty options when AI mode is selected', () => {
      // Update mock store for AI mode
      mockGameStore.session = { type: 'no-game' as const };
      mockGameStore.getCurrentGameId.mockReturnValue(null);
      mockGameStore.settings.gameSettings = { ...mockDefaultGameSettings, mode: 'human_vs_ai' };
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'panel-visible',
        canStartGame: true,
      });

      render(<GameSettings />);

      expect(screen.getByText('Easy')).toBeInTheDocument();
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(screen.getByText('Hard')).toBeInTheDocument();
      expect(screen.getByText('Expert')).toBeInTheDocument();
    });
  });

  describe('Game Mode Selection', () => {
    it('highlights currently selected mode', () => {
      // Set up store with specific mode
      mockGameStore.session = { type: 'no-game' as const };
      mockGameStore.getCurrentGameId.mockReturnValue(null);
      mockGameStore.settings.gameSettings = { ...mockDefaultGameSettings, mode: 'human_vs_ai' };
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'panel-visible',
        canStartGame: true,
      });

      render(<GameSettings />);

      const humanVsAIButton = screen.getByTestId('mode-human-vs-ai');
      expect(humanVsAIButton).toHaveClass('active');
    });

    it('changes mode when clicked', async () => {
      mockGameStore.session = { type: 'no-game' as const };
      mockGameStore.getCurrentGameId.mockReturnValue(null);
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'panel-visible',
        canStartGame: true,
      });
      render(<GameSettings />);
      const user = createUser();

      const humanVsHumanButton = screen.getByTestId('mode-human-vs-human');
      await user.click(humanVsHumanButton);

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'SETTINGS_UPDATED', settings: { mode: 'human_vs_human' } });
    });
  });

  describe('Difficulty Selection', () => {
    beforeEach(() => {
      // Set up AI mode for difficulty tests
      mockGameStore.session = { type: 'no-game' as const };
      mockGameStore.getCurrentGameId.mockReturnValue(null);
      mockGameStore.settings.gameSettings = { ...mockDefaultGameSettings, mode: 'human_vs_ai' };
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'panel-visible',
        canStartGame: true,
      });
    });

    it('highlights currently selected difficulty', async () => {
      render(<GameSettings />);

      const mediumButton = screen.getByText('Medium');
      expect(mediumButton).toHaveClass('active');
    });

    it('changes difficulty when clicked', async () => {
      render(<GameSettings />);
      const user = createUser();

      const hardButton = screen.getByText('Hard');
      await user.click(hardButton);

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'SETTINGS_UPDATED', settings: { ai_difficulty: 'hard' } });
    });
  });

  describe('Connection Status', () => {
    it('shows disabled toggle button when not connected', () => {
      mockGameStore.connection = { type: 'disconnected' as const, canReset: true };
      mockGameStore.isConnected.mockReturnValue(false);
      mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'button-visible',
        enabled: false
      });

      render(<GameSettings />);

      // When disconnected and no gameId, shows disabled toggle button (prevents race conditions)
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');

      // Should NOT show the full settings panel
      expect(screen.queryByTestId('connection-warning')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mode-human-vs-human')).not.toBeInTheDocument();
      expect(screen.queryByTestId('start-game-button')).not.toBeInTheDocument();
    });

    it('disables toggle button when not connected and game is active', () => {
      mockGameStore.connection = { type: 'disconnected' as const, canReset: true };
      mockGameStore.isConnected.mockReturnValue(false);
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
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'button-visible',
        enabled: false
      });

      render(<GameSettings />);

      const toggleButton = screen.getByRole('button', { name: /game settings/i });
      expect(toggleButton).toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');
    });

    it('enables all controls when connected', async () => {
      mockGameStore.connection = { type: 'connected' as const, clientId: 'test-client', since: new Date(), canReset: true };
      mockGameStore.isConnected.mockReturnValue(true);
      mockGameStore.session = { type: 'no-game' as const };
      mockGameStore.getCurrentGameId.mockReturnValue(null);
      mockGameStore.getSettingsUI.mockReturnValue({
        type: 'panel-visible',
        canStartGame: true,
      });

      render(<GameSettings />);

      const humanVsHumanButton = screen.getByTestId('mode-human-vs-human');
      expect(humanVsHumanButton).not.toBeDisabled();
    });
  });
});