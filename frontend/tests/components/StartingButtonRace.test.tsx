/**
 * Starting Button Race Condition Tests
 *
 * Frontend tests that reproduce the "Starting..." button stuck state
 * that was found in E2E tests. These tests isolate the component behavior.
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

// Mock WebSocket service with controllable delays
vi.mock('@/services/websocket', () => ({
  wsService: {
    createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
    connect: vi.fn(() => Promise.resolve()),
    disconnect: vi.fn(),
    isConnected: vi.fn(() => true)
  }
}));

describe('Starting Button Race Condition Tests', () => {
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
    gameId: null,
    reset: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseGameStore.mockReturnValue(baseMockStore);
  });

  describe('Starting Button Stuck State', () => {
    it('should not get stuck in Starting state after rapid game creation/reset', async () => {
      const user = userEvent.setup();
      const resetMock = vi.fn();

      // Start with no game
      mockUseGameStore.mockReturnValue({
        ...baseMockStore,
        reset: resetMock
      });

      const { rerender } = render(<GameSettings />);

      // Click Start Game
      const startButton = screen.getByTestId('start-game-button');
      expect(startButton).toHaveTextContent('Start Game');
      await user.click(startButton);

      // Simulate loading state
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isLoading: true,
          reset: resetMock
        });
      });
      rerender(<GameSettings />);

      // Button should show "Starting..."
      await waitFor(() => {
        const loadingButton = screen.getByTestId('start-game-button');
        expect(loadingButton).toHaveTextContent('Starting...');
        expect(loadingButton).toBeDisabled();
      });

      // Simulate game created
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isLoading: false,
          gameId: 'test-game',
          reset: resetMock
        });
      });
      rerender(<GameSettings />);

      // Should show toggle button now
      await waitFor(() => {
        expect(screen.getByText('⚙️ Game Settings')).toBeInTheDocument();
      });

      // RAPID RESET - this triggers the race condition
      // Simulate user clicking "New Game" which calls reset()
      act(() => {
        resetMock(); // This is what New Game button does

        // Immediate state change - game is gone but loading might still be true
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isLoading: true,  // This is the key - loading state gets stuck
          gameId: null,     // But game is reset
          reset: resetMock
        });
      });
      rerender(<GameSettings />);

      // The bug: button shows "Starting..." and is disabled even though gameId is null
      const buttonAfterReset = screen.getByTestId('start-game-button');

      // This should NOT happen - button should be "Start Game" and enabled
      const buttonText = buttonAfterReset.textContent;
      const isDisabled = buttonAfterReset.hasAttribute('disabled');

      if (buttonText === 'Starting...' && isDisabled) {
        throw new Error(`Race condition reproduced: Button stuck in Starting state after reset`);
      }

      // Correct behavior: button should recover
      expect(buttonAfterReset).toHaveTextContent('Start Game');
      expect(buttonAfterReset).not.toBeDisabled();
    });

    it('should handle WebSocket disconnection during game creation without getting stuck', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<GameSettings />);

      // Click Start Game
      const startButton = screen.getByTestId('start-game-button');
      await user.click(startButton);

      // Simulate loading with WebSocket issue
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isLoading: true,
          isConnected: false  // Connection lost during creation
        });
      });
      rerender(<GameSettings />);

      // Button should be in loading state
      await waitFor(() => {
        const loadingButton = screen.getByTestId('start-game-button');
        expect(loadingButton).toHaveTextContent('Starting...');
      });

      // Connection restored but game creation failed - should reset properly
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isLoading: false,   // Loading finished
          isConnected: true,  // Connection restored
          gameId: null        // But no game created
        });
      });
      rerender(<GameSettings />);

      // Button should NOT be stuck in Starting state
      await waitFor(() => {
        const buttonAfterFailure = screen.getByTestId('start-game-button');
        expect(buttonAfterFailure).toHaveTextContent('Start Game');
        expect(buttonAfterFailure).not.toBeDisabled();
      });
    });

    it('should handle rapid state transitions without button getting stuck', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<GameSettings />);

      // Simulate the exact sequence that causes the race condition
      const stateSequence = [
        { ...baseMockStore, isLoading: false, gameId: null },     // Initial
        { ...baseMockStore, isLoading: true, gameId: null },      // Start game
        { ...baseMockStore, isLoading: false, gameId: 'game-1' }, // Game created
        { ...baseMockStore, isLoading: true, gameId: null },      // New Game clicked (RACE CONDITION)
        { ...baseMockStore, isLoading: false, gameId: null }      // Should recover
      ];

      for (const [index, state] of stateSequence.entries()) {
        act(() => {
          mockUseGameStore.mockReturnValue(state);
        });
        rerender(<GameSettings />);

        if (index === 3) {
          // This is the problematic state - loading=true but gameId=null
          // The button should NOT get stuck here
          const buttonDuringRace = screen.getByTestId('start-game-button');
          const buttonText = buttonDuringRace.textContent;
          const isDisabled = buttonDuringRace.hasAttribute('disabled');

          // Verify the race condition state
          expect(buttonText).toBe('Starting...');
          expect(isDisabled).toBe(true);
        }

        if (index === 4) {
          // Final state - button should recover
          await waitFor(() => {
            const finalButton = screen.getByTestId('start-game-button');
            expect(finalButton).toHaveTextContent('Start Game');
            expect(finalButton).not.toBeDisabled();
          });
        }

        // Small delay to simulate real timing
        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 10));
        });
      }
    });

    it('should handle failed game creation without stuck state', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<GameSettings />);

      // This test doesn't need to mock the WebSocket directly
      // as we're testing store behavior

      const startButton = screen.getByTestId('start-game-button');
      await user.click(startButton);

      // Simulate loading state
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isLoading: true
        });
      });
      rerender(<GameSettings />);

      // Simulate loading completes but creation failed
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isLoading: false,
          gameId: null  // Creation failed
        });
      });
      rerender(<GameSettings />);

      // Button should NOT be stuck
      await waitFor(() => {
        const buttonAfterFailure = screen.getByTestId('start-game-button');
        expect(buttonAfterFailure).toHaveTextContent('Start Game');
        expect(buttonAfterFailure).not.toBeDisabled();
      });
    });

    it('should properly handle store reset during loading state', async () => {
      const resetMock = vi.fn();
      const { rerender } = render(<GameSettings />);

      // Start in loading state (button clicked, creation in progress)
      act(() => {
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isLoading: true,
          gameId: null,
          reset: resetMock
        });
      });
      rerender(<GameSettings />);

      // Button should show loading
      const loadingButton = screen.getByTestId('start-game-button');
      expect(loadingButton).toHaveTextContent('Starting...');

      // Reset is called (New Game button clicked somewhere else)
      act(() => {
        resetMock();
        // Reset should clear loading state
        mockUseGameStore.mockReturnValue({
          ...baseMockStore,
          isLoading: false,  // Reset should clear loading
          gameId: null,
          reset: resetMock
        });
      });
      rerender(<GameSettings />);

      // Button should recover from loading state
      await waitFor(() => {
        const resetButton = screen.getByTestId('start-game-button');
        expect(resetButton).toHaveTextContent('Start Game');
        expect(resetButton).not.toBeDisabled();
      });
    });
  });

  describe('Timing-Dependent Race Conditions', () => {
    it('should handle rapid store updates without intermediate stuck states', async () => {
      const { rerender } = render(<GameSettings />);

      // Rapid fire state changes (simulates real race condition timing)
      const rapidStates = [
        { ...baseMockStore, isLoading: false, gameId: null },
        { ...baseMockStore, isLoading: true, gameId: null },
        { ...baseMockStore, isLoading: true, gameId: 'temp-1' },
        { ...baseMockStore, isLoading: false, gameId: 'temp-1' },
        { ...baseMockStore, isLoading: true, gameId: null },    // Reset during loading
        { ...baseMockStore, isLoading: false, gameId: null }
      ];

      let stuckStateDetected = false;

      for (const state of rapidStates) {
        act(() => {
          mockUseGameStore.mockReturnValue(state);
        });
        rerender(<GameSettings />);

        // Check if button is in valid state
        const button = screen.getByTestId('start-game-button');
        const buttonText = button.textContent;
        const isDisabled = button.hasAttribute('disabled');

        // Valid states:
        // - "Start Game" + enabled (normal state)
        // - "Starting..." + disabled (loading state)
        // Invalid states:
        // - "Starting..." + enabled (inconsistent)
        // - "Start Game" + disabled (stuck)

        const isValidState =
          (buttonText === 'Start Game' && !isDisabled) ||
          (buttonText === 'Starting...' && isDisabled);

        if (!isValidState) {
          stuckStateDetected = true;
          console.error(`Invalid button state: text="${buttonText}", disabled=${isDisabled}`);
        }

        // Minimal delay to simulate real timing
        await act(async () => {
          await new Promise(resolve => setTimeout(resolve, 1));
        });
      }

      expect(stuckStateDetected).toBe(false);
    });
  });
});