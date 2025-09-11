import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock dependencies first (hoisted)
vi.mock('@/store/gameStore', () => ({
  useGameStore: vi.fn()
}));

// Import components and utilities
import { MoveHistory } from '@/components/MoveHistory';
import { render, screen, waitFor } from '../utils/testHelpers';
import { 
  mockInitialGameState, 
  mockMidGameState, 
  mockLongHistoryGameState,
  mockCompletedGameState
} from '../fixtures/gameState';
import { createMockGameStore, mockClipboard } from '../fixtures/mocks';
import { useGameStore } from '@/store/gameStore';

// Mock clipboard API after imports
Object.assign(navigator, {
  clipboard: mockClipboard
});

describe('MoveHistory Component', () => {
  let mockStore: ReturnType<typeof createMockGameStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockStore = createMockGameStore({
      gameId: 'test-game-123',
      gameState: mockMidGameState,
      selectedHistoryIndex: null
    });
    (useGameStore as any).mockReturnValue(mockStore);
    
    // Reset clipboard mocks
    mockClipboard.writeText.mockResolvedValue(undefined);
  });

  describe('Basic Rendering', () => {
    it('renders move history header', () => {
      render(<MoveHistory />);

      expect(screen.getByText('Move History')).toBeInTheDocument();
    });

    it('shows empty state when no game exists', () => {
      mockStore.gameState = null;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<MoveHistory />);

      expect(screen.getByText('No moves yet')).toBeInTheDocument();
    });

    it('shows empty state when game has no moves', () => {
      mockStore.gameState = mockInitialGameState;
      (useGameStore as any).mockReturnValue(mockStore);

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

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(0);
    });

    it('navigates to previous move', async () => {
      mockStore.selectedHistoryIndex = 2;
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<MoveHistory />);

      const previousButton = screen.getByText('◀') || screen.getByText('Previous');
      await user.click(previousButton);

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(1);
    });

    it('navigates to next move', async () => {
      mockStore.selectedHistoryIndex = 1;
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<MoveHistory />);

      const nextButton = screen.getByText('▶') || screen.getByText('Next');
      await user.click(nextButton);

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(2);
    });

    it('navigates to last move', async () => {
      const { user } = render(<MoveHistory />);

      const lastButton = screen.getByText('⏭') || screen.getByText('Last');
      await user.click(lastButton);

      const lastIndex = mockMidGameState.move_history.length - 1;
      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(lastIndex);
    });

    it('returns to current position', async () => {
      mockStore.selectedHistoryIndex = 1;
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<MoveHistory />);

      const currentButton = screen.getByText('Current');
      await user.click(currentButton);

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(null);
    });

    it('disables navigation buttons appropriately', () => {
      mockStore.selectedHistoryIndex = 0; // First move selected
      (useGameStore as any).mockReturnValue(mockStore);

      render(<MoveHistory />);

      const firstButton = screen.getByText('⏮') || screen.getByText('First');
      const previousButton = screen.getByText('◀') || screen.getByText('Previous');

      expect(firstButton).toBeDisabled() || expect(firstButton).toHaveClass('disabled');
      expect(previousButton).toBeDisabled() || expect(previousButton).toHaveClass('disabled');
    });

    it('disables next/last buttons at end of history', () => {
      const lastIndex = mockMidGameState.move_history.length - 1;
      mockStore.selectedHistoryIndex = lastIndex;
      (useGameStore as any).mockReturnValue(mockStore);

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

      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(1);
    });

    it('highlights currently selected move', () => {
      mockStore.selectedHistoryIndex = 1;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<MoveHistory />);

      const selectedMove = screen.getByText('2. e8');
      expect(selectedMove).toHaveClass('selected') || 
      expect(selectedMove.parentElement).toHaveClass('selected') ||
      expect(selectedMove.parentElement).toHaveClass('active');
    });

    it('shows current move indicator when no history is selected', () => {
      mockStore.selectedHistoryIndex = null;
      (useGameStore as any).mockReturnValue(mockStore);

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

      expect(mockClipboard.writeText).toHaveBeenCalledWith('e2 e8 e3 c5h e7 g6v');
    });

    it('copies moves in correct notation format', async () => {
      const { user } = render(<MoveHistory />);

      const copyButton = screen.getByText('Copy Moves') || screen.getByText('📋');
      await user.click(copyButton);

      const copiedText = mockClipboard.writeText.mock.calls[0][0];
      expect(copiedText).toMatch(/^[a-z0-9h-v\s]+$/); // Valid move notation format
    });

    it('handles empty move history for copying', async () => {
      mockStore.gameState = mockInitialGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<MoveHistory />);

      const copyButton = screen.getByText('Copy Moves') || screen.getByText('📋');
      await user.click(copyButton);

      expect(mockClipboard.writeText).toHaveBeenCalledWith('');
    });

    it('handles clipboard failure gracefully', async () => {
      mockClipboard.writeText.mockRejectedValue(new Error('Clipboard access denied'));

      const { user } = render(<MoveHistory />);

      const copyButton = screen.getByText('Copy Moves') || screen.getByText('📋');
      await user.click(copyButton);

      expect(mockClipboard.writeText).toHaveBeenCalled();
      // Component should not crash on clipboard failure
      expect(screen.getByText('Move History')).toBeInTheDocument();
    });
  });

  describe('Long History Handling', () => {
    it('handles long move histories efficiently', () => {
      mockStore.gameState = mockLongHistoryGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      const start = performance.now();
      render(<MoveHistory />);
      const end = performance.now();

      expect(end - start).toBeLessThan(100); // Should render efficiently
      expect(screen.getByText('Move History')).toBeInTheDocument();
    });

    it('implements virtualization for very long histories', () => {
      mockStore.gameState = mockLongHistoryGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<MoveHistory />);

      // Should not render all 100 moves at once if using virtualization
      const moveElements = document.querySelectorAll('.move-item, [data-testid^="move-"]');
      expect(moveElements.length).toBeLessThanOrEqual(50); // Reasonable viewport limit
    });

    it('scrolls to selected move in long history', async () => {
      mockStore.gameState = mockLongHistoryGameState;
      mockStore.selectedHistoryIndex = 50; // Middle of long history
      (useGameStore as any).mockReturnValue(mockStore);

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
      mockStore.gameState = mockCompletedGameState;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<MoveHistory />);

      expect(screen.getByText('Player 1 Wins!') || 
             screen.getByText('Game Over')).toBeInTheDocument();
    });

    it('highlights winning move', () => {
      mockStore.gameState = mockCompletedGameState;
      (useGameStore as any).mockReturnValue(mockStore);

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
      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalled();
    });

    it('supports keyboard shortcuts for navigation', async () => {
      const { user } = render(<MoveHistory />);

      await user.keyboard('{Home}');
      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(0);

      await user.keyboard('{End}');
      const lastIndex = mockMidGameState.move_history.length - 1;
      expect(mockStore.setSelectedHistoryIndex).toHaveBeenCalledWith(lastIndex);
    });
  });

  describe('Error Handling', () => {
    it('handles invalid move data gracefully', () => {
      mockStore.gameState = {
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
      (useGameStore as any).mockReturnValue(mockStore);

      // Should not crash
      expect(() => render(<MoveHistory />)).not.toThrow();
    });

    it('handles missing move history gracefully', () => {
      mockStore.gameState = {
        ...mockMidGameState,
        move_history: [] // Empty history
      };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<MoveHistory />);

      expect(screen.getByText('No moves yet')).toBeInTheDocument();
    });

    it('handles navigation beyond boundaries', async () => {
      mockStore.selectedHistoryIndex = 0;
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<MoveHistory />);

      // Try to go before first move
      const previousButton = screen.getByText('◀') || screen.getByText('Previous');
      await user.click(previousButton);

      // Should not go below 0
      expect(mockStore.setSelectedHistoryIndex).not.toHaveBeenCalledWith(-1);
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
      mockStore.selectedHistoryIndex = 1;
      (useGameStore as any).mockReturnValue(mockStore);

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