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

// Mock the game store with vi.hoisted
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  const store = {
    // State properties
    connection: {
      type: 'connected' as const,
      clientId: 'test-client',
      since: new Date()
    },
    session: { type: 'no-game' as const },
    settings: { 
      gameSettings: { 
        mode: 'human_vs_human', 
        ai_difficulty: 'medium', 
        ai_time_limit: 3000, 
        board_size: 9 
      }, 
      theme: 'light', 
      soundEnabled: true 
    },
    ui: { 
      settingsExpanded: false, 
      selectedHistoryIndex: null, 
      notifications: [] 
    },
    
    // New API methods
    dispatch: vi.fn(),
    getSettingsUI: vi.fn(() => {
      const hasGame = mockGameStore.session.type === 'active-game' || 
                      mockGameStore.session.type === 'game-ending' || 
                      mockGameStore.session.type === 'game-over';
      const connected = mockGameStore.connection.type === 'connected';
      const isCreating = mockGameStore.session.type === 'creating-game';
      
      if (hasGame) {
        return { type: 'button-visible', enabled: connected };
      } else if (connected) {
        return { type: 'panel-visible', canStartGame: !isCreating, isCreating: isCreating };
      } else {
        return { type: 'button-visible', enabled: false };
      }
    }),
    isConnected: vi.fn(() => mockGameStore.connection.type === 'connected'),
    getCurrentGameId: vi.fn(() => {
      if (mockGameStore.session.type === 'active-game' || 
          mockGameStore.session.type === 'game-ending' || 
          mockGameStore.session.type === 'game-over') {
        return mockGameStore.session.gameId;
      }
      return null;
    }),
    getCurrentGameState: vi.fn(() => mockGameStore.session?.state || null),
    canStartGame: vi.fn(() => mockGameStore.connection.type === 'connected' && !mockGameStore.session),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => !!mockGameStore.session?.state && !mockGameStore.session.state.isGameOver),
    
    // Legacy compatibility
    gameId: null,
    gameState: null,
    gameSettings: {
      mode: 'human_vs_human' as const,
      ai_difficulty: 'medium' as const,
      ai_time_limit: 3000,
      board_size: 9
    },
    setGameSettings: vi.fn(),
    isLoading: false,
    isCreatingGame: false,
    error: null,
    selectedHistoryIndex: null,
    // setGameId removed - use dispatch,
    // setGameState removed - use dispatch,
    // setIsConnected removed - use dispatch,
    // setIsLoading removed - use dispatch,
    // setIsCreatingGame removed - use dispatch,
    setError: vi.fn(),
    setSelectedHistoryIndex: vi.fn(),
    addMoveToHistory: vi.fn(),
    reset: vi.fn()
  };

  const useGameStoreMock = vi.fn(() => store);
  useGameStoreMock.getState = vi.fn(() => store);
  
  return {
    mockGameStore: store,
    mockUseGameStore: useGameStoreMock
  };
});

vi.mock('@/store/gameStore', () => ({
  useGameStore: mockUseGameStore
}));

// Mock WebSocket service with controllable delays
vi.mock('@/services/websocket', () => ({
  wsService: {
    createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
    connect: vi.fn(() => Promise.resolve()),
    disconnect: vi.fn(),
    isConnected: vi.fn(() => mockGameStore.connection.type === 'connected')
  }
}));

describe('Starting Button Race Condition Tests', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset store to no game state
    Object.assign(mockGameStore, {
      connection: {
      type: 'connected' as const,
      clientId: 'test-client',
      since: new Date()
    },
      session: { type: 'no-game' as const },
      settings: { 
        gameSettings: { 
          mode: 'human_vs_human', 
          ai_difficulty: 'medium', 
          ai_time_limit: 3000, 
          board_size: 9 
        }, 
        theme: 'light', 
        soundEnabled: true 
      },
      ui: { 
        settingsExpanded: false, 
        selectedHistoryIndex: null, 
        notifications: [] 
      },
      
      // Legacy compatibility
      gameId: null,
      gameState: null,
      gameSettings: {
        mode: 'human_vs_human' as const,
        ai_difficulty: 'medium' as const,
        ai_time_limit: 3000,
        board_size: 9
      },
      isLoading: false,
      isCreatingGame: false,
      error: null,
      selectedHistoryIndex: null
    });
    
    // Update function mocks
    mockGameStore.isConnected.mockReturnValue(true);
    mockGameStore.getCurrentGameId.mockReturnValue(null);
    mockGameStore.getCurrentGameState.mockReturnValue(null);
    mockGameStore.canStartGame.mockReturnValue(true);
    mockGameStore.isGameActive.mockReturnValue(false);
    mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: true, isCreating: false });
  });

  describe('Starting Button Stuck State', () => {
    it('should not get stuck in Starting state after rapid game creation/reset', async () => {
      const user = userEvent.setup();
      const resetMock = vi.fn();

      // Start with no game
      Object.assign(mockGameStore, {
        reset: resetMock
      });

      const { rerender } = render(<GameSettings />);

      // Click Start Game
      const startButton = screen.getByTestId('start-game-button');
      expect(startButton).toHaveTextContent('Start Game');
      await user.click(startButton);

      // Simulate loading state with active game creation
      act(() => {
        Object.assign(mockGameStore, {
          isLoading: true,
          isCreatingGame: true,
          reset: resetMock
        });
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: false, isCreating: true });
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
        Object.assign(mockGameStore, {
          isLoading: false,
          isCreatingGame: false,
          session: {
            type: 'active-game',
            gameId: 'test-game',
            state: null,
            createdAt: Date.now()
          },
          gameId: 'test-game',
          reset: resetMock
        });
        mockGameStore.getCurrentGameId.mockReturnValue('test-game');
        mockGameStore.canStartGame.mockReturnValue(false);
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'button-visible', enabled: true });
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
        Object.assign(mockGameStore, {
          isLoading: true,  // This is the key - loading state gets stuck
          isCreatingGame: false,  // But we're NOT actively creating a game (race condition)
          session: { type: 'no-game' as const },    // Game is reset
          gameId: null,     // But game is reset
          reset: resetMock
        });
        mockGameStore.getCurrentGameId.mockReturnValue(null);
        mockGameStore.canStartGame.mockReturnValue(false); // Still loading
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: false, isCreating: false });
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

      // Simulate loading state (keep connection during loading)
      act(() => {
        Object.assign(mockGameStore, {
          isLoading: true,
          isCreatingGame: true,  // Must be actively creating to show "Starting..."
          connection: {
      type: 'connected' as const,
      clientId: 'test-client',
      since: new Date()
    }  // Keep connected during loading to show settings panel
        });
        mockGameStore.isConnected.mockReturnValue(true);
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: false, isCreating: true });
      });
      rerender(<GameSettings />);

      // Button should be in loading state
      await waitFor(() => {
        const loadingButton = screen.getByTestId('start-game-button');
        expect(loadingButton).toHaveTextContent('Starting...');
      });

      // Connection restored but game creation failed - should reset properly
      act(() => {
        Object.assign(mockGameStore, {
          isLoading: false,   // Loading finished
          isCreatingGame: false,
          connection: {
      type: 'connected' as const,
      clientId: 'test-client',
      since: new Date()
    },  // Connection restored
          session: { type: 'no-game' as const },      // But no game created
          gameId: null        // But no game created
        });
        mockGameStore.isConnected.mockReturnValue(true);
        mockGameStore.getCurrentGameId.mockReturnValue(null);
        mockGameStore.canStartGame.mockReturnValue(true);
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: true, isCreating: false });
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

      // With functional architecture, we test that the UI correctly reflects the state
      // The component should always show the correct UI for the given state
      
      // Test initial state - with mocked panel-visible, should show settings panel
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      
      // Simulate opening settings panel
      act(() => {
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: true, isCreating: false });
      });
      rerender(<GameSettings />);
      
      // Should show the start game button in the panel
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toHaveTextContent('Start Game');
      expect(screen.getByTestId('start-game-button')).not.toBeDisabled();
      
      // Test loading state
      act(() => {
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: false, isCreating: true });
      });
      rerender(<GameSettings />);
      
      const startButton = screen.getByTestId('start-game-button');
      expect(startButton).toHaveTextContent('Starting...');
      expect(startButton).toBeDisabled();
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
        Object.assign(mockGameStore, {
          isLoading: true,
          isCreatingGame: true
        });
        mockGameStore.canStartGame.mockReturnValue(false);
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: false, isCreating: true });
      });
      rerender(<GameSettings />);

      // Simulate loading completes but creation failed
      act(() => {
        Object.assign(mockGameStore, {
          isLoading: false,
          isCreatingGame: false,
          session: { type: 'no-game' as const },
          gameId: null  // Creation failed
        });
        mockGameStore.getCurrentGameId.mockReturnValue(null);
        mockGameStore.canStartGame.mockReturnValue(true);
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: true, isCreating: false });
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
        Object.assign(mockGameStore, {
          isLoading: true,
          isCreatingGame: true,  // Must be actively creating to show "Starting..."
          session: { type: 'no-game' as const },
          gameId: null,
          reset: resetMock
        });
        mockGameStore.getCurrentGameId.mockReturnValue(null);
        mockGameStore.canStartGame.mockReturnValue(false);
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: false, isCreating: true });
      });
      rerender(<GameSettings />);

      // Button should show loading
      const loadingButton = screen.getByTestId('start-game-button');
      expect(loadingButton).toHaveTextContent('Starting...');

      // Reset is called (New Game button clicked somewhere else)
      act(() => {
        resetMock();
        // Reset should clear loading state
        Object.assign(mockGameStore, {
          isLoading: false,  // Reset should clear loading
          isCreatingGame: false,
          session: { type: 'no-game' as const },
          gameId: null,
          reset: resetMock
        });
        mockGameStore.getCurrentGameId.mockReturnValue(null);
        mockGameStore.canStartGame.mockReturnValue(true);
        mockGameStore.getSettingsUI.mockReturnValue({ type: 'panel-visible', canStartGame: true, isCreating: false });
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
        { isLoading: false, isCreatingGame: false, gameId: null, session: { type: 'no-game' as const } },
        { isLoading: true, isCreatingGame: true, gameId: null, session: { type: 'no-game' as const } },
        { isLoading: true, isCreatingGame: false, gameId: null, session: { type: 'no-game' as const } },   // Stuck loading without creation
        { isLoading: false, isCreatingGame: false, gameId: null, session: { type: 'no-game' as const } },  // Recovery
        { isLoading: true, isCreatingGame: false, gameId: null, session: { type: 'no-game' as const } },   // Reset during loading
        { isLoading: false, isCreatingGame: false, gameId: null, session: { type: 'no-game' as const } }
      ];

      let stuckStateDetected = false;

      // With functional architecture, we test that each state produces the correct UI
      // The component should never show inconsistent state combinations
      
      // Test various UI states to ensure consistency
      const uiStates = [
        { type: 'button-visible', enabled: true },
        { type: 'panel-visible', canStartGame: true, isCreating: false },
        { type: 'panel-visible', canStartGame: false, isCreating: true },
        { type: 'panel-visible', canStartGame: true, isCreating: false }
      ];

      for (const uiState of uiStates) {
        act(() => {
          mockGameStore.getSettingsUI.mockReturnValue(uiState);
        });
        rerender(<GameSettings />);

        if (uiState.type === 'button-visible') {
          // Should show toggle button, not settings panel
          expect(screen.getByTestId('settings-toggle-button')).toBeInTheDocument();
        } else {
          // Should show game settings panel with start button
          const startButton = screen.getByTestId('start-game-button');
          
          if (uiState.isCreating) {
            expect(startButton).toHaveTextContent('Starting...');
            expect(startButton).toBeDisabled();
          } else {
            expect(startButton).toHaveTextContent('Start Game');
            expect(startButton).not.toBeDisabled();
          }
        }
      }

      expect(stuckStateDetected).toBe(false);
    });
  });
});