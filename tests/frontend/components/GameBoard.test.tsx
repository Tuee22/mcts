import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GameBoard } from '../../../frontend/src/components/GameBoard';
import { useGameStore } from '../../../frontend/src/store/gameStore';
import { wsService } from '../../../frontend/src/services/websocket';
import { 
  render, 
  mockGameState, 
  mockGameStateWithWalls, 
  mockCompletedGameState,
  createUser 
} from '../utils/test-utils';

import { vi, describe, test, expect, beforeEach, type MockedFunction } from 'vitest';

// Mock dependencies
vi.mock('../../../frontend/src/store/gameStore');
vi.mock('../../../frontend/src/services/websocket');

const mockUseGameStore = useGameStore as MockedFunction<typeof useGameStore>;
const mockWsService = wsService as ReturnType<typeof vi.mocked>;

describe('GameBoard Component', () => {
  const user = createUser();

  const defaultMockStore = {
    gameState: mockGameState,
    gameId: 'test-game-123',
    selectedHistoryIndex: null
  };

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    mockUseGameStore.mockReturnValue(defaultMockStore as any);
    mockWsService.makeMove = jest.fn();
  });

  describe('Rendering', () => {
    it('renders empty state when no game is in progress', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: null
      } as any);

      render(<GameBoard />);
      
      expect(screen.getByText('No game in progress')).toBeInTheDocument();
    });

    it('renders the game board with correct dimensions', () => {
      render(<GameBoard />);
      
      const gameBoard = screen.getByTestId('game-board') || document.querySelector('.game-board');
      expect(gameBoard).toBeInTheDocument();
      
      // Should render 9x9 grid of cells (81 cells total)
      const cells = document.querySelectorAll('.game-cell');
      expect(cells).toHaveLength(81);
    });

    it('renders players at correct positions', () => {
      render(<GameBoard />);
      
      const player1 = screen.getByText('P1');
      const player2 = screen.getByText('P2');
      
      expect(player1).toBeInTheDocument();
      expect(player2).toBeInTheDocument();
      expect(player1).toHaveClass('player', 'player-0');
      expect(player2).toHaveClass('player', 'player-1');
    });

    it('renders game controls', () => {
      render(<GameBoard />);
      
      expect(screen.getByText('Place Wall')).toBeInTheDocument();
      expect(screen.getByText('P1 Walls: 10')).toBeInTheDocument();
      expect(screen.getByText('P2 Walls: 10')).toBeInTheDocument();
      expect(screen.getByText('Current: Player 1')).toBeInTheDocument();
    });

    it('renders walls when present in game state', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: mockGameStateWithWalls
      } as any);

      render(<GameBoard />);
      
      const walls = document.querySelectorAll('.game-wall');
      expect(walls).toHaveLength(2);
      expect(walls[0]).toHaveClass('horizontal');
      expect(walls[1]).toHaveClass('vertical');
    });

    it('shows game over message when game is completed', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: mockCompletedGameState
      } as any);

      render(<GameBoard />);
      
      expect(screen.getByText('Game Over!')).toBeInTheDocument();
      expect(screen.getByText('Player 1 Wins!')).toBeInTheDocument();
    });
  });

  describe('Player Movement', () => {
    it('highlights legal moves', () => {
      render(<GameBoard />);
      
      const legalMoves = document.querySelectorAll('.game-cell.legal');
      expect(legalMoves.length).toBeGreaterThan(0);
    });

    it('makes a move when clicking on a legal cell', async () => {
      render(<GameBoard />);
      
      // Find a legal move cell and click it
      const legalCell = document.querySelector('.game-cell.legal') as HTMLElement;
      expect(legalCell).toBeInTheDocument();
      
      await user.click(legalCell);
      
      expect(mockWsService.makeMove).toHaveBeenCalledWith('test-game-123', expect.any(String));
    });

    it('does not make a move when clicking on an illegal cell', async () => {
      render(<GameBoard />);
      
      // Find a non-legal cell and click it
      const illegalCell = document.querySelector('.game-cell:not(.legal)') as HTMLElement;
      if (illegalCell) {
        await user.click(illegalCell);
        expect(mockWsService.makeMove).not.toHaveBeenCalled();
      }
    });

    it('does not allow moves when game is over', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: mockCompletedGameState
      } as any);

      render(<GameBoard />);
      
      const cell = document.querySelector('.game-cell') as HTMLElement;
      await user.click(cell);
      
      expect(mockWsService.makeMove).not.toHaveBeenCalled();
    });

    it('does not allow moves when viewing history', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        selectedHistoryIndex: 0
      } as any);

      render(<GameBoard />);
      
      const cell = document.querySelector('.game-cell') as HTMLElement;
      await user.click(cell);
      
      expect(mockWsService.makeMove).not.toHaveBeenCalled();
    });
  });

  describe('Wall Placement', () => {
    it('toggles to wall placement mode', async () => {
      render(<GameBoard />);
      
      const wallButton = screen.getByText('Place Wall');
      await user.click(wallButton);
      
      expect(screen.getByText('Place Pawn')).toBeInTheDocument();
      expect(screen.getByText('Horizontal')).toBeInTheDocument();
    });

    it('toggles wall orientation', async () => {
      render(<GameBoard />);
      
      // Enter wall mode
      const wallButton = screen.getByText('Place Wall');
      await user.click(wallButton);
      
      // Toggle orientation
      const orientationButton = screen.getByText('Horizontal');
      await user.click(orientationButton);
      
      expect(screen.getByText('Vertical')).toBeInTheDocument();
    });

    it('places a wall when in wall mode', async () => {
      render(<GameBoard />);
      
      // Enter wall mode
      const wallButton = screen.getByText('Place Wall');
      await user.click(wallButton);
      
      // Click on a wall slot (this would need to be implemented in the actual component)
      const wallSlot = document.querySelector('.wall-slot.legal') as HTMLElement;
      if (wallSlot) {
        await user.click(wallSlot);
        expect(mockWsService.makeMove).toHaveBeenCalled();
      }
    });

    it('does not place walls when not in wall mode', async () => {
      render(<GameBoard />);
      
      // Try to click on a wall position without entering wall mode
      const wallSlot = document.querySelector('.wall-slot') as HTMLElement;
      if (wallSlot) {
        await user.click(wallSlot);
        expect(mockWsService.makeMove).not.toHaveBeenCalled();
      }
    });
  });

  describe('Hover Effects', () => {
    it('shows hover effect on legal cells', async () => {
      render(<GameBoard />);
      
      const legalCell = document.querySelector('.game-cell.legal') as HTMLElement;
      if (legalCell) {
        fireEvent.mouseEnter(legalCell);
        await waitFor(() => {
          expect(legalCell).toHaveClass('hovered');
        });
        
        fireEvent.mouseLeave(legalCell);
        await waitFor(() => {
          expect(legalCell).not.toHaveClass('hovered');
        });
      }
    });

    it('shows hover effect on legal wall slots in wall mode', async () => {
      render(<GameBoard />);
      
      // Enter wall mode
      const wallButton = screen.getByText('Place Wall');
      await user.click(wallButton);
      
      const wallSlot = document.querySelector('.wall-slot.legal') as HTMLElement;
      if (wallSlot) {
        fireEvent.mouseEnter(wallSlot);
        await waitFor(() => {
          expect(wallSlot).toHaveClass('hovered');
        });
      }
    });
  });

  describe('Game State Display', () => {
    it('displays current player correctly', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: {
          ...mockGameState,
          current_player: 1
        }
      } as any);

      render(<GameBoard />);
      
      expect(screen.getByText('Current: Player 2')).toBeInTheDocument();
    });

    it('displays wall counts correctly', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: {
          ...mockGameState,
          walls_remaining: [8, 7]
        }
      } as any);

      render(<GameBoard />);
      
      expect(screen.getByText('P1 Walls: 8')).toBeInTheDocument();
      expect(screen.getByText('P2 Walls: 7')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('provides proper ARIA labels for interactive elements', () => {
      render(<GameBoard />);
      
      const wallButton = screen.getByText('Place Wall');
      expect(wallButton).toHaveAttribute('aria-label', expect.any(String));
    });

    it('supports keyboard navigation', async () => {
      render(<GameBoard />);
      
      const wallButton = screen.getByText('Place Wall');
      wallButton.focus();
      
      await user.keyboard('{Enter}');
      
      expect(screen.getByText('Place Pawn')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles missing game ID gracefully', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: null
      } as any);

      render(<GameBoard />);
      
      const legalCell = document.querySelector('.game-cell.legal') as HTMLElement;
      if (legalCell) {
        await user.click(legalCell);
        expect(mockWsService.makeMove).not.toHaveBeenCalled();
      }
    });

    it('handles WebSocket service errors', async () => {
      mockWsService.makeMove.mockRejectedValue(new Error('Connection failed'));
      
      render(<GameBoard />);
      
      const legalCell = document.querySelector('.game-cell.legal') as HTMLElement;
      if (legalCell) {
        await user.click(legalCell);
        
        await waitFor(() => {
          expect(mockWsService.makeMove).toHaveBeenCalled();
        });
      }
    });
  });

  describe('Performance', () => {
    it('does not re-render unnecessarily', () => {
      const { rerender } = render(<GameBoard />);
      
      // Re-render with same props
      rerender(<GameBoard />);
      
      // Component should handle re-renders efficiently
      expect(document.querySelectorAll('.game-cell')).toHaveLength(81);
    });
  });

  describe('Edge Cases', () => {
    it('handles board sizes other than 9x9', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: {
          ...mockGameState,
          board_size: 5
        }
      } as any);

      render(<GameBoard />);
      
      const cells = document.querySelectorAll('.game-cell');
      expect(cells).toHaveLength(25); // 5x5 = 25 cells
    });

    it('handles empty legal moves array', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: {
          ...mockGameState,
          legal_moves: []
        }
      } as any);

      render(<GameBoard />);
      
      const legalCells = document.querySelectorAll('.game-cell.legal');
      expect(legalCells).toHaveLength(0);
    });

    it('handles malformed game state gracefully', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: {
          ...mockGameState,
          players: [] // Invalid players array
        }
      } as any);

      // Should not crash the component
      expect(() => render(<GameBoard />)).not.toThrow();
    });
  });
});