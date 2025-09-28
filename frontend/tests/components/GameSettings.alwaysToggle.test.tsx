/**
 * GameSettings component tests for E2E-compatible behavior.
 *
 * These tests verify the behavior that ensures settings are always accessible:
 * - Panel shows when no game exists and connected (immediate access)
 * - Toggle button shows when game exists or disconnected (consistent access)
 * - Settings are never completely inaccessible (E2E requirement)
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

describe('GameSettings - E2E Compatible Behavior', () => {
  const defaultMockStore = {
    gameSettings: {
      mode: 'human_vs_human' as const,
      ai_difficulty: 'medium' as const,
      ai_time_limit: 3000,
      board_size: 9
    },
    setGameSettings: vi.fn(),
    isLoading: false,
    isCreatingGame: false,
    isConnected: true,
    gameId: null,
    setIsCreatingGame: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseGameStore.mockReturnValue(defaultMockStore);
  });

  describe('Initial render behavior', () => {
    it('should show settings panel when no game exists and connected', () => {
      render(<GameSettings />);

      // Should show the settings panel for immediate access
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByText('Game Mode')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Should NOT show the toggle button when panel is visible
      expect(screen.queryByText('⚙️ Game Settings')).not.toBeInTheDocument();
    });

    it('should show toggle button when no game exists but disconnected', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        isConnected: false
      });

      render(<GameSettings />);

      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');
      expect(toggleButton).toHaveAttribute('data-testid', 'settings-toggle-button');

      // Should NOT show the settings panel when disconnected
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
      expect(screen.queryByTestId('start-game-button')).not.toBeInTheDocument();
    });

    it('should show toggle button when game exists', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: 'test-game-123'
      });

      render(<GameSettings />);

      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();
      expect(toggleButton).not.toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Game Settings');

      // Should NOT show the settings panel when game exists
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
      expect(screen.queryByTestId('start-game-button')).not.toBeInTheDocument();
    });
  });

  describe('Toggle button interaction', () => {
    it('should expand to full settings panel when toggle button is clicked (game exists)', async () => {
      // Set up scenario where toggle button is shown (game exists)
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: 'test-game-123'
      });

      render(<GameSettings />);

      // Initially should show only toggle button when game exists
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();

      // Click the toggle button
      fireEvent.click(toggleButton);

      // Should now show the full settings panel
      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });

      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-ai')).toBeInTheDocument();
      expect(screen.getByTestId('mode-ai-vs-ai')).toBeInTheDocument();
    });

    it('should show cancel button when expanding from game-exists state', async () => {
      // Set up scenario where toggle button is shown (game exists)
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: 'test-game-123'
      });

      render(<GameSettings />);

      // Click to expand
      fireEvent.click(screen.getByText('⚙️ Game Settings'));

      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });

      // Should show cancel button when game exists
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });
  });

  describe('Different game states', () => {
    it('should still show toggle button when a game exists', () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: 'test-game-123'
      });

      render(<GameSettings />);

      // Should show toggle button even when game exists
      expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
    });

    it('should show cancel button when expanding with existing game', async () => {
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        gameId: 'test-game-123'
      });

      render(<GameSettings />);

      // Click to expand
      fireEvent.click(screen.getByText('⚙️ Game Settings'));

      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });

      // Should show cancel button when game exists
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });
  });

  describe('E2E compatibility scenarios', () => {
    it('should match E2E test expectations for fresh page load', () => {
      // Simulate fresh page load - no game, connected
      render(<GameSettings />);

      // E2E tests expect immediate access to settings - panel should be visible
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });

    it('should match E2E test expectations for browser navigation scenario', () => {
      // Simulate after browser back navigation - should be same as fresh load
      render(<GameSettings />);

      // E2E tests expect immediate access after navigation
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
    });

    it('should provide consistent test selectors for E2E tests', () => {
      render(<GameSettings />);

      // E2E tests rely on these selectors being immediately present when no game exists
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-human')).toBeInTheDocument();
      expect(screen.getByTestId('mode-human-vs-ai')).toBeInTheDocument();
      expect(screen.getByTestId('mode-ai-vs-ai')).toBeInTheDocument();
    });
  });

  describe('Connection state transitions', () => {
    it('should transition from panel to toggle button during disconnection', () => {
      const { rerender } = render(<GameSettings />);

      // Initially connected with no game - should show settings panel
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Simulate disconnection
      mockUseGameStore.mockReturnValue({
        ...defaultMockStore,
        isConnected: false
      });

      rerender(<GameSettings />);

      // Should now show disabled toggle button instead of panel
      const toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeDisabled();
      expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');

      // Should not show settings panel during disconnection
      expect(screen.queryByText('Game Mode')).not.toBeInTheDocument();
    });
  });

  describe('Game creation flow', () => {
    it('should start with settings panel before game creation', async () => {
      const { wsService } = await import('../../src/services/websocket');
      const mockCreateGame = vi.fn();
      wsService.createGame = mockCreateGame;

      render(<GameSettings />);

      // Should start with settings panel visible (no game, connected)
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Click start game directly (no expansion needed)
      fireEvent.click(screen.getByTestId('start-game-button'));

      expect(mockCreateGame).toHaveBeenCalledWith({
        mode: 'human_vs_human',
        ai_config: undefined,
        board_size: 9
      });
    });
  });
});