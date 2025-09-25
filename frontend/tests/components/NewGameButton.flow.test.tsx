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
  isConnected: vi.fn(() => true),
  disconnectFromGame: vi.fn()
}));

vi.mock('@/services/websocket', () => ({
  wsService: mockWsService
}));

// Mock the game store
const mockUseGameStore = vi.fn();
vi.mock('@/store/gameStore', () => ({
  useGameStore: () => mockUseGameStore()
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
  const defaultMockStore = {
    gameId: 'active-game-123',
    isConnected: true,
    isLoading: false,
    gameSettings: {
      mode: 'human_vs_human' as const,
      ai_difficulty: 'medium' as const,
      ai_time_limit: 3000,
      board_size: 9
    },
    reset: vi.fn(),
    setGameSettings: vi.fn(),
    setError: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset createGame to default behavior (successful Promise resolution)
    mockWsService.createGame.mockImplementation(() => Promise.resolve());
    mockUseGameStore.mockReturnValue(defaultMockStore);
  });

  describe('Button visibility and state', () => {
    it('should render when game is active', () => {
      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toBeInTheDocument();
      expect(button).toHaveClass('retro-btn', 'new-game');
    });

    it('should not render when no game is active', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: null
      });

      render(<NewGameButton />);

      expect(screen.queryByText('New Game')).not.toBeInTheDocument();
    });

    it('should be enabled when connected', () => {
      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).not.toBeDisabled();
    });

    it('should be disabled when not connected', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        isConnected: false
      });

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toBeDisabled();
    });

    it('should be disabled during loading', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        isLoading: true
      });

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toBeDisabled();
    });

    it('should show appropriate title when disabled due to connection', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        isConnected: false
      });

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toHaveAttribute('title', 'Connect to server to start a new game');
    });

    it('should show appropriate title when disabled due to loading', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        isLoading: true
      });

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toHaveAttribute('title', 'Please wait, starting new game...');
    });

    it('should show default title when enabled', () => {
      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toHaveAttribute('title', 'Start a new game');
    });
  });

  describe('New game creation flow', () => {
    it('should call resetGame when clicked', () => {
      const mockResetGame = vi.fn();
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame
      });

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      fireEvent.click(button);

      expect(mockResetGame).toHaveBeenCalledTimes(1);
    });

    it('should create new game with current settings', () => {
      const mockResetGame = vi.fn();
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame,
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

      expect(mockWsService.createGame).toHaveBeenCalledWith({
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
      const mockResetGame = vi.fn();
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame,
        gameSettings: {
          mode: 'human_vs_human' as const,
          ai_difficulty: 'medium' as const,
          ai_time_limit: 3000,
          board_size: 9
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_human',
        ai_config: undefined,
        board_size: 9
      });
    });

    it('should handle ai_vs_ai mode correctly', () => {
      const mockResetGame = vi.fn();
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame,
        gameSettings: {
          mode: 'ai_vs_ai' as const,
          ai_difficulty: 'expert' as const,
          ai_time_limit: 10000,
          board_size: 5
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockWsService.createGame).toHaveBeenCalledWith({
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
      const mockResetGame = vi.fn();
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame,
        gameSettings: {
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'easy' as const,
          ai_time_limit: 1000,
          board_size: 9
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockWsService.createGame).toHaveBeenCalledWith({
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
      const mockResetGame = vi.fn();
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame,
        gameSettings: {
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'medium' as const,
          ai_time_limit: 3000,
          board_size: 9
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockWsService.createGame).toHaveBeenCalledWith({
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
      const mockResetGame = vi.fn();
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame,
        gameSettings: {
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'hard' as const,
          ai_time_limit: 5000,
          board_size: 9
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockWsService.createGame).toHaveBeenCalledWith({
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
      const mockResetGame = vi.fn();
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame,
        gameSettings: {
          mode: 'human_vs_ai' as const,
          ai_difficulty: 'expert' as const,
          ai_time_limit: 10000,
          board_size: 9
        }
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockWsService.createGame).toHaveBeenCalledWith({
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

      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame,
        setError: mockSetError
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      expect(mockResetGame).toHaveBeenCalledTimes(1);
      // WebSocket service should still be called even if it throws
      expect(mockWsService.createGame).toHaveBeenCalledTimes(1);
    });

    it('should not create game when not connected', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        isConnected: false
      });

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      fireEvent.click(button);

      // Button should be disabled, so click shouldn't trigger game creation
      expect(mockWsService.createGame).not.toHaveBeenCalled();
    });

    it('should not create game when loading', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
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
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      // Reset should be called first
      expect(mockResetGame).toHaveBeenCalledTimes(1);
      // Then game creation should be triggered
      expect(mockWsService.createGame).toHaveBeenCalledTimes(1);
    });

    it('should maintain settings during game reset', () => {
      const mockResetGame = vi.fn();
      const originalSettings = {
        mode: 'ai_vs_ai' as const,
        ai_difficulty: 'expert' as const,
        ai_time_limit: 10000,
        board_size: 7
      };

      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        reset: mockResetGame,
        gameSettings: originalSettings
      });

      render(<NewGameButton />);

      fireEvent.click(screen.getByText('New Game'));

      // Settings should be used as-is for new game creation
      expect(mockWsService.createGame).toHaveBeenCalledWith({
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
        mockUseGameStore.mockReturnValue({
          ...defaultMockStore,
          reset: mockResetGame,
          gameSettings: {
            ...defaultMockStore.gameSettings,
            board_size: size
          }
        });

        const { rerender } = render(<NewGameButton />);

        fireEvent.click(screen.getByText('New Game'));

        expect(mockWsService.createGame).toHaveBeenCalledWith(
          expect.objectContaining({ board_size: size })
        );

        rerender(<div />); // Clean up between iterations
        vi.clearAllMocks();
      });
    });

    it('should work with all time limit options', () => {
      const timeLimits = [1000, 3000, 5000, 10000];

      timeLimits.forEach(timeLimit => {
        const mockResetGame = vi.fn();
        mockUseGameStore.mockReturnValue({
          ...defaultMockStore,
          reset: mockResetGame,
          gameSettings: {
            ...defaultMockStore.gameSettings,
            mode: 'human_vs_ai' as const,
            ai_time_limit: timeLimit
          }
        });

        const { rerender } = render(<NewGameButton />);

        fireEvent.click(screen.getByText('New Game'));

        expect(mockWsService.createGame).toHaveBeenCalledWith({
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
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        isConnected: false
      });

      render(<NewGameButton />);

      const button = screen.getByText('New Game');
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute('title', 'Connect to server to start a new game');
    });
  });
});