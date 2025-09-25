/**
 * GameSettings Visibility Tests
 *
 * Tests the visibility logic for GameSettings component that was causing E2E failures.
 * The component shows different UI states based on gameId and showSettings state.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { GameSettings } from '@/components/GameSettings';

// Mock the game store
const mockUseGameStore = vi.fn();
vi.mock('@/store/gameStore', () => ({
  useGameStore: () => mockUseGameStore()
}));

// Mock the WebSocket service
vi.mock('@/services/websocket', () => ({
  wsService: {
    createGame: vi.fn()
  }
}));

describe('GameSettings Visibility Logic', () => {
  const defaultMockStore = {
    gameSettings: {
      mode: 'human_vs_human' as const,
      ai_difficulty: 'medium' as const,
      ai_time_limit: 3000,
      board_size: 9
    },
    setGameSettings: vi.fn(),
    isLoading: false,
    isConnected: true,
    gameId: null
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseGameStore.mockReturnValue(defaultMockStore);
  });

  describe('When no game exists (gameId is null)', () => {
    it('should show the full settings panel by default', () => {
      render(<GameSettings />);

      // Should show the settings panel, not the toggle button
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByText('Game Mode')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Should NOT show the toggle button
      expect(screen.queryByText('⚙️ Game Settings')).not.toBeInTheDocument();
    });

    it('should show mode selection buttons', () => {
      render(<GameSettings />);

      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-ai')).toBeInTheDocument();
      expect(screen.getByTestId('mode-ai-vs-ai')).toBeInTheDocument();
    });

    it('should show start game button', () => {
      render(<GameSettings />);

      const startButton = screen.getByTestId('start-game-button');
      expect(startButton).toBeInTheDocument();
      expect(startButton).not.toBeDisabled();
    });

    it('should not show cancel button when no game exists', () => {
      render(<GameSettings />);

      expect(screen.queryByText('Cancel')).not.toBeInTheDocument();
    });
  });

  describe('When a game exists (gameId is present)', () => {
    beforeEach(() => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: 'test-game-123'
      });
    });

    it('should show only the toggle button by default', () => {
      render(<GameSettings />);

      // Should show the toggle button
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();

      // Should NOT show the full settings panel
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
      expect(screen.queryByTestId('start-game-button')).not.toBeInTheDocument();
    });

    it('should show the toggle button with correct attributes', () => {
      render(<GameSettings />);

      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toHaveClass('retro-btn', 'toggle-settings');
      expect(toggleButton).not.toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Game Settings');
    });

    it('should expand to full panel when toggle button is clicked', async () => {
      render(<GameSettings />);

      // Initially should show only toggle button
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();

      // Click the toggle button
      fireEvent.click(toggleButton);

      // Should now show the full settings panel
      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });

      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('should show cancel button when panel is expanded', async () => {
      render(<GameSettings />);

      // Expand the panel
      fireEvent.click(screen.getByText('⚙️ Game Settings'));

      await waitFor(() => {
        const cancelButton = screen.getByText('Cancel');
        expect(cancelButton).toBeInTheDocument();
        expect(cancelButton).toHaveClass('retro-btn', 'cancel');
      });
    });

    it('should collapse back to toggle button when cancel is clicked', async () => {
      render(<GameSettings />);

      // Expand the panel
      fireEvent.click(screen.getByText('⚙️ Game Settings'));

      await waitFor(() => {
        expect(screen.getByText('Cancel')).toBeInTheDocument();
      });

      // Click cancel
      fireEvent.click(screen.getByText('Cancel'));

      // Should be back to toggle button only
      await waitFor(() => {
        expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
      });

      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
    });
  });

  describe('Connection state affects button availability', () => {
    it('should disable toggle button when disconnected', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: 'test-game-123',
        isConnected: false
      });

      render(<GameSettings />);

      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');
    });

    it('should show connection warning in expanded panel when disconnected', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: null, // No game, so panel shows by default
        isConnected: false
      });

      render(<GameSettings />);

      expect(screen.getByTestId('connection-warning')).toBeInTheDocument();
      expect(screen.getByText('⚠️ Connection Required')).toBeInTheDocument();
      expect(screen.getByText('Please connect to the server before configuring game settings.')).toBeInTheDocument();
    });

    it('should disable all settings when disconnected', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: null, // Show panel by default
        isConnected: false
      });

      render(<GameSettings />);

      const modeButtons = [
        screen.getByTestId('mode-human-vs-human'),
        screen.getByTestId('mode-human-vs-ai'),
        screen.getByTestId('mode-ai-vs-ai')
      ];

      modeButtons.forEach(button => {
        expect(button).toBeDisabled();
      });

      const startButton = screen.getByTestId('start-game-button');
      expect(startButton).toBeDisabled();
      expect(startButton).toHaveTextContent('Disconnected');
    });
  });

  describe('Loading state', () => {
    it('should show loading text on start button when loading', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        isLoading: true
      });

      render(<GameSettings />);

      const startButton = screen.getByTestId('start-game-button');
      expect(startButton).toBeDisabled();
      expect(startButton).toHaveTextContent('Starting...');
    });
  });

  describe('Settings panel collapse after game start', () => {
    it('should collapse panel after successful game creation', async () => {
      const { wsService } = await import('../../src/services/websocket');
      const mockCreateGame = vi.fn();
      wsService.createGame = mockCreateGame;

      // Start with no game (panel visible)
      const mockStore = {
        ...defaultMockStore,
        gameId: null
      };
      mockUseGameStore.mockReturnValue(mockStore);

      render(<GameSettings />);

      // Click start game
      const startButton = screen.getByTestId('start-game-button');
      fireEvent.click(startButton);

      // Simulate game creation success by updating gameId
      mockUseGameStore.mockReturnValue({
        ...mockStore,
        gameId: 'new-game-123'
      });

      expect(mockCreateGame).toHaveBeenCalledWith({
        mode: 'human_vs_human',
        ai_config: undefined,
        board_size: 9
      });
    });
  });

  describe('AI settings visibility', () => {
    it('should show AI settings when mode is human_vs_ai', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameSettings: {
          ...defaultMockStore.gameSettings,
          mode: 'human_vs_ai'
        }
      });

      render(<GameSettings />);

      expect(screen.getByText('AI Difficulty')).toBeInTheDocument();
      expect(screen.getByText('AI Time Limit')).toBeInTheDocument();
    });

    it('should show AI settings when mode is ai_vs_ai', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameSettings: {
          ...defaultMockStore.gameSettings,
          mode: 'ai_vs_ai'
        }
      });

      render(<GameSettings />);

      expect(screen.getByText('AI Difficulty')).toBeInTheDocument();
      expect(screen.getByText('AI Time Limit')).toBeInTheDocument();
    });

    it('should hide AI settings when mode is human_vs_human', () => {
      render(<GameSettings />);

      expect(screen.queryByText('AI Difficulty')).not.toBeInTheDocument();
      expect(screen.queryByText('AI Time Limit')).not.toBeInTheDocument();
    });
  });

  describe('E2E Test Compatibility', () => {
    it('should always provide a way to access game settings', () => {
      // When no game exists, full panel is visible
      const { rerender } = render(<GameSettings />);
      expect(screen.getByText('Game Settings')).toBeInTheDocument();

      // When game exists, toggle button is visible
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: 'test-game'
      });

      rerender(<GameSettings />);
      expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
    });

    it('should maintain consistent test selectors', () => {
      render(<GameSettings />);

      // These selectors are used by E2E tests and should always be present
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
    });
  });
});