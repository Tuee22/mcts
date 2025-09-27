/**
 * GameSettings Race Condition Tests
 *
 * Tests rapid state changes that cause UI race conditions in the GameSettings component.
 * These tests specifically target the Settings button visibility issues that cause E2E failures.
 */

import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { GameSettings } from '@/components/GameSettings';

// Mock the game store with controllable state
const mockUseGameStore = vi.fn();
vi.mock('@/store/gameStore', () => ({
  useGameStore: () => mockUseGameStore()
}));

// Mock WebSocket service
vi.mock('@/services/websocket', () => ({
  wsService: {
    createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
    connect: vi.fn(() => Promise.resolve()),
    disconnect: vi.fn(),
    isConnected: vi.fn(() => true)
  }
}));

describe('GameSettings Race Condition Tests', () => {
  const baseMockStore = {
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
    mockUseGameStore.mockReturnValue(baseMockStore);
  });

  describe('Rapid Connection State Changes', () => {
    it('should handle rapid disconnect-reconnect cycles', async () => {
      const { rerender } = render(<GameSettings />);

      // Initially connected - should show settings panel
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Rapid disconnect
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isConnected: false
        });
      });
      rerender(<GameSettings />);

      // Should show disabled toggle button
      await waitFor(() => {
        const toggleButton = screen.getByText('⚙️ Game Settings');
        expect(toggleButton).toBeDisabled();
        expect(toggleButton).toHaveAttribute('title', 'Connect to server to access settings');
      });

      // Rapid reconnect
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isConnected: true
        });
      });
      rerender(<GameSettings />);

      // Should restore settings panel
      await waitFor(() => {
        expect(screen.getByText('Game Settings')).toBeInTheDocument();
        expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      });
    });

    it('should handle multiple rapid disconnections during game creation', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<GameSettings />);

      // Start game creation
      const startButton = screen.getByTestId('start-game-button');
      await user.click(startButton);

      // Rapid state changes during game creation
      const stateSequence = [
        { ...baseMockStore, isLoading: true, isConnected: false },
        { ...baseMockStore, isLoading: true, isConnected: true },
        { ...baseMockStore, isLoading: false, isConnected: false, gameId: 'test-game' },
        { ...baseMockStore, isLoading: false, isConnected: true, gameId: 'test-game' }
      ];

      for (const state of stateSequence) {
        act(() => {
          mockUseGameStore.mockReturnValue(state);
        });
        rerender(<GameSettings />);

        // Small delay to simulate real timing
        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 10));
        });
      }

      // Final state should show toggle button (game exists)
      await waitFor(() => {
        const toggleButton = screen.getByText('⚙️ Game Settings');
        expect(toggleButton).toBeInTheDocument();
        expect(toggleButton).not.toBeDisabled();
      });
    });
  });

  describe('Rapid Game State Transitions', () => {
    it('should handle rapid game creation and deletion cycles', async () => {
      const { rerender } = render(<GameSettings />);

      // Simulate rapid game state changes
      const gameStates = [
        { ...baseMockStore, gameId: null },           // No game
        { ...baseMockStore, gameId: 'game-1' },       // Game created
        { ...baseMockStore, gameId: null },           // Game deleted
        { ...baseMockStore, gameId: 'game-2' },       // New game created
        { ...baseMockStore, gameId: null }            // Game deleted again
      ];

      for (const state of gameStates) {
        act(() => {
          mockUseGameStore.mockReturnValue(state);
        });
        rerender(<GameSettings />);

        // Verify expected UI state
        if (state.gameId) {
          await waitFor(() => {
            expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
          });
        } else {
          await waitFor(() => {
            expect(screen.getByText('Game Settings')).toBeInTheDocument();
            expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
          });
        }

        // Small delay to simulate real timing
        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 5));
        });
      }
    });

    it('should maintain Settings button accessibility during rapid transitions', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<GameSettings />);

      // Start with game active (toggle button visible)
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          gameId: 'test-game'
        });
      });
      rerender(<GameSettings />);

      let toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();

      // Rapid transition: game deleted, immediately recreated
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          gameId: null  // Game deleted
        });
      });
      rerender(<GameSettings />);

      // Brief moment where settings panel should be visible
      await waitFor(() => {
        expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      });

      // Immediate game recreation
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          gameId: 'new-game'  // Game recreated
        });
      });
      rerender(<GameSettings />);

      // Should return to toggle button
      await waitFor(() => {
        toggleButton = screen.getByText('⚙️ Game Settings');
        expect(toggleButton).toBeInTheDocument();
      });

      // Toggle button should still be functional
      await user.click(toggleButton);
      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });
    });
  });

  describe('Combined Race Conditions', () => {
    it('should handle simultaneous connection and game state changes', async () => {
      const { rerender } = render(<GameSettings />);

      // Simulate complex race condition: disconnection + game creation + reconnection
      const complexStateSequence = [
        { ...baseMockStore, isConnected: true, gameId: null, isLoading: false },
        { ...baseMockStore, isConnected: false, gameId: null, isLoading: true },  // Disconnect during loading
        { ...baseMockStore, isConnected: false, gameId: 'game-1', isLoading: false }, // Game created while disconnected
        { ...baseMockStore, isConnected: true, gameId: 'game-1', isLoading: false },  // Reconnect with game
        { ...baseMockStore, isConnected: true, gameId: null, isLoading: false }      // Game ends
      ];

      for (const [index, state] of complexStateSequence.entries()) {
        act(() => {
          mockUseGameStore.mockReturnValue(state);
        });
        rerender(<GameSettings />);

        // Verify UI consistency at each step
        if (!state.isConnected) {
          await waitFor(() => {
            const toggleButton = screen.getByText('⚙️ Game Settings');
            expect(toggleButton).toBeDisabled();
          });
        } else if (state.gameId) {
          await waitFor(() => {
            const toggleButton = screen.getByText('⚙️ Game Settings');
            expect(toggleButton).not.toBeDisabled();
          });
        } else {
          await waitFor(() => {
            expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
          });
        }

        // Simulate realistic timing between state changes
        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, index * 5));
        });
      }
    });

    it('should prevent Settings button from disappearing during user interaction', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<GameSettings />);

      // Start with game active
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          gameId: 'test-game'
        });
      });
      rerender(<GameSettings />);

      // User clicks to expand settings
      const toggleButton = screen.getByText('⚙️ Game Settings');
      await user.click(toggleButton);

      // Verify panel is expanded
      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });

      // Simulate race condition: game state changes while panel is open
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          gameId: null  // Game suddenly ends
        });
      });
      rerender(<GameSettings />);

      // Settings panel should remain visible (user still interacting)
      expect(screen.getByText('Game Mode')).toBeInTheDocument();

      // Check if cancel button exists (only when expanded from toggle)
      const cancelButton = screen.queryByText('Cancel');
      if (cancelButton) {
        await user.click(cancelButton);
      }

      // Now should show the appropriate state (no game = full panel)
      await waitFor(() => {
        expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      });
    });
  });

  describe('Loading State Race Conditions', () => {
    it('should handle loading state changes during rapid transitions', async () => {
      const { rerender } = render(<GameSettings />);

      // Rapid loading state changes
      const loadingStates = [
        { ...baseMockStore, isLoading: false },
        { ...baseMockStore, isLoading: true },
        { ...baseMockStore, isLoading: false, gameId: 'game-1' },
        { ...baseMockStore, isLoading: true, gameId: 'game-1' },
        { ...baseMockStore, isLoading: false, gameId: null }
      ];

      for (const state of loadingStates) {
        act(() => {
          mockUseGameStore.mockReturnValue(state);
        });
        rerender(<GameSettings />);

        // Verify loading states don't break UI
        if (state.isLoading && !state.gameId) {
          const startButton = screen.getByTestId('start-game-button');
          expect(startButton).toBeDisabled();
          expect(startButton).toHaveTextContent('Starting...');
        }

        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }
    });
  });
});