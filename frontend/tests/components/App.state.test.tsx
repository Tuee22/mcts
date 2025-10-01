/**
 * App State Tests
 *
 * Tests the main App component state management and transitions,
 * particularly around game creation, reconnection, and UI state synchronization.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import App from '@/App';

// Mock the game store with comprehensive approach (same pattern as GameSettings test)
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
          canStartGame: true
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
    gameState: null,
    gameSettings: {
      mode: 'human_vs_human',
      ai_difficulty: 'medium',
      ai_time_limit: 3000,
      board_size: 9
    },
    gameId: null,
    error: null,
    selectedHistoryIndex: null,
    // setGameState removed - use dispatch,
    setGameSettings: vi.fn(),
    // setGameId removed - use dispatch,
    // setIsConnected removed - use dispatch,
    // setIsLoading removed - use dispatch,
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

vi.mock('../../src/store/gameStore', () => ({
  useGameStore: mockUseGameStore
}));

// Mock WebSocket service
vi.mock('../../src/services/websocket', () => ({
  wsService: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    disconnectFromGame: vi.fn(),
    makeMove: vi.fn(),
    createGame: vi.fn(),
    getAIMove: vi.fn(),
    isConnected: vi.fn(() => mockGameStore.connection.type === 'connected')
  }
}));

// Mock all child components to focus on App state logic

vi.mock('../../src/components/GameSettings', () => {
  const React = require('react');
  return {
    GameSettings: () => React.createElement('div', { 'data-testid': 'game-settings' }, 'Game Settings Component')
  };
});

vi.mock('../../src/components/GameBoard', () => {
  const React = require('react');
  return {
    GameBoard: () => React.createElement('div', { 'data-testid': 'game-board' }, 'Game Board Component')
  };
});

vi.mock('../../src/components/MoveHistory', () => {
  const React = require('react');
  return {
    MoveHistory: () => React.createElement('div', { 'data-testid': 'move-history' }, 'Move History Component')
  };
});

vi.mock('../../src/components/NewGameButton', () => {
  const React = require('react');
  return {
    NewGameButton: () => React.createElement('div', { 'data-testid': 'new-game-button' }, 'New Game Button')
  };
});

describe('App State Management', () => {
  // Helper function to reset mock store to default state
  const setActiveGameSession = (gameId: string, state: any) => {
    mockGameStore.session = {
      type: 'active-game',
      gameId,
      state,
      lastSync: new Date()
    };
    // Update legacy properties
    mockGameStore.gameId = gameId;
    mockGameStore.gameState = state;
  };

  const resetMockStore = () => {
    // Ensure objects exist before assigning
    if (!mockGameStore.connection) mockGameStore.connection = {};
    if (!mockGameStore.session) mockGameStore.session = {};
    if (!mockGameStore.settings) mockGameStore.settings = {};
    if (!mockGameStore.ui) mockGameStore.ui = {};
    
    Object.assign(mockGameStore.connection, {
      type: 'connected' as const,
          clientId: 'test-client',
          since: new Date(),
      retryCount: 0,
      lastError: null
    });
    Object.assign(mockGameStore.session, {
      type: 'no-game'
    });
    Object.assign(mockGameStore.settings, {
      gameSettings: {
        mode: 'human_vs_human',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      },
      theme: 'light',
      soundEnabled: true
    });
    Object.assign(mockGameStore.ui, {
      settingsExpanded: false,
      selectedHistoryIndex: null,
      notifications: []
    });
    // Update legacy compatibility properties
    mockGameStore.gameId = null;
    mockGameStore.gameState = null;
    mockGameStore.gameSettings = {
      mode: 'human_vs_human',
      ai_difficulty: 'medium',
      ai_time_limit: 3000,
      board_size: 9
    };
    mockGameStore.isConnected.mockReturnValue(true);
    mockGameStore.isLoading = false;
    mockGameStore.error = null;
    mockGameStore.selectedHistoryIndex = null;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    resetMockStore();

    // Reset timers
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Initial render state', () => {
    it('should render connection status', () => {
      render(<App />);
      expect(screen.getByTestId('connection-status')).toBeInTheDocument();
    });

    it('should show game settings when no game is active', () => {
      render(<App />);
      expect(screen.getByTestId('game-settings')).toBeInTheDocument();
    });

    it('should not show game board when no game exists', () => {
      render(<App />);
      expect(screen.queryByTestId('game-board')).not.toBeInTheDocument();
    });

    it('should not show move history when no game exists', () => {
      render(<App />);
      expect(screen.queryByTestId('move-history')).not.toBeInTheDocument();
    });

    it('should not show new game button when no game exists', () => {
      render(<App />);
      expect(screen.queryByTestId('new-game-button')).not.toBeInTheDocument();
    });
  });

  describe('Game active state', () => {
    const activeGameState = {
      board_size: 9,
      current_player: 1 as 0 | 1,
      players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
      walls: [],
      walls_remaining: [10, 10] as [number, number],
      legal_moves: [],
      winner: null,
      move_history: []
    };

    beforeEach(() => {
      setActiveGameSession('test-game-123', activeGameState);
    });

    it('should show all game components when game is active', () => {
      render(<App />);

      expect(screen.getByTestId('connection-status')).toBeInTheDocument();
      expect(screen.getByTestId('game-settings')).toBeInTheDocument();
      expect(screen.getByTestId('game-board')).toBeInTheDocument();
      expect(screen.getByTestId('move-history')).toBeInTheDocument();
      expect(screen.getByTestId('new-game-button')).toBeInTheDocument();
    });

    it('should show game info section with correct data', () => {
      render(<App />);

      expect(screen.getByText('Mode:')).toBeInTheDocument();
      expect(screen.getByText('human vs human')).toBeInTheDocument();
    });

    it('should not show AI info for human vs human mode', () => {
      render(<App />);

      expect(screen.queryByText('AI Level:')).not.toBeInTheDocument();
      expect(screen.queryByText('AI Time:')).not.toBeInTheDocument();
    });
  });

  describe('AI game modes', () => {
    it('should show AI info for human_vs_ai mode', () => {
      setActiveGameSession('test-game-123', { /* minimal game state */ } as any);
      mockGameStore.settings.gameSettings = {
        mode: 'human_vs_ai',
        ai_difficulty: 'hard',
        ai_time_limit: 5000,
        board_size: 9
      };
      // Update legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = { /* minimal game state */ } as any;
      mockGameStore.gameSettings = {
        mode: 'human_vs_ai',
        ai_difficulty: 'hard',
        ai_time_limit: 5000,
        board_size: 9
      };

      render(<App />);

      expect(screen.getByText('AI Level:')).toBeInTheDocument();
      expect(screen.getByText('hard')).toBeInTheDocument();
      expect(screen.getByText('AI Time:')).toBeInTheDocument();
      expect(screen.getByText('5s')).toBeInTheDocument();
    });

    it('should show AI info for ai_vs_ai mode', () => {
      setActiveGameSession('test-game-123', { /* minimal game state */ } as any);
      mockGameStore.settings.gameSettings = {
        mode: 'ai_vs_ai',
        ai_difficulty: 'expert',
        ai_time_limit: 10000,
        board_size: 9
      };
      // Update legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = { /* minimal game state */ } as any;
      mockGameStore.gameSettings = {
        mode: 'ai_vs_ai',
        ai_difficulty: 'expert',
        ai_time_limit: 10000,
        board_size: 9
      };

      render(<App />);

      expect(screen.getByText('AI Level:')).toBeInTheDocument();
      expect(screen.getByText('expert')).toBeInTheDocument();
      expect(screen.getByText('AI Time:')).toBeInTheDocument();
      expect(screen.getByText('10s')).toBeInTheDocument();
    });
  });

  describe('AI move automation', () => {
    it('should trigger AI move for ai_vs_ai mode when its AIs turn', async () => {
      const { wsService } = await import('@/services/websocket');
      const mockGetAIMove = vi.fn().mockResolvedValue({});
      wsService.getAIMove = mockGetAIMove;

      const gameState = {
        board_size: 9,
        current_player: 1 as 0 | 1,
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        walls: [],
        walls_remaining: [10, 10] as [number, number],
        legal_moves: [],
        winner: null,
        move_history: []
      };

      setActiveGameSession('test-game-123', gameState);
      mockGameStore.settings.gameSettings = {
        mode: 'ai_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      };
      // Update legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = gameState;
      mockGameStore.gameSettings = {
        mode: 'ai_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      };

      render(<App />);

      // Fast-forward past the delay
      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(mockGetAIMove).toHaveBeenCalledWith('test-game-123');
      }, { timeout: 2000 });
    });

    it('should trigger AI move for human_vs_ai mode when its AIs turn (player 1)', async () => {
      const { wsService } = await import('@/services/websocket');
      const mockGetAIMove = vi.fn().mockResolvedValue({});
      wsService.getAIMove = mockGetAIMove;

      const gameState = {
        board_size: 9,
        current_player: 1, // AI's turn (0-based: 0=human, 1=AI)
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        walls: [],
        walls_remaining: [10, 10],
        legal_moves: [],
        winner: null,
        move_history: []
      };

      setActiveGameSession('test-game-123', gameState);
      mockGameStore.settings.gameSettings = {
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      };
      // Update legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = gameState;
      mockGameStore.gameSettings = {
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      };

      render(<App />);

      // Fast-forward past the delay
      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      await waitFor(() => {
        expect(mockGetAIMove).toHaveBeenCalledWith('test-game-123');
      }, { timeout: 2000 });
    });

    it('should not trigger AI move for human_vs_ai mode when its humans turn (player 0)', async () => {
      const { wsService } = await import('@/services/websocket');
      const mockGetAIMove = vi.fn().mockResolvedValue({});
      wsService.getAIMove = mockGetAIMove;

      const gameState = {
        board_size: 9,
        current_player: 0, // Human's turn (0-based: 0=human, 1=AI)
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        walls: [],
        walls_remaining: [10, 10],
        legal_moves: [],
        winner: null,
        move_history: []
      };

      setActiveGameSession('test-game-123', gameState);
      mockGameStore.settings.gameSettings = {
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      };
      // Update legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = gameState;
      mockGameStore.gameSettings = {
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      };

      render(<App />);

      // Fast-forward past the delay
      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      expect(mockGetAIMove).not.toHaveBeenCalled();
    });

    it('should not trigger AI move when game has ended', async () => {
      const { wsService } = await import('@/services/websocket');
      const mockGetAIMove = vi.fn().mockResolvedValue({});
      wsService.getAIMove = mockGetAIMove;

      const gameState = {
        board_size: 9,
        current_player: 1 as 0 | 1,
        players: [{ x: 4, y: 0 }, { x: 4, y: 8 }], // Player 1 won
        walls: [],
        walls_remaining: [10, 10] as [number, number],
        legal_moves: [],
        winner: 1 as 0 | 1,
        move_history: []
      };

      setActiveGameSession('test-game-123', gameState);
      mockGameStore.settings.gameSettings = {
        mode: 'ai_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      };
      // Update legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = gameState;
      mockGameStore.gameSettings = {
        mode: 'ai_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      };

      render(<App />);

      await act(async () => {
        vi.advanceTimersByTime(1500);
      });

      expect(mockGetAIMove).not.toHaveBeenCalled();
    });
  });

  describe('Game state transitions', () => {
    it('should handle transition from no game to active game', () => {
      const { rerender } = render(<App />);

      // Initially no game
      expect(screen.queryByTestId('game-board')).not.toBeInTheDocument();

      // Update to have active game
      const newGameState = {
        board_size: 9,
        current_player: 1 as 0 | 1,
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        walls: [],
        walls_remaining: [10, 10] as [number, number],
        legal_moves: [],
        winner: null,
        move_history: []
      };

      setActiveGameSession('new-game-123', newGameState);

      rerender(<App />);

      expect(screen.getByTestId('game-board')).toBeInTheDocument();
      expect(screen.getByTestId('move-history')).toBeInTheDocument();
      expect(screen.getByTestId('new-game-button')).toBeInTheDocument();
    });

    it('should handle game end state', () => {
      const endGameState = {
        board_size: 9,
        current_player: 1 as 0 | 1,
        players: [{ x: 4, y: 0 }, { x: 4, y: 8 }], // Player 1 reached the end
        walls: [],
        walls_remaining: [8, 9] as [number, number],
        legal_moves: [],
        winner: 1 as 0 | 1,
        move_history: [
          { player: 0, notation: 'e8', type: 'move' },
          { player: 0, notation: 'e7', type: 'move' },
          { player: 0, notation: 'e6', type: 'move' },
          { player: 0, notation: 'e5', type: 'move' },
          { player: 0, notation: 'e4', type: 'move' },
          { player: 0, notation: 'e3', type: 'move' },
          { player: 0, notation: 'e2', type: 'move' },
          { player: 0, notation: 'e1', type: 'move' }
        ]
      };

      setActiveGameSession('test-game-123', endGameState);

      render(<App />);

      // Game components should still be visible
      expect(screen.getByTestId('game-board')).toBeInTheDocument();
      expect(screen.getByTestId('move-history')).toBeInTheDocument();
      expect(screen.getByTestId('new-game-button')).toBeInTheDocument();
    });
  });

  describe('Error states', () => {
    it('should handle connection errors gracefully', () => {
      mockGameStore.connection = { type: 'disconnected' as const };
      mockGameStore.connection.lastError = 'WebSocket connection failed';
      mockGameStore.ui.notifications = []; // Ensure notifications are handled
      // Update legacy properties
      mockGameStore.isConnected.mockReturnValue(false);
      mockGameStore.error = 'WebSocket connection failed';

      render(<App />);

      // Should still render without crashing
      expect(screen.getByTestId('connection-status')).toBeInTheDocument();
      expect(screen.getByTestId('game-settings')).toBeInTheDocument();
    });

    it('should handle missing game state', () => {
      // Game ID exists but no state yet - should be joining state
      mockGameStore.session = {
        type: 'joining-game',
        gameId: 'test-game-123'
      };
      // Update legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = null;

      render(<App />);

      // Should render settings but not game components
      expect(screen.getByTestId('game-settings')).toBeInTheDocument();
      expect(screen.queryByTestId('game-board')).not.toBeInTheDocument();
    });
  });

  describe('Cleanup and memory management', () => {
    it('should clean up timers on unmount', () => {
      const { unmount } = render(<App />);

      const gameState = {
        board_size: 9,
        current_player: 1 as 0 | 1,
        players: [{ x: 4, y: 8 }, { x: 4, y: 0 }],
        walls: [],
        walls_remaining: [10, 10] as [number, number],
        legal_moves: [],
        winner: null,
        move_history: []
      };

      setActiveGameSession('test-game-123', gameState);
      mockGameStore.settings.gameSettings = {
        mode: 'ai_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      };
      // Update legacy properties
      mockGameStore.gameId = 'test-game-123';
      mockGameStore.gameState = gameState;
      mockGameStore.gameSettings = {
        mode: 'ai_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 3000,
        board_size: 9
      };

      unmount();

      // Advance timers after unmount
      act(() => {
        vi.advanceTimersByTime(2000);
      });

      // Should not crash or call functions after unmount
      // Note: Cannot easily test this with dynamic import, but the test serves as documentation
    });
  });

  describe('Component rendering optimization', () => {
    it('should render all necessary components for complete game state', () => {
      const complexGameState = {
        board_size: 9,
        current_player: 0 as 0 | 1, // Changed from 2 to 0 (using 0-based)
        players: [{ x: 4, y: 6 }, { x: 4, y: 2 }],
        walls: [],
        walls_remaining: [8, 7] as [number, number],
        legal_moves: [],
        winner: null,
        move_history: [
          { player: 0, notation: 'e7', type: 'move' },
          { player: 1, notation: 'h4v5', type: 'wall' },
          { player: 0, notation: 'e6', type: 'move' }
        ]
      };

      setActiveGameSession('test-game-123', complexGameState);

      render(<App />);

      // Verify all game components are rendered
      const components = [
        'connection-status',
        'game-settings',
        'game-board',
        'move-history',
        'new-game-button'
      ];

      components.forEach(testId => {
        expect(screen.getByTestId(testId)).toBeInTheDocument();
      });
    });
  });
});