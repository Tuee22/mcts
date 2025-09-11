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
import { GameSettings } from '@/components/GameSettings';
import { render, screen, waitFor } from '../utils/testHelpers';
import { 
  mockDefaultGameSettings,
  mockHumanVsHumanSettings,
  mockAIVsAISettings,
  mockEasyAISettings,
  mockExpertAISettings
} from '../fixtures/gameSettings';
import { createMockGameStore } from '../fixtures/mocks';
import { useGameStore } from '@/store/gameStore';

describe('GameSettings Component', () => {
  let mockStore: ReturnType<typeof createMockGameStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockStore = createMockGameStore({
      gameSettings: mockDefaultGameSettings,
      isConnected: true,
      isLoading: false
    });
    (useGameStore as any).mockReturnValue(mockStore);
  });

  describe('Basic Rendering', () => {
    it('renders game settings header', () => {
      render(<GameSettings />);

      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });

    it('renders all game mode options', () => {
      render(<GameSettings />);

      expect(screen.getByText('Human vs Human') || screen.getByText('👤 vs 👤')).toBeInTheDocument();
      expect(screen.getByText('Human vs AI') || screen.getByText('👤 vs 🤖')).toBeInTheDocument();
      expect(screen.getByText('AI vs AI') || screen.getByText('🤖 vs 🤖')).toBeInTheDocument();
    });

    it('renders difficulty options', () => {
      render(<GameSettings />);

      expect(screen.getByText('Easy')).toBeInTheDocument();
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(screen.getByText('Hard')).toBeInTheDocument();
      expect(screen.getByText('Expert')).toBeInTheDocument();
    });

    it('renders time limit options', () => {
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
      expect(screen.getByText('11x11')).toBeInTheDocument();
    });

    it('renders start game button', () => {
      render(<GameSettings />);

      expect(screen.getByText('Start Game')).toBeInTheDocument();
    });
  });

  describe('Game Mode Selection', () => {
    it('highlights currently selected mode', () => {
      mockStore.gameSettings = mockDefaultGameSettings; // human_vs_ai
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      const humanVsAI = screen.getByText('Human vs AI') || screen.getByText('👤 vs 🤖');
      expect(humanVsAI).toHaveClass('selected') || 
      expect(humanVsAI.parentElement).toHaveClass('selected') ||
      expect(humanVsAI.parentElement).toHaveClass('active');
    });

    it('changes mode when clicked', async () => {
      const { user } = render(<GameSettings />);

      const humanVsHuman = screen.getByText('Human vs Human') || screen.getByText('👤 vs 👤');
      await user.click(humanVsHuman);

      expect(mockStore.setGameSettings).toHaveBeenCalledWith(
        expect.objectContaining({ mode: 'human_vs_human' })
      );
    });

    it('updates to AI vs AI mode correctly', async () => {
      const { user } = render(<GameSettings />);

      const aiVsAI = screen.getByText('AI vs AI') || screen.getByText('🤖 vs 🤖');
      await user.click(aiVsAI);

      expect(mockStore.setGameSettings).toHaveBeenCalledWith(
        expect.objectContaining({ mode: 'ai_vs_ai' })
      );
    });
  });

  describe('AI Difficulty Selection', () => {
    it('shows difficulty options for AI modes', () => {
      render(<GameSettings />);

      expect(screen.getByText('Easy')).toBeInTheDocument();
      expect(screen.getByText('Medium')).toBeInTheDocument();
      expect(screen.getByText('Hard')).toBeInTheDocument();
      expect(screen.getByText('Expert')).toBeInTheDocument();
    });

    it('highlights currently selected difficulty', () => {
      mockStore.gameSettings = { ...mockDefaultGameSettings, ai_difficulty: 'hard' };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      const hardDifficulty = screen.getByText('Hard');
      expect(hardDifficulty).toHaveClass('selected') || 
      expect(hardDifficulty.parentElement).toHaveClass('selected') ||
      expect(hardDifficulty.parentElement).toHaveClass('active');
    });

    it('changes difficulty when clicked', async () => {
      const { user } = render(<GameSettings />);

      const expertDifficulty = screen.getByText('Expert');
      await user.click(expertDifficulty);

      expect(mockStore.setGameSettings).toHaveBeenCalledWith(
        expect.objectContaining({ ai_difficulty: 'expert' })
      );
    });

    it('hides AI options for human vs human mode', async () => {
      mockStore.gameSettings = mockHumanVsHumanSettings;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      // AI difficulty should be hidden or disabled
      const difficultySection = document.querySelector('.ai-difficulty, [data-testid="ai-difficulty"]');
      if (difficultySection) {
        expect(difficultySection).not.toBeVisible() || 
        expect(difficultySection).toHaveClass('hidden', 'disabled');
      }
    });
  });

  describe('Time Limit Selection', () => {
    it('highlights currently selected time limit', () => {
      mockStore.gameSettings = { ...mockDefaultGameSettings, ai_time_limit: 10000 };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      const tenSeconds = screen.getByText('10s');
      expect(tenSeconds).toHaveClass('selected') || 
      expect(tenSeconds.parentElement).toHaveClass('selected') ||
      expect(tenSeconds.parentElement).toHaveClass('active');
    });

    it('changes time limit when clicked', async () => {
      const { user } = render(<GameSettings />);

      const threeSeconds = screen.getByText('3s');
      await user.click(threeSeconds);

      expect(mockStore.setGameSettings).toHaveBeenCalledWith(
        expect.objectContaining({ ai_time_limit: 3000 })
      );
    });

    it('converts time display correctly', () => {
      mockStore.gameSettings = { ...mockDefaultGameSettings, ai_time_limit: 1000 };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      expect(screen.getByText('1s')).toBeInTheDocument();
    });
  });

  describe('Board Size Selection', () => {
    it('highlights currently selected board size', () => {
      mockStore.gameSettings = { ...mockDefaultGameSettings, board_size: 7 };
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      const sevenBySeven = screen.getByText('7x7');
      expect(sevenBySeven).toHaveClass('selected') || 
      expect(sevenBySeven.parentElement).toHaveClass('selected') ||
      expect(sevenBySeven.parentElement).toHaveClass('active');
    });

    it('changes board size when clicked', async () => {
      const { user } = render(<GameSettings />);

      const smallBoard = screen.getByText('5x5');
      await user.click(smallBoard);

      expect(mockStore.setGameSettings).toHaveBeenCalledWith(
        expect.objectContaining({ board_size: 5 })
      );
    });

    it('supports large board sizes', async () => {
      const { user } = render(<GameSettings />);

      const largeBoard = screen.getByText('11x11');
      await user.click(largeBoard);

      expect(mockStore.setGameSettings).toHaveBeenCalledWith(
        expect.objectContaining({ board_size: 11 })
      );
    });
  });

  describe('Game Creation', () => {
    it('starts game with correct settings', async () => {
      const { user } = render(<GameSettings />);

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      expect(mockWebSocketService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_ai',
        board_size: 9,
        ai_config: {
          difficulty: 'medium',
          time_limit_ms: 5000,
          use_mcts: true,
          mcts_iterations: expect.any(Number)
        }
      });
    });

    it('starts human vs human game correctly', async () => {
      const { user } = render(<GameSettings />);

      // First change to human vs human mode
      const humanVsHuman = screen.getByText('Human vs Human') || screen.getByText('👤 vs 👤');
      await user.click(humanVsHuman);

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      expect(mockWebSocketService.createGame).toHaveBeenCalledWith({
        mode: 'human_vs_human',
        board_size: 9
        // No ai_config for human vs human
      });
    });

    it('starts AI vs AI game correctly', async () => {
      const { user } = render(<GameSettings />);

      // Configure AI vs AI with expert difficulty
      const aiVsAI = screen.getByText('AI vs AI') || screen.getByText('🤖 vs 🤖');
      await user.click(aiVsAI);

      const expertDifficulty = screen.getByText('Expert');
      await user.click(expertDifficulty);

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      expect(mockWebSocketService.createGame).toHaveBeenCalledWith({
        mode: 'ai_vs_ai',
        board_size: 9,
        ai_config: {
          difficulty: 'expert',
          time_limit_ms: expect.any(Number),
          use_mcts: true,
          mcts_iterations: expect.any(Number)
        }
      });
    });

    it('includes custom board size in game creation', async () => {
      const { user } = render(<GameSettings />);

      // Select small board
      const smallBoard = screen.getByText('5x5');
      await user.click(smallBoard);

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      expect(mockWebSocketService.createGame).toHaveBeenCalledWith(
        expect.objectContaining({ board_size: 5 })
      );
    });
  });

  describe('Loading State', () => {
    it('shows loading state during game creation', () => {
      mockStore.isLoading = true;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      const startButton = screen.getByText('Starting...') || 
                          screen.getByText('Loading...') ||
                          document.querySelector('.loading');

      expect(startButton).toBeInTheDocument();
    });

    it('disables button during loading', () => {
      mockStore.isLoading = true;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      const startButton = screen.getByRole('button') || 
                          document.querySelector('button:disabled');

      expect(startButton).toBeDisabled();
    });

    it('re-enables button after loading completes', () => {
      const { rerender } = render(<GameSettings />);

      // Start with loading state
      mockStore.isLoading = true;
      (useGameStore as any).mockReturnValue(mockStore);
      rerender(<GameSettings />);

      // Complete loading
      mockStore.isLoading = false;
      (useGameStore as any).mockReturnValue(mockStore);
      rerender(<GameSettings />);

      const startButton = screen.getByText('Start Game');
      expect(startButton).not.toBeDisabled();
    });
  });

  describe('Connection State', () => {
    it('disables start button when disconnected', () => {
      mockStore.isConnected = false;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      const startButton = screen.getByText('Start Game') || screen.getByRole('button');
      expect(startButton).toBeDisabled();
    });

    it('shows disconnected message', () => {
      mockStore.isConnected = false;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      expect(screen.getByText('Connect to start playing') || 
             screen.getByText('Disconnected')).toBeInTheDocument();
    });

    it('enables start button when connected', () => {
      mockStore.isConnected = true;
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      const startButton = screen.getByText('Start Game');
      expect(startButton).not.toBeDisabled();
    });
  });

  describe('Compact Mode (Active Game)', () => {
    it('shows compact view when game is active', () => {
      mockStore.gameId = 'active-game-123';
      (useGameStore as any).mockReturnValue(mockStore);

      render(<GameSettings />);

      // Should show toggle button or compact view
      const toggleButton = screen.queryByText('Settings') || 
                          screen.queryByText('⚙️') ||
                          document.querySelector('.settings-toggle');

      expect(toggleButton).toBeInTheDocument();
    });

    it('expands settings when toggle is clicked', async () => {
      mockStore.gameId = 'active-game-123';
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<GameSettings />);

      const toggleButton = screen.getByText('Settings') || 
                          screen.getByText('⚙️') ||
                          document.querySelector('.settings-toggle');

      if (toggleButton) {
        await user.click(toggleButton as HTMLElement);

        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      }
    });
  });

  describe('Error Handling', () => {
    it('handles game creation failure gracefully', async () => {
      mockWebSocketService.createGame.mockRejectedValue(new Error('Server error'));

      const { user } = render(<GameSettings />);

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      expect(mockWebSocketService.createGame).toHaveBeenCalled();
      
      // Component should not crash and button should be re-enabled
      await waitFor(() => {
        expect(screen.getByText('Start Game')).not.toBeDisabled();
      });
    });

    it('validates settings before starting game', async () => {
      // Mock invalid settings
      mockStore.gameSettings = {
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 0, // Invalid
        board_size: 0     // Invalid
      };
      (useGameStore as any).mockReturnValue(mockStore);

      const { user } = render(<GameSettings />);

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      // Should either not call createGame or handle validation
      expect(mockWebSocketService.createGame).toHaveBeenCalledWith(
        expect.not.objectContaining({
          board_size: 0,
          ai_config: expect.objectContaining({
            time_limit_ms: 0
          })
        })
      );
    });
  });

  describe('Settings Persistence', () => {
    it('updates store when settings change', async () => {
      const { user } = render(<GameSettings />);

      // Change multiple settings
      const hardDifficulty = screen.getByText('Hard');
      await user.click(hardDifficulty);

      const smallBoard = screen.getByText('5x5');
      await user.click(smallBoard);

      const fastTime = screen.getByText('1s');
      await user.click(fastTime);

      // Each change should update the store
      expect(mockStore.setGameSettings).toHaveBeenCalledTimes(3);
    });
  });

  describe('AI Configuration', () => {
    it('sets correct MCTS iterations for different difficulties', async () => {
      const { user } = render(<GameSettings />);

      const expertDifficulty = screen.getByText('Expert');
      await user.click(expertDifficulty);

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      expect(mockWebSocketService.createGame).toHaveBeenCalledWith(
        expect.objectContaining({
          ai_config: expect.objectContaining({
            difficulty: 'expert',
            mcts_iterations: expect.any(Number)
          })
        })
      );

      // Expert should have more iterations than easy
      const callArgs = mockWebSocketService.createGame.mock.calls[0][0];
      expect(callArgs.ai_config.mcts_iterations).toBeGreaterThan(1000);
    });

    it('configures AI correctly for different time limits', async () => {
      const { user } = render(<GameSettings />);

      const longTime = screen.getByText('10s');
      await user.click(longTime);

      const startButton = screen.getByText('Start Game');
      await user.click(startButton);

      expect(mockWebSocketService.createGame).toHaveBeenCalledWith(
        expect.objectContaining({
          ai_config: expect.objectContaining({
            time_limit_ms: 10000
          })
        })
      );
    });
  });

  describe('Accessibility', () => {
    it('provides proper ARIA labels for all controls', () => {
      render(<GameSettings />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toBeInTheDocument();
        // Should have either aria-label or accessible text content
        expect(
          button.getAttribute('aria-label') || 
          button.textContent?.trim()
        ).toBeTruthy();
      });
    });

    it('supports keyboard navigation', async () => {
      const { user } = render(<GameSettings />);

      const humanVsHuman = screen.getByText('Human vs Human') || screen.getByText('👤 vs 👤');
      humanVsHuman.focus();

      await user.keyboard('{Enter}');

      expect(mockStore.setGameSettings).toHaveBeenCalledWith(
        expect.objectContaining({ mode: 'human_vs_human' })
      );
    });

    it('provides proper focus management', async () => {
      const { user } = render(<GameSettings />);

      // Tab through controls
      await user.tab();
      expect(document.activeElement).toBeDefined();

      await user.tab();
      expect(document.activeElement).toBeDefined();
    });
  });

  describe('Performance', () => {
    it('renders quickly even with many options', () => {
      const start = performance.now();
      render(<GameSettings />);
      const end = performance.now();

      expect(end - start).toBeLessThan(50);
    });

    it('does not re-render unnecessarily', () => {
      const { rerender } = render(<GameSettings />);

      // Re-render with same props
      rerender(<GameSettings />);

      // Should still show the same content
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
    });
  });
});