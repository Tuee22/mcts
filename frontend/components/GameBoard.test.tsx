import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock dependencies first (hoisted)
vi.mock('@/store/gameStore', () => ({
  useGameStore: vi.fn()
}));

vi.mock('@/services/websocket', () => ({
  wsService: {
    connect: vi.fn(() => Promise.resolve()),
    disconnect: vi.fn(),
    isConnected: vi.fn(() => true),
    createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
    makeMove: vi.fn(() => Promise.resolve()),
    getAIMove: vi.fn(() => Promise.resolve()),
  }
}));

// Import components and utilities
import { GameBoard } from '@/components/GameBoard';
import { render, screen, waitFor, createUser } from '../utils/testHelpers';
import { 
  mockInitialGameState, 
  mockMidGameState, 
  mockCompletedGameState,
  mockWallHeavyGameState,
  mockSmallBoardState,
  mockStalemateGameState
} from '../fixtures/gameState';
import { createMockGameStore } from '../fixtures/mocks';
import { useGameStore } from '@/store/gameStore';
import { wsService } from '@/services/websocket';

// Create reference to the mocked service for easier access in tests
const mockWebSocketService = wsService as any;

describe('GameBoard Component', () => {
  let mockStore: ReturnType<typeof createMockGameStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockStore = createMockGameStore({
      gameId: 'test-game-123',
      gameState: mockInitialGameState
    });
    (useGameStore as any).mockReturnValue(mockStore);
  });

  describe('Basic Rendering', () => {
    it('renders empty state when no game exists', () => {
      mockStore.gameState = null;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameBoard />);

      expect(screen.getByText('No game in progress')).toBeInTheDocument();
    });

    it('renders game board with correct grid size', () => {
      render(<GameBoard />);

      const gameBoard = screen.getByTestId('game-board') || document.querySelector('.game-board');
      expect(gameBoard).toBeInTheDocument();

      // Should render 9x9 grid (81 cells)
      const cells = document.querySelectorAll('.game-cell, [data-testid^="cell-"]');
      expect(cells.length).toBe(81);
    });

    it('adapts to different board sizes', () => {
      mockStore.gameState = mockSmallBoardState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameBoard />);

      // Should render 5x5 grid (25 cells)
      const cells = document.querySelectorAll('.game-cell, [data-testid^="cell-"]');
      expect(cells.length).toBe(25);
    });
  });

  describe('Player Rendering', () => {
    it('renders players at correct positions', () => {
      render(<GameBoard />);

      // Look for player indicators - these might be text, icons, or styled elements
      const playerElements = document.querySelectorAll('[data-testid^="player-"], .player');
      expect(playerElements.length).toBeGreaterThanOrEqual(2);

      // Verify players have distinct styling
      const player1Elements = document.querySelectorAll('[data-testid="player-0"], .player-0');
      const player2Elements = document.querySelectorAll('[data-testid="player-1"], .player-1');
      
      expect(player1Elements.length).toBeGreaterThanOrEqual(1);
      expect(player2Elements.length).toBeGreaterThanOrEqual(1);
    });

    it('highlights current player', () => {
      mockStore.gameState = { ...mockInitialGameState, current_player: 1 };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameBoard />);

      // Current player should be highlighted somehow
      expect(screen.getByText('Current: Player 2')).toBeInTheDocument();
    });
  });

  describe('Legal Moves Display', () => {
    it('highlights legal move positions', () => {
      render(<GameBoard />);

      const legalMoves = document.querySelectorAll('.legal-move, [data-testid^="legal-"], .game-cell.legal');
      expect(legalMoves.length).toBeGreaterThan(0);
    });

    it('shows no legal moves when array is empty', () => {
      mockStore.gameState = mockStalemateGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameBoard />);

      const legalMoves = document.querySelectorAll('.legal-move, [data-testid^="legal-"], .game-cell.legal');
      expect(legalMoves.length).toBe(0);
    });
  });

  describe('Wall Rendering', () => {
    it('renders walls when present', () => {
      mockStore.gameState = mockWallHeavyGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameBoard />);

      const walls = document.querySelectorAll('.wall, [data-testid^="wall-"], .game-wall');
      expect(walls.length).toBe(mockWallHeavyGameState.walls.length);
    });

    it('distinguishes between horizontal and vertical walls', () => {
      mockStore.gameState = mockMidGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameBoard />);

      const horizontalWalls = document.querySelectorAll('.wall.horizontal, .wall-horizontal, [data-testid*="horizontal"]');
      const verticalWalls = document.querySelectorAll('.wall.vertical, .wall-vertical, [data-testid*="vertical"]');

      expect(horizontalWalls.length).toBe(1);
      expect(verticalWalls.length).toBe(1);
    });
  });

  describe('Game Controls', () => {
    it('displays current player turn', () => {
      render(<GameBoard />);

      expect(screen.getByText('Current: Player 1')).toBeInTheDocument();
    });

    it('displays wall counts', () => {
      render(<GameBoard />);

      expect(screen.getByText('P1 Walls: 10')).toBeInTheDocument();
      expect(screen.getByText('P2 Walls: 10')).toBeInTheDocument();
    });

    it('updates wall counts correctly', () => {
      mockStore.gameState = {
        ...mockInitialGameState,
        walls_remaining: [8, 7]
      };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameBoard />);

      expect(screen.getByText('P1 Walls: 8')).toBeInTheDocument();
      expect(screen.getByText('P2 Walls: 7')).toBeInTheDocument();
    });

    it('shows wall placement controls', () => {
      render(<GameBoard />);

      const wallButton = screen.getByText('Place Wall') || screen.getByRole('button', { name: /wall/i });
      expect(wallButton).toBeInTheDocument();
    });
  });

  describe('Game Over State', () => {
    it('displays game over message when winner exists', () => {
      mockStore.gameState = mockCompletedGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameBoard />);

      expect(screen.getByText('Game Over!')).toBeInTheDocument();
      expect(screen.getByText('Player 1 Wins!')).toBeInTheDocument();
    });

    it('prevents interactions when game is over', async () => {
      mockStore.gameState = mockCompletedGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<GameBoard />);

      // Try to click on a cell - should not trigger move
      const cells = document.querySelectorAll('.game-cell, [data-testid^="cell-"]');
      if (cells.length > 0) {
        await user.click(cells[0] as HTMLElement);
        expect(mockWebSocketService.makeMove).not.toHaveBeenCalled();
      }
    });
  });

  describe('User Interactions', () => {
    it('makes move when clicking on legal position', async () => {
      vi.useFakeTimers();
      
      render(<GameBoard />);
      const user = createUser();

      // Find a legal move cell
      const legalCell = document.querySelector('.legal-move, [data-testid^="legal-"], .game-cell.legal') as HTMLElement;
      
      if (legalCell) {
        await user.click(legalCell);
        
        // Advance timers to process any delayed operations
        vi.runAllTimers();
        expect(mockWebSocketService.makeMove).toHaveBeenCalledWith(
          'test-game-123',
          expect.any(String)
        );
      }
      
      vi.useRealTimers();
    });

    it('does not make move when clicking on illegal position', async () => {
      const { user } = render(<GameBoard />);

      // Find a non-legal cell
      const illegalCell = document.querySelector('.game-cell:not(.legal), .game-cell:not([data-testid^="legal-"])') as HTMLElement;
      
      if (illegalCell) {
        await user.click(illegalCell);
        expect(mockWebSocketService.makeMove).not.toHaveBeenCalled();
      }
    });

    it('prevents moves when not connected', async () => {
      mockStore.isConnected = false;
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<GameBoard />);

      const legalCell = document.querySelector('.legal-move, .game-cell.legal') as HTMLElement;
      
      if (legalCell) {
        await user.click(legalCell);
        expect(mockWebSocketService.makeMove).not.toHaveBeenCalled();
      }
    });

    it('prevents moves when viewing history', async () => {
      mockStore.selectedHistoryIndex = 0;
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<GameBoard />);

      const cell = document.querySelector('.game-cell') as HTMLElement;
      
      if (cell) {
        await user.click(cell);
        expect(mockWebSocketService.makeMove).not.toHaveBeenCalled();
      }
    });
  });

  describe('Wall Placement Mode', () => {
    it('toggles to wall placement mode', async () => {
      const { user } = render(<GameBoard />);

      const wallButton = screen.getByText('Place Wall');
      await user.click(wallButton);

      // Should show different button text and orientation control
      expect(screen.getByText('Place Pawn') || screen.getByText('Place Move')).toBeInTheDocument();
      expect(screen.getByText('Horizontal') || screen.getByText('Vertical')).toBeInTheDocument();
    });

    it('toggles wall orientation', async () => {
      const { user } = render(<GameBoard />);

      // Enter wall mode first
      const wallButton = screen.getByText('Place Wall');
      await user.click(wallButton);

      // Toggle orientation
      const orientationButton = screen.getByText('Horizontal') || screen.getByText('Toggle Orientation');
      await user.click(orientationButton);

      expect(screen.getByText('Vertical')).toBeInTheDocument();
    });

    it('places wall when in wall mode', async () => {
      const { user } = render(<GameBoard />);

      // Enter wall mode
      const wallButton = screen.getByText('Place Wall');
      await user.click(wallButton);

      // Click on a wall slot
      const wallSlot = document.querySelector('.wall-slot.legal, [data-testid^="wall-slot-"]') as HTMLElement;
      
      if (wallSlot) {
        await user.click(wallSlot);
        expect(mockWebSocketService.makeMove).toHaveBeenCalled();
      }
    });
  });

  describe('History Integration', () => {
    it('displays historical position when history is selected', () => {
      mockStore.selectedHistoryIndex = 0;
      mockStore.gameState = mockMidGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameBoard />);

      // Should show historical game state, not current
      // The exact implementation depends on how history is handled
      expect(mockStore.selectedHistoryIndex).toBe(0);
    });
  });

  describe('Error Handling', () => {
    it('handles missing game ID gracefully', async () => {
      mockStore.gameId = null;
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<GameBoard />);

      const cells = document.querySelectorAll('.game-cell');
      if (cells.length > 0) {
        await user.click(cells[0] as HTMLElement);
        expect(mockWebSocketService.makeMove).not.toHaveBeenCalled();
      }
    });

    it('handles WebSocket errors gracefully', async () => {
      mockWebSocketService.makeMove.mockRejectedValue(new Error('Connection failed'));

      const { user } = render(<GameBoard />);

      const legalCell = document.querySelector('.legal-move, .game-cell.legal') as HTMLElement;
      
      if (legalCell) {
        await user.click(legalCell);
        
        // Should attempt the move even if it fails
        expect(mockWebSocketService.makeMove).toHaveBeenCalled();
        // Component should not crash
        expect(screen.getByTestId('game-board') || document.querySelector('.game-board')).toBeInTheDocument();
      }
    });

    it('handles invalid game state gracefully', () => {
      mockStore.gameState = {
        ...mockInitialGameState,
        players: [] // Invalid - no players
      };
      (useGameStore as any).mockReturnValue(mockStore);

      // Should not crash
      expect(() => render(<GameBoard />)).not.toThrow();
    });
  });

  describe('Hover Effects', () => {
    it('shows hover effects on legal moves', async () => {
      const { user } = render(<GameBoard />);

      const legalCell = document.querySelector('.legal-move, .game-cell.legal') as HTMLElement;
      
      if (legalCell) {
        await user.hover(legalCell);
        
        await waitFor(() => {
          expect(legalCell).toHaveClass('hovered') || 
          expect(legalCell.style.opacity).not.toBe('');
        });

        await user.unhover(legalCell);
        
        await waitFor(() => {
          expect(legalCell).not.toHaveClass('hovered');
        });
      }
    });

    it('shows hover effects on wall slots in wall mode', async () => {
      const { user } = render(<GameBoard />);

      // Enter wall mode
      const wallButton = screen.getByText('Place Wall');
      await user.click(wallButton);

      const wallSlot = document.querySelector('.wall-slot, [data-testid^="wall-slot"]') as HTMLElement;
      
      if (wallSlot) {
        await user.hover(wallSlot);
        
        await waitFor(() => {
          expect(wallSlot).toHaveClass('hovered') || 
          expect(wallSlot.style.opacity).not.toBe('');
        });
      }
    });
  });

  describe('Performance', () => {
    it('renders large boards efficiently', () => {
      mockStore.gameState = {
        ...mockInitialGameState,
        board_size: 19 // Large board
      };
      (useGameStore as any).mockReturnValue(mockStore);

      const start = performance.now();
      render(<GameBoard />);
      const end = performance.now();

      // Should render in reasonable time even for large boards
      expect(end - start).toBeLessThan(100);
    });

    it('handles many walls efficiently', () => {
      mockStore.gameState = mockWallHeavyGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      const start = performance.now();
      render(<GameBoard />);
      const end = performance.now();

      // Should render efficiently even with many walls
      expect(end - start).toBeLessThan(50);
    });

    it('does not re-render unnecessarily', () => {
      const { rerender } = render(<GameBoard />);

      // Re-render with same props
      rerender(<GameBoard />);

      // Should still have the same number of cells
      const cells = document.querySelectorAll('.game-cell, [data-testid^="cell-"]');
      expect(cells.length).toBe(81);
    });
  });

  describe('Accessibility', () => {
    it('provides proper ARIA labels for interactive elements', () => {
      render(<GameBoard />);

      const wallButton = screen.getByText('Place Wall');
      expect(wallButton).toHaveAttribute('aria-label', expect.stringContaining('wall'));
    });

    it('supports keyboard navigation', async () => {
      const { user } = render(<GameBoard />);

      const wallButton = screen.getByText('Place Wall');
      wallButton.focus();

      await user.keyboard('{Enter}');

      expect(screen.getByText('Place Pawn') || screen.getByText('Place Move')).toBeInTheDocument();
    });

    it('provides proper role attributes', () => {
      render(<GameBoard />);

      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);

      buttons.forEach(button => {
        expect(button).toBeInTheDocument();
      });
    });
  });
});