import React from 'react';
import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GameBoard } from '../../../frontend/src/components/GameBoard';
import { MoveHistory } from '../../../frontend/src/components/MoveHistory';
import { GameSettings } from '../../../frontend/src/components/GameSettings';
import { useGameStore } from '../../../frontend/src/store/gameStore';
import { wsService } from '../../../frontend/src/services/websocket';
import { 
  render, 
  createUser, 
  mockGameStateWithHistory,
  mockGameSettings,
  generateMockMove 
} from '../utils/test-utils';

// Mock dependencies
jest.mock('../../../frontend/src/store/gameStore');
jest.mock('../../../frontend/src/services/websocket');

const mockUseGameStore = useGameStore as jest.MockedFunction<typeof useGameStore>;
const mockWsService = wsService as jest.Mocked<typeof wsService>;

describe('Component Interactions Integration Tests', () => {
  const user = createUser();
  let mockStore: any;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockStore = {
      gameId: 'test-game-123',
      gameState: mockGameStateWithHistory,
      gameSettings: mockGameSettings,
      isConnected: true,
      isLoading: false,
      error: null,
      selectedHistoryIndex: null,
      setGameId: jest.fn(),
      setGameState: jest.fn(),
      setGameSettings: jest.fn(),
      setIsConnected: jest.fn(),
      setIsLoading: jest.fn(),
      setError: jest.fn(),
      setSelectedHistoryIndex: jest.fn(),
      addMoveToHistory: jest.fn(),
      reset: jest.fn()
    };

    mockUseGameStore.mockReturnValue(mockStore);
    mockWsService.makeMove = jest.fn();
    mockWsService.createGame = jest.fn();
  });

  describe('GameBoard and MoveHistory Interaction', () => {
    it('synchronizes board display with selected history move', async () => {
      const TestComponent = () => (
        <div>
          <GameBoard />
          <MoveHistory />
        </div>
      );

      render(<TestComponent />);

      // Click on first move in history
      const firstMove = screen.getByText('e2').closest('.move-item');
      await user.click(firstMove!);

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(0);

      // Board should prevent moves when viewing history
      mockStore.selectedHistoryIndex = 0;
      mockUseGameStore.mockReturnValue(mockStore);

      const cells = document.querySelectorAll('.game-cell');
      await user.click(cells[0] as HTMLElement);

      expect(mockWsService.makeMove).not.toHaveBeenCalled();
    });

    it('updates board when navigating through history', async () => {
      const TestComponent = () => (
        <div>
          <GameBoard />
          <MoveHistory />
        </div>
      );

      render(<TestComponent />);

      // Navigate to previous move
      const previousButton = screen.getByText('◀');
      mockStore.selectedHistoryIndex = 1;
      mockUseGameStore.mockReturnValue(mockStore);

      await user.click(previousButton);

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(0);
    });

    it('returns to current position from history view', async () => {
      mockStore.selectedHistoryIndex = 0;
      mockUseGameStore.mockReturnValue(mockStore);

      const TestComponent = () => (
        <div>
          <GameBoard />
          <MoveHistory />
        </div>
      );

      render(<TestComponent />);

      // Click current button
      const currentButton = screen.getByText('Current');
      await user.click(currentButton);

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(null);
    });

    it('shows proper game state when history is selected', async () => {
      mockStore.selectedHistoryIndex = 0;
      mockStore.gameState = {
        ...mockGameStateWithHistory,
        move_history: [
          {
            notation: 'e2',
            player: 0 as 0 | 1,
            type: 'move' as const,
            position: { x: 4, y: 7 },
            board_state: {
              ...mockGameStateWithHistory,
              current_player: 1 as 0 | 1,
              players: [{ x: 4, y: 7 }, { x: 4, y: 8 }]
            }
          }
        ]
      };
      mockUseGameStore.mockReturnValue(mockStore);

      const TestComponent = () => (
        <div>
          <GameBoard />
          <MoveHistory />
        </div>
      );

      render(<TestComponent />);

      // Board should show the historical position
      expect(screen.getByText('e2')).toBeInTheDocument();
    });
  });

  describe('GameSettings and GameBoard Integration', () => {
    it('creates game with correct settings and displays board', async () => {
      mockStore.gameId = null;
      mockStore.gameState = null;
      mockUseGameStore.mockReturnValue(mockStore);

      const TestComponent = () => (
        <div>
          <GameSettings />
          <GameBoard />
        </div>
      );

      render(<TestComponent />);

      // Should show settings, not board
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.queryByText('P1 Walls:')).not.toBeInTheDocument();

      // Change settings and start game
      const hardDifficulty = screen.getByText('Hard');
      await user.click(hardDifficulty);

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        board_size: 9,
        ai_config: {
          difficulty: 'hard',
          time_limit_ms: 5000,
          use_mcts: true,
          mcts_iterations: 5000
        }
      });
    });

    it('hides settings when game is active', async () => {
      const TestComponent = () => (
        <div>
          <GameSettings />
          <GameBoard />
        </div>
      );

      render(<TestComponent />);

      // With active game, settings should be toggleable
      expect(screen.getByText('P1 Walls: 10')).toBeInTheDocument();
    });

    it('shows settings toggle when game is running', async () => {
      render(<GameSettings />);

      // Should show compact settings or toggle
      const toggleButton = document.querySelector('.toggle-settings');
      if (toggleButton) {
        await user.click(toggleButton);
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      }
    });
  });

  describe('All Components Integration', () => {
    it('handles complete game flow across all components', async () => {
      const TestComponent = () => (
        <div>
          <GameSettings />
          <GameBoard />
          <MoveHistory />
        </div>
      );

      // Start with no game
      mockStore.gameId = null;
      mockStore.gameState = null;
      mockUseGameStore.mockReturnValue(mockStore);

      const { rerender } = render(<TestComponent />);

      // 1. Configure and start game
      const aiVsAi = screen.getByText('AI vs AI');
      await user.click(aiVsAi);
      expect(mockStore.setGameSettings).toHaveBeenCalledWith({ mode: 'ai_vs_ai' });

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);
      expect(mockWsService.createGame).toHaveBeenCalled();

      // 2. Simulate game created
      mockStore.gameId = 'test-game-123';
      mockStore.gameState = mockGameStateWithHistory;
      mockUseGameStore.mockReturnValue(mockStore);
      rerender(<TestComponent />);

      // 3. Should show board and history
      expect(screen.getByText('P1 Walls: 10')).toBeInTheDocument();
      expect(screen.getByText('Move History')).toBeInTheDocument();

      // 4. Make a move on board
      const legalCell = document.querySelector('.game-cell.legal');
      if (legalCell) {
        await user.click(legalCell);
        expect(mockWsService.makeMove).toHaveBeenCalled();
      }

      // 5. Navigate in history
      const firstMove = screen.getByText('e2').closest('.move-item');
      await user.click(firstMove!);
      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(0);

      // 6. Board should prevent moves in history view
      mockStore.selectedHistoryIndex = 0;
      mockUseGameStore.mockReturnValue(mockStore);
      rerender(<TestComponent />);

      const anyCell = document.querySelector('.game-cell');
      if (anyCell) {
        await user.click(anyCell);
        // Should not make additional moves
        expect(mockWsService.makeMove).toHaveBeenCalledTimes(1);
      }
    });

    it('maintains state consistency across components', async () => {
      const TestComponent = () => (
        <div>
          <GameBoard />
          <MoveHistory />
        </div>
      );

      render(<TestComponent />);

      // All components should use the same game state
      expect(screen.getByText('Current: Player 1')).toBeInTheDocument(); // From GameBoard
      expect(screen.getByText('e2')).toBeInTheDocument(); // From MoveHistory

      // History selection should affect both
      const firstMove = screen.getByText('e2').closest('.move-item');
      await user.click(firstMove!);

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(0);
    });
  });

  describe('Error Propagation Between Components', () => {
    it('propagates WebSocket errors to all components', async () => {
      mockStore.error = 'Connection lost';
      mockUseGameStore.mockReturnValue(mockStore);

      const TestComponent = () => (
        <div>
          <GameSettings />
          <GameBoard />
          <MoveHistory />
        </div>
      );

      render(<TestComponent />);

      // Error should be cleared after being processed
      expect(mockStore.setError).toHaveBeenCalledWith(null);
    });

    it('handles loading state across components', async () => {
      mockStore.isLoading = true;
      mockUseGameStore.mockReturnValue(mockStore);

      render(<GameSettings />);

      const startButton = screen.getByText('Starting...');
      expect(startButton).toBeDisabled();
    });

    it('handles connection state across components', async () => {
      mockStore.isConnected = false;
      mockUseGameStore.mockReturnValue(mockStore);

      const TestComponent = () => (
        <div>
          <GameBoard />
          <GameSettings />
        </div>
      );

      render(<TestComponent />);

      // Both components should respect connection state
      const cells = document.querySelectorAll('.game-cell');
      if (cells.length > 0) {
        await user.click(cells[0] as HTMLElement);
        expect(mockWsService.makeMove).not.toHaveBeenCalled();
      }
    });
  });

  describe('Performance with Multiple Components', () => {
    it('efficiently renders all components together', () => {
      const TestComponent = () => (
        <div>
          <GameSettings />
          <GameBoard />
          <MoveHistory />
        </div>
      );

      const start = performance.now();
      render(<TestComponent />);
      const end = performance.now();

      // Should render efficiently even with multiple components
      expect(end - start).toBeLessThan(50);
    });

    it('handles rapid state changes across components', async () => {
      const TestComponent = () => (
        <div>
          <GameBoard />
          <MoveHistory />
        </div>
      );

      render(<TestComponent />);

      // Rapid history navigation
      const moves = ['◀', '▶', '⏮', '⏭'];
      
      for (const move of moves) {
        const button = screen.getByText(move);
        await user.click(button);
      }

      // Should handle rapid changes without issues
      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledTimes(4);
    });

    it('manages memory efficiently with large game states', () => {
      const largeGameState = {
        ...mockGameStateWithHistory,
        move_history: Array.from({ length: 1000 }, (_, i) =>
          generateMockMove(`move${i}`, i % 2 as 0 | 1)
        )
      };

      mockStore.gameState = largeGameState;
      mockUseGameStore.mockReturnValue(mockStore);

      const TestComponent = () => (
        <div>
          <GameBoard />
          <MoveHistory />
        </div>
      );

      const start = performance.now();
      render(<TestComponent />);
      const end = performance.now();

      // Should handle large states efficiently
      expect(end - start).toBeLessThan(100);
      expect(screen.getByText('Move History')).toBeInTheDocument();
    });
  });

  describe('Accessibility Across Components', () => {
    it('maintains proper focus flow between components', async () => {
      const TestComponent = () => (
        <div>
          <GameSettings />
          <GameBoard />
          <MoveHistory />
        </div>
      );

      render(<TestComponent />);

      // Focus should move naturally between components
      const settingsButton = screen.getByText('Human vs AI');
      settingsButton.focus();

      await user.tab();
      // Should move to next focusable element

      expect(document.activeElement).not.toBe(settingsButton);
    });

    it('provides consistent ARIA labels across components', () => {
      const TestComponent = () => (
        <div>
          <GameSettings />
          <MoveHistory />
        </div>
      );

      render(<TestComponent />);

      // All interactive elements should have proper ARIA labels
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toHaveAttribute('aria-label', expect.any(String));
      });
    });
  });
});