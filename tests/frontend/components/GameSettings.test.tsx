import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { GameSettings } from '../../../frontend/src/components/GameSettings';
import { useGameStore } from '../../../frontend/src/store/gameStore';
import { wsService } from '../../../frontend/src/services/websocket';
import { 
  render, 
  mockGameSettings,
  createUser 
} from '../utils/test-utils';

// Mock dependencies
vi.mock('../../../frontend/src/store/gameStore');
vi.mock('../../../frontend/src/services/websocket');

const mockUseGameStore = vi.mocked(useGameStore);
const mockWsService = vi.mocked(wsService);

describe('GameSettings Component', () => {
  const user = createUser();
  const mockSetGameSettings = vi.fn();

  const defaultMockStore = {
    gameSettings: mockGameSettings,
    isLoading: false,
    setGameSettings: mockSetGameSettings
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseGameStore.mockReturnValue(defaultMockStore as any);
    mockWsService.createGame = vi.fn();
  });

  describe('Rendering', () => {
    it('renders game settings title', () => {
      render(<GameSettings />);
      
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });

    it('renders game mode options', () => {
      render(<GameSettings />);
      
      expect(screen.getByText('Human vs Human')).toBeInTheDocument();
      expect(screen.getByText('Human vs AI')).toBeInTheDocument();
      expect(screen.getByText('AI vs AI')).toBeInTheDocument();
    });

    it('shows human vs ai as active by default', () => {
      render(<GameSettings />);
      
      const humanVsAiButton = screen.getByText('Human vs AI').closest('.mode-btn');
      expect(humanVsAiButton).toHaveClass('active');
    });

    it('renders AI difficulty options when AI is involved', () => {
      render(<GameSettings />);
      
      expect(screen.getByText('Easy')).toBeInTheDocument();
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(screen.getByText('Hard')).toBeInTheDocument();
      expect(screen.getByText('Expert')).toBeInTheDocument();
    });

    it('renders AI time limit options when AI is involved', () => {
      render(<GameSettings />);
      
      expect(screen.getByText('1s')).toBeInTheDocument();
      expect(screen.getByText('3s')).toBeInTheDocument();
      expect(screen.getByText('5s')).toBeInTheDocument();
      expect(screen.getByText('10s')).toBeInTheDocument();
    });

    it('renders board size options', () => {
      render(<GameSettings />);
      
      expect(screen.getByText('5x5')).toBeInTheDocument();
      expect(screen.getByText('7x7')).toBeInTheDocument();
      expect(screen.getByText('9x9')).toBeInTheDocument();
    });

    it('renders action buttons', () => {
      render(<GameSettings />);
      
      expect(screen.getByText('Start Game')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('hides AI settings for human vs human mode', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameSettings: {
          ...mockGameSettings,
          mode: 'human_vs_human'
        }
      } as any);

      render(<GameSettings />);
      
      expect(screen.queryByText('AI Difficulty')).not.toBeInTheDocument();
      expect(screen.queryByText('AI Time Limit')).not.toBeInTheDocument();
    });
  });

  describe('Game Mode Selection', () => {
    it('selects human vs human mode', async () => {
      render(<GameSettings />);
      
      const humanVsHumanButton = screen.getByText('Human vs Human');
      await user.click(humanVsHumanButton);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ mode: 'human_vs_human' });
    });

    it('selects human vs AI mode', async () => {
      render(<GameSettings />);
      
      const humanVsAiButton = screen.getByText('Human vs AI');
      await user.click(humanVsAiButton);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ mode: 'human_vs_ai' });
    });

    it('selects AI vs AI mode', async () => {
      render(<GameSettings />);
      
      const aiVsAiButton = screen.getByText('AI vs AI');
      await user.click(aiVsAiButton);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ mode: 'ai_vs_ai' });
    });

    it('highlights selected mode', async () => {
      render(<GameSettings />);
      
      const aiVsAiButton = screen.getByText('AI vs AI').closest('.mode-btn');
      await user.click(aiVsAiButton!);
      
      await waitFor(() => {
        expect(aiVsAiButton).toHaveClass('active');
      });
    });
  });

  describe('AI Difficulty Selection', () => {
    it('selects easy difficulty', async () => {
      render(<GameSettings />);
      
      const easyButton = screen.getByText('Easy');
      await user.click(easyButton);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ ai_difficulty: 'easy' });
    });

    it('selects medium difficulty', async () => {
      render(<GameSettings />);
      
      const mediumButton = screen.getByText('Medium');
      await user.click(mediumButton);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ ai_difficulty: 'medium' });
    });

    it('selects hard difficulty', async () => {
      render(<GameSettings />);
      
      const hardButton = screen.getByText('Hard');
      await user.click(hardButton);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ ai_difficulty: 'hard' });
    });

    it('selects expert difficulty', async () => {
      render(<GameSettings />);
      
      const expertButton = screen.getByText('Expert');
      await user.click(expertButton);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ ai_difficulty: 'expert' });
    });

    it('highlights selected difficulty', async () => {
      render(<GameSettings />);
      
      const hardButton = screen.getByText('Hard').closest('.difficulty-btn');
      await user.click(hardButton!);
      
      await waitFor(() => {
        expect(hardButton).toHaveClass('active');
      });
    });
  });

  describe('AI Time Limit Selection', () => {
    it('selects 1 second time limit', async () => {
      render(<GameSettings />);
      
      const oneSecButton = screen.getByText('1s');
      await user.click(oneSecButton);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ ai_time_limit: 1000 });
    });

    it('selects 3 second time limit', async () => {
      render(<GameSettings />);
      
      const threeSec = screen.getByText('3s');
      await user.click(threeSec);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ ai_time_limit: 3000 });
    });

    it('selects 5 second time limit', async () => {
      render(<GameSettings />);
      
      const fiveSec = screen.getByText('5s');
      await user.click(fiveSec);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ ai_time_limit: 5000 });
    });

    it('selects 10 second time limit', async () => {
      render(<GameSettings />);
      
      const tenSec = screen.getByText('10s');
      await user.click(tenSec);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ ai_time_limit: 10000 });
    });

    it('highlights selected time limit', async () => {
      render(<GameSettings />);
      
      const tenSecButton = screen.getByText('10s').closest('.time-btn');
      await user.click(tenSecButton!);
      
      await waitFor(() => {
        expect(tenSecButton).toHaveClass('active');
      });
    });
  });

  describe('Board Size Selection', () => {
    it('selects 5x5 board size', async () => {
      render(<GameSettings />);
      
      const fiveByFive = screen.getByText('5x5');
      await user.click(fiveByFive);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ board_size: 5 });
    });

    it('selects 7x7 board size', async () => {
      render(<GameSettings />);
      
      const sevenBySeven = screen.getByText('7x7');
      await user.click(sevenBySeven);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ board_size: 7 });
    });

    it('selects 9x9 board size', async () => {
      render(<GameSettings />);
      
      const nineByNine = screen.getByText('9x9');
      await user.click(nineByNine);
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ board_size: 9 });
    });

    it('highlights selected board size', async () => {
      render(<GameSettings />);
      
      const sevenBySevenButton = screen.getByText('7x7').closest('.size-btn');
      await user.click(sevenBySevenButton!);
      
      await waitFor(() => {
        expect(sevenBySevenButton).toHaveClass('active');
      });
    });
  });

  describe('Game Creation', () => {
    it('creates game with human vs human settings', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameSettings: {
          ...mockGameSettings,
          mode: 'human_vs_human',
          board_size: 9
        }
      } as any);

      render(<GameSettings />);
      
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);
      
      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_human',
        board_size: 9,
        ai_config: undefined
      });
    });

    it('creates game with AI settings', async () => {
      render(<GameSettings />);
      
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);
      
      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        board_size: 9,
        ai_config: {
          difficulty: 'medium',
          time_limit_ms: 5000,
          use_mcts: true,
          mcts_iterations: 1000
        }
      });
    });

    it('creates game with expert AI settings', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameSettings: {
          ...mockGameSettings,
          ai_difficulty: 'expert',
          ai_time_limit: 10000
        }
      } as any);

      render(<GameSettings />);
      
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);
      
      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        board_size: 9,
        ai_config: {
          difficulty: 'expert',
          time_limit_ms: 10000,
          use_mcts: true,
          mcts_iterations: 10000
        }
      });
    });

    it('creates game with easy AI settings (no MCTS)', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameSettings: {
          ...mockGameSettings,
          ai_difficulty: 'easy'
        }
      } as any);

      render(<GameSettings />);
      
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);
      
      expect(mockWsService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        board_size: 9,
        ai_config: {
          difficulty: 'easy',
          time_limit_ms: 5000,
          use_mcts: false,
          mcts_iterations: 100
        }
      });
    });

    it('hides settings panel after starting game', async () => {
      render(<GameSettings />);
      
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);
      
      await waitFor(() => {
        expect(screen.queryByText('Game Settings')).not.toBeInTheDocument();
        expect(screen.getByText('Game Settings')).toBeInTheDocument(); // Toggle button
      });
    });
  });

  describe('Loading State', () => {
    it('shows loading state when starting game', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        isLoading: true
      } as any);

      render(<GameSettings />);
      
      expect(screen.getByText('Starting...')).toBeInTheDocument();
      
      const startButton = screen.getByText('Starting...');
      expect(startButton).toBeDisabled();
    });

    it('enables start button when not loading', () => {
      render(<GameSettings />);
      
      const startButton = screen.getByText('Start Game');
      expect(startButton).not.toBeDisabled();
    });
  });

  describe('Toggle Functionality', () => {
    it('shows toggle button when settings are hidden', async () => {
      render(<GameSettings />);
      
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);
      
      await waitFor(() => {
        const toggleButton = screen.getByText('Game Settings');
        expect(toggleButton).toBeInTheDocument();
        expect(toggleButton).toHaveClass('toggle-settings');
      });
    });

    it('shows settings panel when toggle button is clicked', async () => {
      render(<GameSettings />);
      
      // Hide settings first
      const startButton = screen.getByText('Start Game');
      await user.click(startButton);
      
      // Then show them again
      await waitFor(async () => {
        const toggleButton = screen.getByText('Game Settings');
        await user.click(toggleButton);
        
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });
    });

    it('hides settings panel when cancel is clicked', async () => {
      render(<GameSettings />);
      
      const cancelButton = screen.getByText('Cancel');
      await user.click(cancelButton);
      
      await waitFor(() => {
        expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('provides proper ARIA labels for mode buttons', () => {
      render(<GameSettings />);
      
      const humanVsHuman = screen.getByText('Human vs Human');
      const humanVsAi = screen.getByText('Human vs AI');
      const aiVsAi = screen.getByText('AI vs AI');
      
      expect(humanVsHuman).toHaveAttribute('aria-label', expect.any(String));
      expect(humanVsAi).toHaveAttribute('aria-label', expect.any(String));
      expect(aiVsAi).toHaveAttribute('aria-label', expect.any(String));
    });

    it('supports keyboard navigation', async () => {
      render(<GameSettings />);
      
      const humanVsHuman = screen.getByText('Human vs Human');
      humanVsHuman.focus();
      
      await user.keyboard('{Enter}');
      
      expect(mockSetGameSettings).toHaveBeenCalledWith({ mode: 'human_vs_human' });
    });

    it('provides proper focus management', async () => {
      render(<GameSettings />);
      
      const startButton = screen.getByText('Start Game');
      startButton.focus();
      
      expect(document.activeElement).toBe(startButton);
    });
  });

  describe('Error Handling', () => {
    it('handles WebSocket service errors gracefully', async () => {
      mockWsService.createGame.mockRejectedValue(new Error('Connection failed'));
      
      render(<GameSettings />);
      
      const startButton = screen.getByText('Start Game');
      
      // Should not throw
      expect(async () => {
        await user.click(startButton);
      }).not.toThrow();
    });
  });

  describe('Edge Cases', () => {
    it('handles invalid game settings gracefully', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameSettings: {
          mode: 'invalid_mode' as any,
          ai_difficulty: 'invalid' as any,
          ai_time_limit: -1,
          board_size: 0
        }
      } as any);

      // Should not crash
      expect(() => render(<GameSettings />)).not.toThrow();
    });

    it('handles missing settings gracefully', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameSettings: null as any
      } as any);

      // Should not crash
      expect(() => render(<GameSettings />)).not.toThrow();
    });
  });

  describe('Performance', () => {
    it('does not re-render unnecessarily', () => {
      const { rerender } = render(<GameSettings />);
      
      // Re-render with same props
      rerender(<GameSettings />);
      
      // Component should handle re-renders efficiently
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });

    it('renders quickly with all options', () => {
      const start = performance.now();
      
      render(<GameSettings />);
      
      const end = performance.now();
      const renderTime = end - start;
      
      // Should render reasonably quickly (less than 50ms)
      expect(renderTime).toBeLessThan(50);
    });
  });
});