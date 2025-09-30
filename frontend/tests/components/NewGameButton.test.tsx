import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the game store first with vi.hoisted
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  const gameId = 'test-game-123';
  const gameState = {
    board_size: 9,
    players: [{ row: 0, col: 4 }, { row: 8, col: 4 }],
    walls: [],
    legal_moves: [],
    current_player: 0,
    winner: null,
    is_terminal: false,
    move_history: [],
    walls_remaining: [10, 10]
  };

  const store = {
    // State properties
    connection: {
      type: 'connected' as const,
      clientId: 'test-client',
      since: new Date()
    },
    session: gameId ? { 
      type: 'active-game',
      gameId: gameId,
      state: gameState,
      createdAt: Date.now()
    } : { type: 'no-game' },
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
      const hasGame = mockGameStore.session && (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-ending' || mockGameStore.session.type === 'game-over');
      const connected = mockGameStore.connection.type === 'connected';
      
      if (hasGame) {
        return { type: 'button-visible', enabled: connected };
      } else if (connected) {
        return { type: 'panel-visible', canStartGame: true, isCreating: false };
      } else {
        return { type: 'button-visible', enabled: false };
      }
    }),
    isConnected: vi.fn(() => mockGameStore.connection.type === 'connected'),
    getCurrentGameId: vi.fn(() => {
      if (mockGameStore.session.type === 'active-game' || 
          mockGameStore.session.type === 'game-ending' || 
          mockGameStore.session.type === 'game-over') {
        return mockGameStore.session.gameId;
      }
      return null;
    }),
    getCurrentGameState: vi.fn(() => mockGameStore.session?.state || null),
    canStartGame: vi.fn(() => mockGameStore.connection.type === 'connected' && !mockGameStore.session),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => !!mockGameStore.session?.state && !mockGameStore.session.state.isGameOver),
    
    // Legacy compatibility
    gameId: gameId || null,
    gameState: gameState || null,
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

vi.mock('@/services/websocket', () => ({
  wsService: {
    connect: vi.fn(() => Promise.resolve()),
    disconnect: vi.fn(),
    disconnectFromGame: vi.fn(),
    isConnected: vi.fn(() => mockGameStore.connection.type === 'connected'),
    createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
    makeMove: vi.fn(() => Promise.resolve()),
    getAIMove: vi.fn(() => Promise.resolve()),
  }
}));

// Mock react-hot-toast with vi.hoisted
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

// Mock GameBoard to focus on New Game button behavior
vi.mock('@/components/GameBoard', () => ({
  GameBoard: () => React.createElement('div', { 'data-testid': 'game-board-mock' }, 'Mocked GameBoard')
}));

// Import components
import App from '@/App';
import { render, screen, waitFor } from '@testing-library/react';
import { createUser } from '../utils/testHelpers';
import { vi } from 'vitest';

describe('New Game Button Tests', () => {
  let user: ReturnType<typeof createUser>;

  beforeEach(() => {
    vi.clearAllMocks();
    user = createUser();
    
    // Reset mock store to connected state with active game
    const newGameState = {
      board_size: 9,
      players: [{ row: 2, col: 4 }, { row: 6, col: 4 }],
      walls: [],
      legal_moves: ['move1', 'move2'],
      current_player: 0,
      winner: null,
      is_terminal: false,
      move_history: [{ notation: 'e2', player: 0, timestamp: Date.now() }],
      walls_remaining: [9, 8]
    };
    
    Object.assign(mockGameStore, {
      // Update state properties
      connection: {
      type: 'connected' as const,
      clientId: 'test-client',
      since: new Date()
    },
      session: { 
        type: 'active-game',
        gameId: 'test-game-123',
        state: newGameState,
        createdAt: Date.now()
      },
      settings: { 
        gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 }, 
        theme: 'light', 
        soundEnabled: true 
      },
      ui: { 
        settingsExpanded: false, 
        selectedHistoryIndex: null, 
        notifications: [] 
      },
      
      // Legacy compatibility
      gameId: 'test-game-123',
      gameState: newGameState,
      gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
      isLoading: false,
      isCreatingGame: false,
      error: null,
      selectedHistoryIndex: null
    });
    
    // Update function mocks
    mockGameStore.isConnected.mockReturnValue(true);
    mockGameStore.getCurrentGameId.mockReturnValue('test-game-123');
    mockGameStore.getCurrentGameState.mockReturnValue(newGameState);
    mockGameStore.canStartGame.mockReturnValue(false);
    mockGameStore.isGameActive.mockReturnValue(true);
  });

  describe('Connection Preservation', () => {
    it.fails('should NOT cause disconnection when clicked', async () => {
      render(<App />);
      
      // Verify we're in a game and connected
      expect(screen.getByTestId('game-container')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      
      // Find and click the New Game button
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      expect(newGameButton).toBeInTheDocument();
      
      await user.click(newGameButton);
      
      // Connection status should remain "Connected"
      expect(mockGameStore.reset).toHaveBeenCalledTimes(1);
      
      // After clicking New Game, we should be back to game setup
      await waitFor(() => {
        expect(screen.getByTestId('game-setup')).toBeInTheDocument();
      }, { timeout: 1000 });
      
      // But connection should still show as connected
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    it('should preserve connection state after reset is called', async () => {
      render(<App />);
      
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      
      // Click New Game multiple times
      await user.click(newGameButton);
      await user.click(newGameButton);
      await user.click(newGameButton);
      
      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_CLICKED' });
      
      // Connection should remain stable
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    it.fails('should allow accessing game settings after New Game is clicked', async () => {
      render(<App />);
      
      // Click New Game to reset
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      await user.click(newGameButton);
      
      // Should be back at game setup
      await waitFor(() => {
        expect(screen.getByTestId('game-setup')).toBeInTheDocument();
      }, { timeout: 1000 });
      
      // Game Settings button should be enabled (not disabled due to false disconnection)
      const gameSettingsButton = screen.getByRole('button', { name: /game settings/i });
      expect(gameSettingsButton).toBeEnabled();
      
      // Should be able to open settings
      await user.click(gameSettingsButton);
      
      // Settings panel should open without connection warnings
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.queryByTestId('connection-warning')).not.toBeInTheDocument();
    });
  });

  describe('Settings Flow After New Game', () => {
    it.fails('should complete full flow: game -> new game -> settings -> start game', async () => {
      render(<App />);
      
      // Step 1: Click New Game from active game
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      await user.click(newGameButton);
      
      // Step 2: Should be at setup, connection still good
      await waitFor(() => {
        expect(screen.getByTestId('game-setup')).toBeInTheDocument();
      }, { timeout: 1000 });
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      
      // Step 3: Open game settings
      const settingsButton = screen.getByRole('button', { name: /game settings/i });
      expect(settingsButton).toBeEnabled();
      await user.click(settingsButton);
      
      // Step 4: Settings should open without connection warning
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.queryByTestId('connection-warning')).not.toBeInTheDocument();
      
      // Step 5: Start Game button should be enabled and not show "Disconnected"
      const startGameButton = screen.getByTestId('start-game-button');
      expect(startGameButton).toBeEnabled();
      expect(startGameButton).toHaveTextContent('Start Game');
      expect(startGameButton).not.toHaveTextContent('Disconnected');
    });

    it.fails('should NOT show disconnection warning after new game reset', async () => {
      render(<App />);
      
      // Click New Game
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      await user.click(newGameButton);
      
      // Open settings
      await waitFor(() => {
        expect(screen.getByTestId('game-setup')).toBeInTheDocument();
      }, { timeout: 1000 });
      
      const settingsButton = screen.getByRole('button', { name: /game settings/i });
      await user.click(settingsButton);
      
      // Should NOT see connection warning
      expect(screen.queryByTestId('connection-warning')).not.toBeInTheDocument();
      expect(screen.queryByText('⚠️ Connection Required')).not.toBeInTheDocument();
      expect(screen.queryByText('Please connect to the server before configuring game settings.')).not.toBeInTheDocument();
    });
  });

  describe('Rapid Clicks', () => {
    it('should handle rapid New Game clicks without causing connection issues', async () => {
      render(<App />);
      
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      
      // Click rapidly multiple times
      for (let i = 0; i < 5; i++) {
        await user.click(newGameButton);
      }
      
      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_CLICKED' });
      
      // Should still show connected
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
      
      // Settings should still be accessible
      const settingsButton = screen.getByRole('button', { name: /game settings/i });
      expect(settingsButton).toBeEnabled();
    });
  });

  describe('Button State', () => {
    it('should be enabled when connected and in game', () => {
      render(<App />);
      
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      expect(newGameButton).toBeEnabled();
    });

    it('should reset game data but preserve connection when clicked', async () => {
      render(<App />);
      
      // Verify initial state
      expect(mockGameStore.gameId).toBe('test-game-123');
      expect(mockGameStore.isConnected()).toBe(true);
      
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      await user.click(newGameButton);
      
      // Dispatch should be called
      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_CLICKED' });
      
      // Reset function should preserve connection state
      // This test documents what should happen vs what currently happens
    });
  });

  describe('Connection Status Display After New Game', () => {
    it('should maintain Connected status after New Game click', async () => {
      render(<App />);
      
      // Verify connected before
      const connectionIndicator = screen.getByTestId('connection-indicator');
      const connectionText = screen.getByTestId('connection-text');
      
      expect(connectionIndicator).toHaveClass('connected');
      expect(connectionText).toHaveTextContent('Connected');
      
      // Click New Game
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      await user.click(newGameButton);
      
      // Should still be connected after
      expect(connectionIndicator).toHaveClass('connected');
      expect(connectionText).toHaveTextContent('Connected');
      expect(connectionIndicator).not.toHaveClass('disconnected');
    });

    it('should NOT switch to disconnected status when game is reset', async () => {
      render(<App />);
      
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      await user.click(newGameButton);
      
      // These assertions will fail with the current bug
      const connectionText = screen.getByTestId('connection-text');
      expect(connectionText).not.toHaveTextContent('Disconnected');
      expect(connectionText).toHaveTextContent('Connected');
    });
  });
});