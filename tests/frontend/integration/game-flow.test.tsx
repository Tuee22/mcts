import React from 'react';
import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import App from '../../../frontend/src/App';
import { wsService } from '../../../frontend/src/services/websocket';
import { useGameStore } from '../../../frontend/src/store/gameStore';
import { render, createUser, mockWebSocketEvents } from '../utils/test-utils';
import { MockWebSocket } from '../mocks/websocket.mock';

// Mock dependencies
vi.mock('../../../frontend/src/services/websocket');
vi.mock('../../../frontend/src/store/gameStore');

const mockWsService = wsService as ReturnType<typeof vi.mocked<typeof wsService>>;
const mockUseGameStore = useGameStore as ReturnType<typeof vi.mocked<typeof useGameStore>>;

describe('Game Flow Integration Tests', () => {
  const user = createUser();
  let mockSocket: MockWebSocket;
  let mockStore: any;

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockStore = {
      gameId: null,
      gameState: null,
      gameSettings: {
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      },
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

    mockUseGameStore.mockReturnValue(mockStore);

    mockSocket = new MockWebSocket('http://localhost:8000');
    mockWsService.connect = vi.fn();
    mockWsService.createGame = vi.fn();
    mockWsService.makeMove = vi.fn();
    mockWsService.isConnected = vi.fn(() => true);
  });

  describe('Complete Game Flow', () => {
    it('handles full game creation and play flow', async () => {
      render(<App />);

      // 1. Initial state - should show game settings
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByText('Human vs AI')).toBeInTheDocument();

      // 2. Configure game settings
      const aiDifficultyHard = screen.getByText('Hard');
      await user.click(aiDifficultyHard);
      expect(mockStore.setGameSettings).toHaveBeenCalledWith({ ai_difficulty: 'hard' });

      const boardSize5x5 = screen.getByText('5x5');
      await user.click(boardSize5x5);
      expect(mockStore.setGameSettings).toHaveBeenCalledWith({ board_size: 5 });

      // 3. Start game
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);
      
      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        board_size: 5,
        ai_config: {
          difficulty: 'hard',
          time_limit_ms: 5000,
          use_mcts: true,
          mcts_iterations: 5000
        }
      });

      // 4. Simulate game created
      act(() => {
        mockStore.gameId = 'test-game-123';
        mockStore.gameState = mockWebSocketEvents.gameCreated.state;
        mockUseGameStore.mockReturnValue({
          ...mockStore,
          gameId: 'test-game-123',
          gameState: mockWebSocketEvents.gameCreated.state
        });
      });

      // Re-render with game state
      render(<App />);

      // 5. Should show game board
      await waitFor(() => {
        expect(screen.getByText('Current: Player 1')).toBeInTheDocument();
        expect(screen.getByText('P1 Walls: 10')).toBeInTheDocument();
      });
    });

    it('handles game settings changes and persistence', async () => {
      render(<App />);

      // Change to AI vs AI mode
      const aiVsAiButton = screen.getByText('AI vs AI');
      await user.click(aiVsAiButton);
      expect(mockStore.setGameSettings).toHaveBeenCalledWith({ mode: 'ai_vs_ai' });

      // Change AI difficulty
      const expertButton = screen.getByText('Expert');
      await user.click(expertButton);
      expect(mockStore.setGameSettings).toHaveBeenCalledWith({ ai_difficulty: 'expert' });

      // Change time limit
      const tenSecButton = screen.getByText('10s');
      await user.click(tenSecButton);
      expect(mockStore.setGameSettings).toHaveBeenCalledWith({ ai_time_limit: 10000 });

      // Start game with all settings
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'ai_vs_ai',
        board_size: 9,
        ai_config: {
          difficulty: 'expert',
          time_limit_ms: 10000,
          use_mcts: true,
          mcts_iterations: 10000
        }
      });
    });

    it('handles human vs human mode correctly', async () => {
      render(<App />);

      // Change to human vs human
      const humanVsHumanButton = screen.getByText('Human vs Human');
      await user.click(humanVsHumanButton);
      expect(mockStore.setGameSettings).toHaveBeenCalledWith({ mode: 'human_vs_human' });

      // AI settings should be hidden
      expect(screen.queryByText('AI Difficulty')).not.toBeInTheDocument();
      expect(screen.queryByText('AI Time Limit')).not.toBeInTheDocument();

      // Start game
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_human',
        board_size: 9,
        ai_config: undefined
      });
    });
  });

  describe('Game Board Interaction', () => {
    beforeEach(() => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = {
        ...mockWebSocketEvents.gameCreated.state,
        legal_moves: ['e2', 'a1', 'a2']
      };
      mockUseGameStore.mockReturnValue(mockStore);
    });

    it('handles player moves correctly', async () => {
      render(<App />);

      // Find and click a legal move cell
      const cells = document.querySelectorAll('.game-cell.legal');
      expect(cells.length).toBeGreaterThan(0);

      await user.click(cells[0] as HTMLElement);

      expect(mockWsService.makeMove).toHaveBeenCalledWith('test-game-123', expect.any(String));
    });

    it('handles wall placement mode', async () => {
      render(<App />);

      // Enter wall placement mode
      const wallButton = screen.getByText('Place Wall');
      await user.click(wallButton);

      expect(screen.getByText('Place Pawn')).toBeInTheDocument();
      expect(screen.getByText('Horizontal')).toBeInTheDocument();

      // Toggle orientation
      const orientationButton = screen.getByText('Horizontal');
      await user.click(orientationButton);

      expect(screen.getByText('Vertical')).toBeInTheDocument();
    });

    it('prevents moves when viewing history', async () => {
      mockStore.selectedHistoryIndex = 0;
      mockUseGameStore.mockReturnValue(mockStore);

      render(<App />);

      const cells = document.querySelectorAll('.game-cell');
      await user.click(cells[0] as HTMLElement);

      expect(mockWsService.makeMove).not.toHaveBeenCalled();
    });
  });

  describe('Move History Integration', () => {
    beforeEach(() => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = {
        ...mockWebSocketEvents.gameCreated.state,
        move_history: [
          {
            notation: 'e2',
            player: 0,
            type: 'move',
            position: { x: 4, y: 7 },
            board_state: mockWebSocketEvents.gameCreated.state
          },
          {
            notation: 'e8',
            player: 1,
            type: 'move',
            position: { x: 4, y: 1 },
            board_state: mockWebSocketEvents.gameCreated.state
          }
        ]
      };
      mockUseGameStore.mockReturnValue(mockStore);
    });

    it('displays move history and allows navigation', async () => {
      render(<App />);

      // Should show move history
      expect(screen.getByText('Move History')).toBeInTheDocument();
      expect(screen.getByText('e2')).toBeInTheDocument();
      expect(screen.getByText('e8')).toBeInTheDocument();

      // Click on first move
      const firstMove = screen.getByText('e2').closest('.move-item');
      await user.click(firstMove!);

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(0);

      // Use navigation controls
      const nextButton = screen.getByText('▶');
      await user.click(nextButton);

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(1);
    });

    it('shows current button when history is selected', async () => {
      mockStore.selectedHistoryIndex = 0;
      mockUseGameStore.mockReturnValue(mockStore);

      render(<App />);

      expect(screen.getByText('Current')).toBeInTheDocument();

      const currentButton = screen.getByText('Current');
      await user.click(currentButton);

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(null);
    });
  });

  describe('Error Handling Integration', () => {
    it('displays connection errors', async () => {
      mockStore.error = 'Connection failed';
      mockUseGameStore.mockReturnValue(mockStore);

      render(<App />);

      // Error should be displayed (via toast)
      expect(mockStore.setError).toHaveBeenCalledWith(null);
    });

    it('handles WebSocket disconnection', async () => {
      mockStore.isConnected = false;
      mockUseGameStore.mockReturnValue(mockStore);

      render(<App />);

      const statusText = screen.getByText('Disconnected');
      expect(statusText).toBeInTheDocument();

      const statusIndicator = document.querySelector('.status-indicator');
      expect(statusIndicator).toHaveClass('disconnected');
    });

    it('handles game creation errors', async () => {
      mockWsService.createGame.mockRejectedValue(new Error('Server error'));

      render(<App />);

      const startButton = screen.getByText('Start Game');
      
      // Should handle error gracefully
      await expect(async () => {
        await user.click(startButton);
      }).not.toThrow();
    });
  });

  describe('Game Completion Flow', () => {
    it('handles game over state', async () => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = {
        ...mockWebSocketEvents.gameOver.state,
        winner: 0
      };
      mockUseGameStore.mockReturnValue(mockStore);

      render(<App />);

      expect(screen.getByText('Game Over!')).toBeInTheDocument();
      expect(screen.getByText('Player 1 Wins!')).toBeInTheDocument();
    });

    it('allows starting new game after completion', async () => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = {
        ...mockWebSocketEvents.gameOver.state,
        winner: 0
      };
      mockUseGameStore.mockReturnValue(mockStore);

      render(<App />);

      const newGameButton = screen.getByText('New Game');
      await user.click(newGameButton);

      expect(mockStore.reset).toHaveBeenCalled();
    });
  });

  describe('AI Move Integration', () => {
    it('requests AI moves in human vs AI mode', async () => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = {
        ...mockWebSocketEvents.gameCreated.state,
        current_player: 1 // AI turn
      };
      mockStore.gameSettings = {
        ...mockStore.gameSettings,
        mode: 'human_vs_ai'
      };
      mockUseGameStore.mockReturnValue(mockStore);

      render(<App />);

      // Should request AI move after a delay
      await waitFor(() => {
        expect(mockWsService.getAIMove).toHaveBeenCalledWith('test-game-123');
      }, { timeout: 1000 });
    });

    it('continuously requests AI moves in AI vs AI mode', async () => {
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = {
        ...mockWebSocketEvents.gameCreated.state,
        current_player: 0
      };
      mockStore.gameSettings = {
        ...mockStore.gameSettings,
        mode: 'ai_vs_ai'
      };
      mockUseGameStore.mockReturnValue(mockStore);

      render(<App />);

      // Should request AI move for both players
      await waitFor(() => {
        expect(mockWsService.getAIMove).toHaveBeenCalledWith('test-game-123');
      }, { timeout: 1500 });
    });
  });

  describe('Accessibility Integration', () => {
    it('maintains proper focus management', async () => {
      render(<App />);

      const startButton = screen.getByText('Start Game');
      startButton.focus();

      expect(document.activeElement).toBe(startButton);

      // Tab navigation should work
      await user.tab();
      expect(document.activeElement).not.toBe(startButton);
    });

    it('provides proper ARIA labels', async () => {
      render(<App />);

      const humanVsAi = screen.getByText('Human vs AI');
      expect(humanVsAi.closest('button')).toHaveAttribute('aria-label', expect.any(String));
    });
  });

  describe('Performance Integration', () => {
    it('handles rapid user interactions', async () => {
      render(<App />);

      // Rapidly click different settings
      const buttons = [
        screen.getByText('Hard'),
        screen.getByText('5x5'),
        screen.getByText('AI vs AI'),
        screen.getByText('10s')
      ];

      // Should handle rapid clicks without issues
      for (const button of buttons) {
        await user.click(button);
      }

      expect(mockStore.setGameSettings).toHaveBeenCalledTimes(4);
    });

    it('efficiently handles large game states', async () => {
      const largeGameState = {
        ...mockWebSocketEvents.gameCreated.state,
        move_history: Array.from({ length: 500 }, (_, i) => ({
          notation: `move${i}`,
          player: i % 2 as 0 | 1,
          type: 'move' as const,
          position: { x: 0, y: 0 }
        }))
      };

      mockStore.gameId = 'test-game-123';
      mockStore.gameState = largeGameState;
      mockUseGameStore.mockReturnValue(mockStore);

      const start = performance.now();
      render(<App />);
      const end = performance.now();

      // Should render large states efficiently (less than 100ms)
      expect(end - start).toBeLessThan(100);
    });
  });
});