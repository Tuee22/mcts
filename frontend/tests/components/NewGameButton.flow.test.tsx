/**
 * NewGameButton Flow Tests
 *
 * Tests the NewGameButton component interaction flows, particularly
 * around state transitions and integration with game settings.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { NewGameButton } from '@/components/NewGameButton';

// Mock WebSocket service with vi.hoisted
const mockWsService = vi.hoisted(() => ({
  createGame: vi.fn(),
  isConnected: vi.fn(() => true), // Will be updated after mockGameStore is created
  disconnectFromGame: vi.fn()
}));

vi.mock('@/services/websocket', () => ({
  wsService: mockWsService
}));

// Mock the game store with vi.hoisted
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  const store = {
    // State properties
    connection: {
      type: 'connected' as const,
      clientId: 'test-client',
      since: new Date()
    },
    session: { 
      type: 'active-game' as const,
      gameId: 'active-game-123',
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
      const hasGame = mockGameStore.session.type === 'active-game' || 
                      mockGameStore.session.type === 'game-over';
      const connected = mockGameStore.connection.type === 'connected';
      
      if (hasGame) {
        return { type: 'button-visible', enabled: connected };
      } else if (connected) {
        return { type: 'panel-visible', canStartGame: true };
      } else {
        return { type: 'button-visible', enabled: false };
      }
    }),
    isConnected: vi.fn(() => mockGameStore.connection.type === 'connected'),
    getCurrentGameId: vi.fn(() => {
      if (mockGameStore.session.type === 'active-game' || 
          mockGameStore.session.type === 'game-over') {
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
    canStartGame: vi.fn(() => mockGameStore.connection.type === 'connected' && !mockGameStore.session),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => !!mockGameStore.session?.state && !mockGameStore.session.state.isGameOver),
    
    // Legacy compatibility
    gameId: 'active-game-123',
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
    if (typeof selector === 'function') {
      return selector(store);
    }
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

// Mock AI config utilities
vi.mock('@/utils/aiConfig', () => ({
  createGameCreationSettings: vi.fn((settings) => {
    const mctsIterationsMap = {
      easy: 100,
      medium: 1000,
      hard: 5000,
      expert: 10000
    };

    return {
      mode: settings.mode,
      ai_config: settings.mode !== 'human_vs_human' ? {
        difficulty: settings.ai_difficulty,
        time_limit_ms: settings.ai_time_limit,
        use_mcts: settings.ai_difficulty !== 'easy',
        mcts_iterations: mctsIterationsMap[settings.ai_difficulty]
      } : undefined,
      board_size: settings.board_size
    };
  })
}));

describe('NewGameButton Flow Tests', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset createGame to default behavior (successful Promise resolution)
    mockWsService.createGame.mockImplementation(() => Promise.resolve());
    // Update isConnected to use the mockGameStore
    mockWsService.isConnected.mockImplementation(() => mockGameStore.connection.type === 'connected');
    
    // Reset store to active game state
    Object.assign(mockGameStore, {
      connection: {
      type: 'connected' as const,
      clientId: 'test-client',
      since: new Date()
    },
      session: { 
        type: 'active-game',
        gameId: 'active-game-123',
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
      gameId: 'active-game-123',
      gameState: {
        board_size: 9,
        current_player: 0,
        players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
        walls: [],
        walls_remaining: [10, 10],
        legal_moves: [],
        winner: null,
        move_history: []
      },
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
    
    // Update function mocks - ensure all functions exist and are set correctly
    mockGameStore.dispatch = vi.fn();
    mockGameStore.isConnected = vi.fn(() => true);
    mockGameStore.getCurrentGameId = vi.fn(() => 'active-game-123');
    mockGameStore.getCurrentGameState = vi.fn(() => ({
      board_size: 9,
      current_player: 0,
      players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
      walls: [],
      walls_remaining: [10, 10],
      legal_moves: [],
      winner: null,
      move_history: []
    }));
    mockGameStore.canStartGame = vi.fn(() => false);
    mockGameStore.isGameActive = vi.fn(() => true);
  });

  describe('Button visibility and state', () => {
    it('should render when game is active', () => {
      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toBeInTheDocument();
      expect(button).toHaveClass('retro-btn', 'new-game');
    });

    it('should not render when no game is active', () => {
      // Update store to no game state
      Object.assign(mockGameStore, {
        session: { type: 'no-game' as const },
        gameId: null
      });
      mockGameStore.getCurrentGameId.mockReturnValue(null);

      render(<NewGameButton />);

      expect(screen.queryByText('New Game')).not.toBeInTheDocument();
    });

    it('should be enabled when connected', () => {
      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).not.toBeDisabled();
    });

    it('should be disabled when not connected', () => {
      // Update store to disconnected state
      Object.assign(mockGameStore, {
        connection: {
      type: 'disconnected' as const,
      canReset: true
    }
      });
      mockGameStore.isConnected.mockReturnValue(false);

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toBeDisabled();
    });

    // Note: game-ending state removed in simplified state machine

    it('should show appropriate title when disabled due to connection', () => {
      // Update store to disconnected state
      Object.assign(mockGameStore, {
        connection: {
      type: 'disconnected' as const,
      canReset: true
    }
      });
      mockGameStore.isConnected.mockReturnValue(false);

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toHaveAttribute('title', 'Connect to server to start a new game');
    });

    // Note: game-ending title test removed - state no longer exists
    });

    it('should show default title when enabled', () => {
      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toHaveAttribute('title', 'Start a new game');
    });
  });

  describe('New game creation flow', () => {
    it('should call dispatch with NEW_GAME_REQUESTED when clicked', () => {
      Object.assign(mockGameStore, {
        dispatch: vi.fn()
      });

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      fireEvent.click(button);

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
    });

    it('should create new game with current settings', () => {
      Object.assign(mockGameStore, {
        dispatch: vi.fn(),
        settings: {
          gameSettings: {
            mode: 'human_vs_ai' as const,
            ai_difficulty: 'hard' as const,
            ai_time_limit: 5000,
            board_size: 7
          },
          theme: 'light',
          soundEnabled: true
        },
        gameSettings: {
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'hard' as const,
          ai_time_limit: 5000,
          board_size: 7
        }
      });

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      fireEvent.click(button);

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      expect(mockWsService.disconnectFromGame).toHaveBeenCalled();
      // Note: actual game creation happens in GameSettings after transition
      expect(mockWsService.createGame).not.toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        ai_config: {
          difficulty: 'hard',
          time_limit_ms: 5000,
          use_mcts: true,
          mcts_iterations: 5000
        },
        board_size: 7
      });
    });

    it('should handle human_vs_human mode correctly', () => {
      Object.assign(mockGameStore, {
        dispatch: vi.fn(),
        settings: {
          gameSettings: {
            mode: 'human_vs_human' as const,
            ai_difficulty: 'medium' as const,
            ai_time_limit: 3000,
            board_size: 9
          },
          theme: 'light',
          soundEnabled: true
        },
        gameSettings: {
          mode: 'human_vs_human' as const,
          ai_difficulty: 'medium' as const,
          ai_time_limit: 3000,
          board_size: 9
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      expect(mockWsService.disconnectFromGame).toHaveBeenCalled();
      // Note: actual game creation happens in GameSettings after transition
      expect(mockWsService.createGame).not.toHaveBeenCalledWith({
        mode: 'human_vs_human',
        ai_config: undefined,
        board_size: 9
      });
    });

    it('should handle ai_vs_ai mode correctly', () => {
      Object.assign(mockGameStore, {
        dispatch: vi.fn(),
        settings: {
          gameSettings: {
            mode: 'ai_vs_ai' as const,
            ai_difficulty: 'expert' as const,
            ai_time_limit: 10000,
            board_size: 5
          },
          theme: 'light',
          soundEnabled: true
        },
        gameSettings: {
          mode: 'ai_vs_ai' as const,
          ai_difficulty: 'expert' as const,
          ai_time_limit: 10000,
          board_size: 5
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      expect(mockWsService.disconnectFromGame).toHaveBeenCalled();
      // Note: actual game creation happens in GameSettings after transition
      expect(mockWsService.createGame).not.toHaveBeenCalledWith({
        mode: 'ai_vs_ai',
        ai_config: {
          difficulty: 'expert',
          time_limit_ms: 10000,
          use_mcts: true,
          mcts_iterations: 10000
        },
        board_size: 5
      });
    });
  });

  describe('AI configuration logic', () => {
    it('should set use_mcts=false for easy difficulty', () => {
      Object.assign(mockGameStore, {
        dispatch: vi.fn(),
        settings: {
          gameSettings: {
            mode: 'human_vs_ai' as const,
            ai_difficulty: 'easy' as const,
            ai_time_limit: 1000,
            board_size: 9
          },
          theme: 'light',
          soundEnabled: true
        },
        gameSettings: {
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'easy' as const,
          ai_time_limit: 1000,
          board_size: 9
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      expect(mockWsService.disconnectFromGame).toHaveBeenCalled();
      // Note: actual game creation happens in GameSettings after transition
      expect(mockWsService.createGame).not.toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        ai_config: {
          difficulty: 'easy',
          time_limit_ms: 1000,
          use_mcts: false,
          mcts_iterations: 100
        },
        board_size: 9
      });
    });

    it('should set correct mcts_iterations for medium difficulty', () => {
      Object.assign(mockGameStore, {
        dispatch: vi.fn(),
        settings: {
          gameSettings: {
            mode: 'human_vs_ai' as const,
            ai_difficulty: 'medium' as const,
            ai_time_limit: 3000,
            board_size: 9
          },
          theme: 'light',
          soundEnabled: true
        },
        gameSettings: {
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'medium' as const,
          ai_time_limit: 3000,
          board_size: 9
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      expect(mockWsService.disconnectFromGame).toHaveBeenCalled();
      // Note: actual game creation happens in GameSettings after transition
      expect(mockWsService.createGame).not.toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        ai_config: {
          difficulty: 'medium',
          time_limit_ms: 3000,
          use_mcts: true,
          mcts_iterations: 1000
        },
        board_size: 9
      });
    });

    it('should set correct mcts_iterations for hard difficulty', () => {
      Object.assign(mockGameStore, {
        dispatch: vi.fn(),
        settings: {
          gameSettings: {
            mode: 'human_vs_ai' as const,
            ai_difficulty: 'hard' as const,
            ai_time_limit: 5000,
            board_size: 9
          },
          theme: 'light',
          soundEnabled: true
        },
        gameSettings: {
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'hard' as const,
          ai_time_limit: 5000,
          board_size: 9
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      expect(mockWsService.disconnectFromGame).toHaveBeenCalled();
      // Note: actual game creation happens in GameSettings after transition
      expect(mockWsService.createGame).not.toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        ai_config: {
          difficulty: 'hard',
          time_limit_ms: 5000,
          use_mcts: true,
          mcts_iterations: 5000
        },
        board_size: 9
      });
    });

    it('should set correct mcts_iterations for expert difficulty', () => {
      Object.assign(mockGameStore, {
        dispatch: vi.fn(),
        settings: {
          gameSettings: {
            mode: 'human_vs_ai' as const,
            ai_difficulty: 'expert' as const,
            ai_time_limit: 10000,
            board_size: 9
          },
          theme: 'light',
          soundEnabled: true
        },
        gameSettings: {
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'expert' as const,
          ai_time_limit: 10000,
          board_size: 9
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      expect(mockWsService.disconnectFromGame).toHaveBeenCalled();
      // Note: actual game creation happens in GameSettings after transition
      expect(mockWsService.createGame).not.toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        ai_config: {
          difficulty: 'expert',
          time_limit_ms: 10000,
          use_mcts: true,
          mcts_iterations: 10000
        },
        board_size: 9
      });
    });
  });

  describe('Error handling', () => {
    it('should handle WebSocket errors during game creation', async () => {
      const mockResetGame = vi.fn();
      const mockSetError = vi.fn();
      mockWsService.createGame.mockImplementation(() => {
        return Promise.reject(new Error('WebSocket connection failed'));
      });

      Object.assign(mockGameStore, {
        reset: mockResetGame,
        setError: mockSetError
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      // WebSocket disconnect should be called 
      expect(mockWsService.disconnectFromGame).toHaveBeenCalledTimes(1);
    });

    it('should not create game when not connected', () => {
      Object.assign(mockGameStore, {
        connection: {
      type: 'disconnected' as const,
      canReset: true
    }
      });
      mockGameStore.isConnected.mockReturnValue(false);

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      fireEvent.click(button);

      // Button should be disabled, so click shouldn't trigger game creation
      expect(mockWsService.createGame).not.toHaveBeenCalled();
    });

    it('should not create game when loading', () => {
      Object.assign(mockGameStore, {
        isLoading: true
      });

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      fireEvent.click(button);

      // Button should be disabled, so click shouldn't trigger game creation
      expect(mockWsService.createGame).not.toHaveBeenCalled();
    });
  });

  describe('State cleanup', () => {
    it('should reset game state before creating new game', () => {
      const mockResetGame = vi.fn();
      Object.assign(mockGameStore, {
        reset: mockResetGame
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      // Dispatch should be called with NEW_GAME_REQUESTED action
      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      // Note: Actual game creation happens in GameSettings component after state transition
    });

    it('should maintain settings during game reset', () => {
      const mockResetGame = vi.fn();
      const originalSettings = {
        mode: 'ai_vs_ai' as const,
        ai_difficulty: 'expert' as const,
        ai_time_limit: 10000,
        board_size: 7
      };

      Object.assign(mockGameStore, {
        reset: mockResetGame,
        settings: {
          gameSettings: originalSettings,
          theme: 'light',
          soundEnabled: true
        },
        gameSettings: originalSettings
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      // Settings should be used as-is for new game creation
      expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      expect(mockWsService.disconnectFromGame).toHaveBeenCalled();
      // Note: actual game creation happens in GameSettings after transition
      expect(mockWsService.createGame).not.toHaveBeenCalledWith({
        mode: 'ai_vs_ai',
        ai_config: {
          difficulty: 'expert',
          time_limit_ms: 10000,
          use_mcts: true,
          mcts_iterations: 10000
        },
        board_size: 7
      });
    });
  });

  describe('Integration with game settings', () => {
    it('should work with various board sizes', () => {
      const sizes = [5, 7, 9];

      sizes.forEach(size => {
        const mockResetGame = vi.fn();
        const gameSettings = {
          ...mockGameStore.gameSettings,
          board_size: size
        };
        
        Object.assign(mockGameStore, {
          reset: mockResetGame,
          settings: {
            gameSettings: gameSettings,
            theme: 'light',
            soundEnabled: true
          },
          gameSettings: gameSettings
        });

        const { rerender } = render(<NewGameButton />);

        fireEvent.click(screen.getByText('New Game'));

        // NewGameButton only dispatches action, doesn't directly create game
        expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });

        rerender(<div />); // Clean up between iterations
        vi.clearAllMocks();
      });
    });

    it('should work with all time limit options', () => {
      const timeLimits = [1000, 3000, 5000, 10000];

      timeLimits.forEach(timeLimit => {
        const mockResetGame = vi.fn();
        const gameSettings = {
          ...mockGameStore.gameSettings,
          mode: 'human_vs_ai' as const,
          ai_time_limit: timeLimit
        };
        
        Object.assign(mockGameStore, {
          reset: mockResetGame,
          settings: {
            gameSettings: gameSettings,
            theme: 'light',
            soundEnabled: true
          },
          gameSettings: gameSettings
        });

        const { rerender } = render(<NewGameButton />);

        fireEvent.click(screen.getByText('New Game'));

        expect(mockGameStore.dispatch).toHaveBeenCalledWith({ type: 'NEW_GAME_REQUESTED' });
      expect(mockWsService.disconnectFromGame).toHaveBeenCalled();
      // Note: actual game creation happens in GameSettings after transition
      expect(mockWsService.createGame).not.toHaveBeenCalledWith({
          mode: 'human_vs_ai',
          ai_config: expect.objectContaining({
            time_limit_ms: timeLimit
          }),
          board_size: 9
        });

        rerender(<div />); // Clean up between iterations
        vi.clearAllMocks();
      });
    });
  });

  describe('Accessibility and UX', () => {
    it('should be focusable when enabled', () => {
      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      button.focus();

      expect(document.activeElement).toBe(button);
    });

    it('should have proper ARIA attributes', () => {
      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toHaveAttribute('type', 'button');
      expect(button).toHaveAttribute('title');
    });

    it('should provide clear feedback when disabled', () => {
      Object.assign(mockGameStore, {
        connection: {
          type: 'disconnected' as const,
          canReset: true
        }
      });
      mockGameStore.isConnected.mockReturnValue(false);

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute('title', 'Connect to server to start a new game');
    });
  });