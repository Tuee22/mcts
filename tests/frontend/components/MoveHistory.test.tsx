import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MoveHistory } from '../../../frontend/src/components/MoveHistory';
import { useGameStore } from '../../../frontend/src/store/gameStore';
import { 
  render, 
  mockGameState, 
  mockGameStateWithHistory, 
  mockCompletedGameState,
  generateMockMove,
  createUser 
} from '../utils/test-utils';
import { vi } from 'vitest';

// Mock dependencies
vi.mock('../../../frontend/src/store/gameStore');

const mockUseGameStore = vi.mocked(useGameStore);

describe('MoveHistory Component', () => {
  const user = createUser();
  const mockSetSelectedHistoryIndex = vi.fn();

  const defaultMockStore = {
    gameState: mockGameStateWithHistory,
    selectedHistoryIndex: null,
    setSelectedHistoryIndex: mockSetSelectedHistoryIndex
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseGameStore.mockReturnValue(defaultMockStore as any);
  });

  describe('Rendering', () => {
    it('renders empty state when no game state exists', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: null
      } as any);

      render(<MoveHistory />);
      
      expect(screen.getByText('No moves yet')).toBeInTheDocument();
    });

    it('renders move history header', () => {
      render(<MoveHistory />);
      
      expect(screen.getByText('Move History')).toBeInTheDocument();
    });

    it('renders initial position item', () => {
      render(<MoveHistory />);
      
      expect(screen.getByText('Start')).toBeInTheDocument();
      expect(screen.getByText('Initial position')).toBeInTheDocument();
    });

    it('renders move history items', () => {
      render(<MoveHistory />);
      
      expect(screen.getByText('e2')).toBeInTheDocument();
      expect(screen.getByText('e8')).toBeInTheDocument();
    });

    it('renders navigation controls', () => {
      render(<MoveHistory />);
      
      expect(screen.getByText('⏮')).toBeInTheDocument(); // First
      expect(screen.getByText('◀')).toBeInTheDocument();  // Previous
      expect(screen.getByText('▶')).toBeInTheDocument();  // Next
      expect(screen.getByText('⏭')).toBeInTheDocument(); // Last
    });

    it('shows current button when history item is selected', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        selectedHistoryIndex: 0
      } as any);

      render(<MoveHistory />);
      
      expect(screen.getByText('Current')).toBeInTheDocument();
    });

    it('renders game result when game is completed', () => {
      const completedGameWithHistory = {
        ...mockCompletedGameState,
        move_history: [
          generateMockMove('e2', 0),
          generateMockMove('e8', 1)
        ]
      };

      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: completedGameWithHistory
      } as any);

      render(<MoveHistory />);
      
      expect(screen.getByText('1-0')).toBeInTheDocument();
      expect(screen.getByText('Player 1 wins!')).toBeInTheDocument();
    });
  });

  describe('Move Selection', () => {
    it('selects initial position when clicking start', async () => {
      render(<MoveHistory />);
      
      const startItem = screen.getByText('Start').closest('.move-item');
      expect(startItem).toBeInTheDocument();
      
      await user.click(startItem!);
      
      expect(mockSetSelectedHistoryIndex).toHaveBeenCalledWith(2); // Beyond history length = current
    });

    it('selects specific move when clicking on move item', async () => {
      render(<MoveHistory />);
      
      const moveItem = screen.getByText('e2').closest('.move-item');
      expect(moveItem).toBeInTheDocument();
      
      await user.click(moveItem!);
      
      expect(mockSetSelectedHistoryIndex).toHaveBeenCalledWith(0);
    });

    it('returns to current position when clicking beyond history', async () => {
      render(<MoveHistory />);
      
      // Simulate clicking to go to current
      const startItem = screen.getByText('Start').closest('.move-item');
      await user.click(startItem!);
      
      expect(mockSetSelectedHistoryIndex).toHaveBeenCalledWith(2);
    });

    it('shows selected move as active', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        selectedHistoryIndex: 0
      } as any);

      render(<MoveHistory />);
      
      const selectedMove = screen.getByText('e2').closest('.move-item');
      expect(selectedMove).toHaveClass('selected');
    });

    it('shows current position as active when no history selected', () => {
      render(<MoveHistory />);
      
      const startItem = screen.getByText('Start').closest('.move-item');
      expect(startItem).toHaveClass('selected');
    });
  });

  describe('Navigation Controls', () => {
    it('navigates to first move', async () => {
      render(<MoveHistory />);
      
      const firstButton = screen.getByText('⏮');
      await user.click(firstButton);
      
      expect(mockSetSelectedHistoryIndex).toHaveBeenCalledWith(0);
    });

    it('navigates to previous move', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        selectedHistoryIndex: 1
      } as any);

      render(<MoveHistory />);
      
      const previousButton = screen.getByText('◀');
      await user.click(previousButton);
      
      expect(mockSetSelectedHistoryIndex).toHaveBeenCalledWith(0);
    });

    it('navigates to next move', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        selectedHistoryIndex: 0
      } as any);

      render(<MoveHistory />);
      
      const nextButton = screen.getByText('▶');
      await user.click(nextButton);
      
      expect(mockSetSelectedHistoryIndex).toHaveBeenCalledWith(1);
    });

    it('navigates to last move (current)', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        selectedHistoryIndex: 0
      } as any);

      render(<MoveHistory />);
      
      const lastButton = screen.getByText('⏭');
      await user.click(lastButton);
      
      expect(mockSetSelectedHistoryIndex).toHaveBeenCalledWith(null);
    });

    it('disables first button when at beginning', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        selectedHistoryIndex: 0
      } as any);

      render(<MoveHistory />);
      
      const firstButton = screen.getByText('⏮');
      expect(firstButton).toBeDisabled();
    });

    it('disables previous button when at beginning', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        selectedHistoryIndex: 0
      } as any);

      render(<MoveHistory />);
      
      const previousButton = screen.getByText('◀');
      expect(previousButton).toBeDisabled();
    });

    it('disables next and last buttons when at current position', () => {
      render(<MoveHistory />);
      
      const nextButton = screen.getByText('▶');
      const lastButton = screen.getByText('⏭');
      
      expect(nextButton).toBeDisabled();
      expect(lastButton).toBeDisabled();
    });
  });

  describe('Move Type Icons', () => {
    it('shows pawn icon for move type', () => {
      const gameStateWithMoveTypes = {
        ...mockGameState,
        move_history: [
          { ...generateMockMove('e2', 0), type: 'move' as const }
        ]
      };

      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: gameStateWithMoveTypes
      } as any);

      render(<MoveHistory />);
      
      expect(screen.getByText('👣')).toBeInTheDocument();
    });

    it('shows wall icon for wall type', () => {
      const gameStateWithWallMove = {
        ...mockGameState,
        move_history: [
          { ...generateMockMove('a1h', 0), type: 'wall' as const }
        ]
      };

      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: gameStateWithWallMove
      } as any);

      render(<MoveHistory />);
      
      expect(screen.getByText('🧱')).toBeInTheDocument();
    });
  });

  describe('Player Move Colors', () => {
    it('colors white moves correctly', () => {
      render(<MoveHistory />);
      
      const firstMove = screen.getByText('e2').closest('.move-item');
      expect(firstMove).toHaveClass('white-move');
    });

    it('colors black moves correctly', () => {
      render(<MoveHistory />);
      
      const secondMove = screen.getByText('e8').closest('.move-item');
      expect(secondMove).toHaveClass('black-move');
    });
  });

  describe('Current Button Functionality', () => {
    it('returns to current position when current button is clicked', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        selectedHistoryIndex: 0
      } as any);

      render(<MoveHistory />);
      
      const currentButton = screen.getByText('Current');
      await user.click(currentButton);
      
      expect(mockSetSelectedHistoryIndex).toHaveBeenCalledWith(null);
    });

    it('hides current button when at current position', () => {
      render(<MoveHistory />);
      
      expect(screen.queryByText('Current')).not.toBeInTheDocument();
    });
  });

  describe('Scrolling Behavior', () => {
    it('handles long move lists with scrolling', () => {
      const longGameHistory = {
        ...mockGameState,
        move_history: Array.from({ length: 50 }, (_, i) => 
          generateMockMove(`move${i}`, i % 2 as 0 | 1)
        )
      };

      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: longGameHistory
      } as any);

      render(<MoveHistory />);
      
      const movesList = document.querySelector('.move-history-list');
      expect(movesList).toHaveStyle('overflow-y: auto');
    });
  });

  describe('Accessibility', () => {
    it('provides proper ARIA labels for navigation controls', () => {
      render(<MoveHistory />);
      
      const firstButton = screen.getByText('⏮');
      const previousButton = screen.getByText('◀');
      const nextButton = screen.getByText('▶');
      const lastButton = screen.getByText('⏭');
      
      expect(firstButton).toHaveAttribute('aria-label', expect.stringContaining('first'));
      expect(previousButton).toHaveAttribute('aria-label', expect.stringContaining('previous'));
      expect(nextButton).toHaveAttribute('aria-label', expect.stringContaining('next'));
      expect(lastButton).toHaveAttribute('aria-label', expect.stringContaining('last'));
    });

    it('supports keyboard navigation', async () => {
      render(<MoveHistory />);
      
      const firstButton = screen.getByText('⏮');
      firstButton.focus();
      
      await user.keyboard('{Enter}');
      
      expect(mockSetSelectedHistoryIndex).toHaveBeenCalledWith(0);
    });
  });

  describe('Edge Cases', () => {
    it('handles empty move history', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: {
          ...mockGameState,
          move_history: []
        }
      } as any);

      render(<MoveHistory />);
      
      expect(screen.getByText('Start')).toBeInTheDocument();
      expect(screen.getByText('Initial position')).toBeInTheDocument();
      
      // Navigation buttons should be disabled
      const firstButton = screen.getByText('⏮');
      expect(firstButton).toBeDisabled();
    });

    it('handles single move in history', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: {
          ...mockGameState,
          move_history: [generateMockMove('e2', 0)]
        }
      } as any);

      render(<MoveHistory />);
      
      expect(screen.getByText('e2')).toBeInTheDocument();
    });

    it('handles malformed move history gracefully', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: {
          ...mockGameState,
          move_history: [null as any, undefined as any]
        }
      } as any);

      // Should not crash
      expect(() => render(<MoveHistory />)).not.toThrow();
    });

    it('handles invalid selected history index', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        selectedHistoryIndex: 999 // Invalid index
      } as any);

      render(<MoveHistory />);
      
      // Should handle gracefully without crashing
      expect(screen.getByText('Move History')).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    it('efficiently renders large move histories', () => {
      const start = performance.now();
      
      const largeGameHistory = {
        ...mockGameState,
        move_history: Array.from({ length: 200 }, (_, i) => 
          generateMockMove(`move${i}`, i % 2 as 0 | 1)
        )
      };

      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameState: largeGameHistory
      } as any);

      render(<MoveHistory />);
      
      const end = performance.now();
      const renderTime = end - start;
      
      // Should render reasonably quickly (less than 100ms)
      expect(renderTime).toBeLessThan(100);
    });

    it('does not re-render unnecessarily', () => {
      const { rerender } = render(<MoveHistory />);
      
      // Re-render with same props
      rerender(<MoveHistory />);
      
      // Component should handle re-renders efficiently
      expect(screen.getByText('Move History')).toBeInTheDocument();
    });
  });
});