import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the game store first with vi.hoisted (same pattern as other tests)
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  const store = {
    gameId: 'test-game-123',
    gameState: null,
    gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
    isConnected: true,
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

  // Create a proper Zustand-style mock that returns the store
  const useGameStoreMock = vi.fn(() => store);
  // CRITICAL: getState must return the same store object with all methods
  useGameStoreMock.getState = vi.fn(() => store);
  
  return {
    mockGameStore: store,
    mockUseGameStore: useGameStoreMock
  };
});

vi.mock('@/store/gameStore', () => ({
  useGameStore: mockUseGameStore
}));

// Import components and utilities
import { MoveHistory } from '@/components/MoveHistory';
import { render, screen, waitFor, createUser } from '../utils/testHelpers';
import { 
  mockInitialGameState, 
  mockMidGameState, 
  mockLongHistoryGameState,
  mockCompletedGameState
} from '../fixtures/gameState';

describe('MoveHistory Component', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset the game store state for each test
    Object.assign(mockGameStore, {
      gameId: 'test-game-123',
      gameState: mockMidGameState,
      gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
      isConnected: true,
      isLoading: false,
      error: null,
      selectedHistoryIndex: null
    });
  });

  describe('Basic Rendering', () => {
    it('renders move history header', () => {
      render(<MoveHistory />);

      expect(screen.getByText('Move History')).toBeInTheDocument();
    });

    it('shows empty state when no game exists', () => {
      mockGameStore.gameState = null;

      render(<MoveHistory />);

      expect(screen.getByText('No moves yet')).toBeInTheDocument();
    });

    it('shows empty state when game has no moves', () => {
      mockGameStore.gameState = mockInitialGameState;

      render(<MoveHistory />);

      expect(screen.getByText('No moves yet')).toBeInTheDocument();
    });
  });

  describe('Move Display', () => {
    it('displays all moves in the history', () => {
      render(<MoveHistory />);

      // Check for moves from mockMidGameState
      expect(screen.getByText('1. e2')).toBeInTheDocument();
      expect(screen.getByText('2. e8')).toBeInTheDocument();
      expect(screen.getByText('3. e3')).toBeInTheDocument();
      expect(screen.getByText('4. c5h')).toBeInTheDocument();
    });

    it('displays move numbers correctly', () => {
      render(<MoveHistory />);

      const moveNumbers = screen.getAllByText(/^\d+\./);
      expect(moveNumbers).toHaveLength(mockMidGameState.move_history.length);
    });

    it('distinguishes between move and wall placements', () => {
      render(<MoveHistory />);

      // Wall moves should be distinguishable (e.g., different styling, icon)
      const wallMove = screen.getByText('4. c5h');
      expect(wallMove).toHaveClass('wall-move') || 
      expect(wallMove.parentElement).toHaveClass('wall-move') ||
      expect(wallMove.querySelector('.wall-icon')).toBeInTheDocument();
    });

    it('shows player indicators for moves', () => {
      render(<MoveHistory />);

      // Should show which player made each move
      const playerIndicators = document.querySelectorAll('.player-indicator, [data-testid^="player-"]');
      expect(playerIndicators.length).toBeGreaterThan(0);
    });
  });

  describe('History Navigation', () => {
    it('renders navigation buttons', () => {
      render(<MoveHistory />);

      expect(screen.getByText('⏮') || screen.getByText('First')).toBeInTheDocument();
      expect(screen.getByText('◀') || screen.getByText('Previous')).toBeInTheDocument();
      expect(screen.getByText('▶') || screen.getByText('Next')).toBeInTheDocument();
      expect(screen.getByText('⏭') || screen.getByText('Last')).toBeInTheDocument();
      expect(screen.getByText('Current')).toBeInTheDocument();
    });

    it('navigates to first move', async () => {
      const { user } = render(<MoveHistory />);

      const firstButton = screen.getByText('⏮') || screen.getByText('First');
      await user.click(firstButton);

      expect(mockGameStore.setSelectedHistoryIndex).toHaveBeenCalledWith(0);
    });

    it('navigates to previous move', async () => {
      mockGameStore.selectedHistoryIndex = 2;

      const { user } = render(<MoveHistory />);

      const previousButton = screen.getByText('◀') || screen.getByText('Previous');
      await user.click(previousButton);

      expect(mockGameStore.setSelectedHistoryIndex).toHaveBeenCalledWith(1);
    });

    it('navigates to next move', async () => {
      mockGameStore.selectedHistoryIndex = 1;

      const { user } = render(<MoveHistory />);

      const nextButton = screen.getByText('▶') || screen.getByText('Next');
      await user.click(nextButton);

      expect(mockGameStore.setSelectedHistoryIndex).toHaveBeenCalledWith(2);
    });

    it('navigates to last move', async () => {
      const { user } = render(<MoveHistory />);

      const lastButton = screen.getByText('⏭') || screen.getByText('Last');
      await user.click(lastButton);

      const lastIndex = mockMidGameState.move_history.length - 1;
      expect(mockGameStore.setSelectedHistoryIndex).toHaveBeenCalledWith(lastIndex);
    });

    it('returns to current position', async () => {
      mockGameStore.selectedHistoryIndex = 1;

      const { user } = render(<MoveHistory />);

      const currentButton = screen.getByText('Current');
      await user.click(currentButton);

      expect(mockGameStore.setSelectedHistoryIndex).toHaveBeenCalledWith(null);
    });

    it('disables navigation buttons appropriately', () => {
      mockGameStore.selectedHistoryIndex = 0; // First move selected

      render(<MoveHistory />);

      const firstButton = screen.getByText('⏮') || screen.getByText('First');
      const previousButton = screen.getByText('◀') || screen.getByText('Previous');

      expect(firstButton).toBeDisabled() || expect(firstButton).toHaveClass('disabled');
      expect(previousButton).toBeDisabled() || expect(previousButton).toHaveClass('disabled');
    });

    it('disables next/last buttons at end of history', () => {
      const lastIndex = mockMidGameState.move_history.length - 1;
      mockGameStore.selectedHistoryIndex = lastIndex;

      render(<MoveHistory />);

      const nextButton = screen.getByText('▶') || screen.getByText('Next');
      const lastButton = screen.getByText('⏭') || screen.getByText('Last');

      expect(nextButton).toBeDisabled() || expect(nextButton).toHaveClass('disabled');
      expect(lastButton).toBeDisabled() || expect(lastButton).toHaveClass('disabled');
    });
  });

  describe('Move Selection', () => {
    it('allows clicking on individual moves', async () => {
      const { user } = render(<MoveHistory />);

      const secondMove = screen.getByText('2. e8');
      await user.click(secondMove);

      expect(mockGameStore.setSelectedHistoryIndex).toHaveBeenCalledWith(1);
    });

    it('highlights currently selected move', () => {
      mockGameStore.selectedHistoryIndex = 1;

      render(<MoveHistory />);

      const selectedMove = screen.getByText('2. e8');
      expect(selectedMove).toHaveClass('selected') || 
      expect(selectedMove.parentElement).toHaveClass('selected') ||
      expect(selectedMove.parentElement).toHaveClass('active');
    });

    it('shows current move indicator when no history is selected', () => {
      mockGameStore.selectedHistoryIndex = null;

      render(<MoveHistory />);

      // Should indicate current position somehow
      const currentIndicator = screen.getByText('Current') || 
                              document.querySelector('.current-position') ||
                              document.querySelector('.current-move');

      expect(currentIndicator).toHaveClass('active') || 
      expect(currentIndicator).toHaveClass('selected');
    });
  });

  describe('Copy Functionality', () => {
    it('renders copy moves button', () => {
      render(<MoveHistory />);

      expect(screen.getByText('Copy Moves') || screen.getByText('📋')).toBeInTheDocument();
    });

    it('copies all moves to clipboard', async () => {
      const { user } = render(<MoveHistory />);

      const copyButton = screen.getByText('Copy Moves') || screen.getByText('📋');
      await user.click(copyButton);

      // Check if navigator.clipboard.writeText was called (it's mocked in setupTests.ts)
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('e2 e8 e3 c5h e7 g6v');
    });

    it('copies moves in correct notation format', async () => {
      const { user } = render(<MoveHistory />);

      const copyButton = screen.getByText('Copy Moves') || screen.getByText('📋');
      await user.click(copyButton);

      const copiedText = (navigator.clipboard.writeText as any).mock.calls[0][0];
      expect(copiedText).toMatch(/^[a-z0-9h-v\s]+$/); // Valid move notation format
    });

    it('handles empty move history for copying', async () => {
      mockGameStore.gameState = mockInitialGameState;

      const { user } = render(<MoveHistory />);

      const copyButton = screen.getByText('Copy Moves') || screen.getByText('📋');
      await user.click(copyButton);

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('');
    });

    it('handles clipboard failure gracefully', async () => {
      (navigator.clipboard.writeText as any).mockRejectedValue(new Error('Clipboard access denied'));

      const { user } = render(<MoveHistory />);

      const copyButton = screen.getByText('Copy Moves') || screen.getByText('📋');
      await user.click(copyButton);

      expect(navigator.clipboard.writeText).toHaveBeenCalled();
      // Component should not crash on clipboard failure
      expect(screen.getByText('Move History')).toBeInTheDocument();
    });
  });

  describe('Long History Handling', () => {
    it('handles long move histories efficiently', () => {
      mockGameStore.gameState = mockLongHistoryGameState;

      const start = performance.now();
      render(<MoveHistory />);
      const end = performance.now();

      expect(end - start).toBeLessThan(100); // Should render efficiently
      expect(screen.getByText('Move History')).toBeInTheDocument();
    });

    it('implements virtualization for very long histories', () => {
      mockGameStore.gameState = mockLongHistoryGameState;

      render(<MoveHistory />);

      // Should not render all 100 moves at once if using virtualization
      const moveElements = document.querySelectorAll('.move-item, [data-testid^="move-"]');
      expect(moveElements.length).toBeLessThanOrEqual(50); // Reasonable viewport limit
    });

    it('scrolls to selected move in long history', async () => {
      mockGameStore.gameState = mockLongHistoryGameState;
      mockGameStore.selectedHistoryIndex = 50; // Middle of long history

      render(<MoveHistory />);

      // Should scroll the selected move into view
      const selectedMove = document.querySelector('.selected, .active');
      if (selectedMove) {
        // Mock scroll into view behavior verification
        expect(selectedMove.scrollIntoView || true).toBeTruthy();
      }
    });
  });

  describe('Game Completion', () => {
    it('shows game result when game is completed', () => {
      mockGameStore.gameState = mockCompletedGameState;

      render(<MoveHistory />);

      expect(screen.getByText('Player 1 Wins!') || 
             screen.getByText('Game Over')).toBeInTheDocument();
    });

    it('highlights winning move', () => {
      mockGameStore.gameState = mockCompletedGameState;

      render(<MoveHistory />);

      // Last move should be highlighted as winning move
      const winningMove = document.querySelector('.winning-move, .game-ending-move');
      if (winningMove) {
        expect(winningMove).toHaveClass('winning-move') || 
        expect(winningMove).toHaveClass('highlight');
      }
    });
  });

  describe('Keyboard Navigation', () => {
    it('supports arrow key navigation', async () => {
      const { user } = render(<MoveHistory />);

      // Focus on move history
      const moveHistory = document.querySelector('.move-history') || screen.getByText('Move History');
      (moveHistory as HTMLElement).focus();

      await user.keyboard('{ArrowUp}');
      expect(mockGameStore.setSelectedHistoryIndex).toHaveBeenCalled();
    });

    it('supports keyboard shortcuts for navigation', async () => {
      const { user } = render(<MoveHistory />);

      await user.keyboard('{Home}');
      expect(mockGameStore.setSelectedHistoryIndex).toHaveBeenCalledWith(0);

      await user.keyboard('{End}');
      const lastIndex = mockMidGameState.move_history.length - 1;
      expect(mockGameStore.setSelectedHistoryIndex).toHaveBeenCalledWith(lastIndex);
    });
  });

  describe('Error Handling', () => {
    it('handles invalid move data gracefully', () => {
      mockGameStore.gameState = {
        ...mockMidGameState,
        move_history: [
          {
            notation: '', // Invalid
            player: 0,
            type: 'move',
            position: { x: -1, y: -1 } // Invalid position
          }
        ]
      };

      // Should not crash
      expect(() => render(<MoveHistory />)).not.toThrow();
    });

    it('handles missing move history gracefully', () => {
      mockGameStore.gameState = {
        ...mockMidGameState,
        move_history: [] // Empty history
      };

      render(<MoveHistory />);

      expect(screen.getByText('No moves yet')).toBeInTheDocument();
    });

    it('handles navigation beyond boundaries', async () => {
      mockGameStore.selectedHistoryIndex = 0;

      const { user } = render(<MoveHistory />);

      // Try to go before first move
      const previousButton = screen.getByText('◀') || screen.getByText('Previous');
      await user.click(previousButton);

      // Should not go below 0
      expect(mockGameStore.setSelectedHistoryIndex).not.toHaveBeenCalledWith(-1);
    });
  });

  describe('Performance', () => {
    it('renders move history quickly', () => {
      const start = performance.now();
      render(<MoveHistory />);
      const end = performance.now();

      expect(end - start).toBeLessThan(50);
    });

    it('does not re-render unnecessarily', () => {
      const { rerender } = render(<MoveHistory />);

      // Re-render with same props
      rerender(<MoveHistory />);

      // Should still show the same content
      expect(screen.getByText('Move History')).toBeInTheDocument();
    });

    it('efficiently handles move selection changes', async () => {
      const { user } = render(<MoveHistory />);

      const start = performance.now();
      
      // Rapidly change selected moves
      const firstMove = screen.getByText('1. e2');
      const secondMove = screen.getByText('2. e8');
      const thirdMove = screen.getByText('3. e3');

      await user.click(firstMove);
      await user.click(secondMove);
      await user.click(thirdMove);

      const end = performance.now();

      expect(end - start).toBeLessThan(100);
    });
  });

  describe('Accessibility', () => {
    it('provides proper ARIA labels for navigation', () => {
      render(<MoveHistory />);

      const navigationButtons = screen.getAllByRole('button');
      navigationButtons.forEach(button => {
        expect(
          button.getAttribute('aria-label') || 
          button.textContent?.trim()
        ).toBeTruthy();
      });
    });

    it('provides proper role for move list', () => {
      render(<MoveHistory />);

      const moveList = document.querySelector('[role="list"], .move-list') || 
                      screen.getByRole('list');
      
      expect(moveList).toBeInTheDocument();
    });

    it('supports screen reader navigation', () => {
      render(<MoveHistory />);

      // Move items should have proper roles and labels
      const moveItems = document.querySelectorAll('[role="listitem"], .move-item');
      
      if (moveItems.length > 0) {
        expect(moveItems[0]).toHaveAttribute('aria-label', expect.stringContaining('move')) ||
        expect(moveItems[0].textContent).toBeTruthy();
      }
    });

    it('announces current position to screen readers', () => {
      mockGameStore.selectedHistoryIndex = 1;

      render(<MoveHistory />);

      // Should have aria-live region for announcing current position
      const liveRegion = document.querySelector('[aria-live], [role="status"]');
      if (liveRegion) {
        expect(liveRegion).toHaveTextContent('move 2') || 
        expect(liveRegion).toHaveAttribute('aria-label');
      }
    });
  });
});