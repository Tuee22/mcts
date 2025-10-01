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

// Mock the game store first with vi.hoisted
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  // Create mock store inline to avoid import issues with hoisting
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
    dispatch: vi.fn((action) => {
      // Simulate actual state updates for relevant actions
      if (action.type === 'SETTINGS_TOGGLED') {
        mockGameStore.ui.settingsExpanded = !mockGameStore.ui.settingsExpanded;
      } else if (action.type === 'GAME_CREATED') {
        mockGameStore.isLoading = true;
        mockGameStore.isCreatingGame = true;
      }
    }),
    getSettingsUI: () => {
      // Replicate the actual getSettingsUIState logic
      const hasGame = mockGameStore.session && (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-ending' || mockGameStore.session.type === 'game-over');
      const connected = mockGameStore.connection.type === 'connected';
      
      // If settings are explicitly expanded, show panel
      if (mockGameStore.ui.settingsExpanded) {
        const isCreating = mockGameStore.isLoading && mockGameStore.isCreatingGame;
        const canStart = connected && !hasGame;
        return { type: 'panel-visible', canStartGame: canStart, isCreating };
      }
      
      // Otherwise, determine based on session state
      if (hasGame) {
        return {
          type: 'button-visible',
          enabled: connected
        };
      } else if (connected) {
        return {
          type: 'panel-visible',
          canStartGame: true,
          isCreating: mockGameStore.isLoading && mockGameStore.isCreatingGame
        };
      } else {
        return {
          type: 'button-visible',
          enabled: false
        };
      }
    },
    isConnected: vi.fn(() => mockGameStore.connection.type === 'connected'),
    getCurrentGameId: vi.fn(() => {
      if (mockGameStore.session.type === 'active-game' || 
          mockGameStore.session.type === 'game-ending' || 
          mockGameStore.session.type === 'game-over') {
        return mockGameStore.session.gameId;
      }
      return null;
    }),
    getCurrentGameState: vi.fn(() => null),
    canStartGame: vi.fn(() => {
      const connected = mockGameStore.connection.type === 'connected';
      const hasGame = mockGameStore.session && (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-ending' || mockGameStore.session.type === 'game-over');
      return connected && !hasGame;
    }),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => false),
    getSelectedHistoryIndex: vi.fn(() => null),
    getLatestError: vi.fn(() => null),
    getIsLoading: vi.fn(() => false),
    
    // Legacy compatibility
    gameId: null,
    gameState: null,
    gameSettings: { mode: 'human_vs_human', ai_difficulty: 'medium', ai_time_limit: 3000, board_size: 9 },
    isLoading: false,
    isCreatingGame: false,
    error: null,
    selectedHistoryIndex: null,
    // setGameId removed - use dispatch,
    // setGameState removed - use dispatch,
    setGameSettings: vi.fn(),
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

const mockWsService = vi.hoisted(() => ({
  connect: vi.fn(() => Promise.resolve()),
  disconnect: vi.fn(),
  disconnectFromGame: vi.fn(),
  isConnected: vi.fn(() => mockGameStore.connection.type === 'connected'),
  createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
  makeMove: vi.fn(() => Promise.resolve()),
  getAIMove: vi.fn(() => Promise.resolve()),
  joinGame: vi.fn(),
  requestGameState: vi.fn(() => Promise.resolve()),
  connectToGame: vi.fn(),
}));

vi.mock('@/services/websocket', () => ({
  wsService: mockWsService
}));

describe('GameSettings Race Condition Tests', () => {
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    vi.clearAllMocks();
    user = userEvent.setup();
    
    // Reset the game store state for each test
    mockGameStore.connection = { type: 'connected' as const, clientId: 'test-client', since: new Date() };
    mockGameStore.session = {
      gameId: null,
      gameState: null,
      createdAt: Date.now()
    };
    mockGameStore.ui.settingsExpanded = false;
    mockGameStore.isLoading = false;
    mockGameStore.isCreatingGame = false;
    mockGameStore.error = null;
    
    // Reset mock return values
    mockGameStore.isConnected.mockReturnValue(true);
    mockGameStore.getCurrentGameId.mockReturnValue(null);
    mockGameStore.getCurrentGameState.mockReturnValue(null);
    // Don't override getSettingsUI - let it use the dynamic function
  });

  describe('Rapid Connection State Changes', () => {
    it('should handle rapid disconnect-reconnect cycles', async () => {
      const { rerender } = render(<GameSettings />);

      // Initially connected - should show settings panel
      expect(screen.getByText('Game Settings')).toBeInTheDocument();
      expect(screen.getByTestId('start-game-button')).toBeInTheDocument();

      // Rapid disconnect
      act(() => {
        mockGameStore.connection = { type: 'disconnected' as const };
        mockGameStore.isConnected.mockReturnValue(false);
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
        mockGameStore.connection = { type: 'connected' as const, clientId: 'test-client', since: new Date() };
        mockGameStore.isConnected.mockReturnValue(true);
      });
      rerender(<GameSettings />);

      // Should restore settings panel
      await waitFor(() => {
        expect(screen.getByText('Game Settings')).toBeInTheDocument();
        expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      });
    });

    it('should handle multiple rapid disconnections during game creation', async () => {
      const { rerender } = render(<GameSettings />);

      // Start game creation
      const startButton = screen.getByTestId('start-game-button');
      await user.click(startButton);

      // Rapid state changes during game creation
      const stateSequence = [
        { connected: false, loading: true, gameId: null },
        { connected: true, loading: true, gameId: null },
        { connected: false, loading: false, gameId: 'test-game' },
        { connected: true, loading: false, gameId: 'test-game' }
      ];

      for (const state of stateSequence) {
        act(() => {
          mockGameStore.connection = state.connected 
            ? { type: 'connected' as const, clientId: 'test-client', since: new Date() }
            : { type: 'disconnected' as const };
          mockGameStore.isConnected.mockReturnValue(state.connected);
          mockGameStore.isLoading = state.loading;
          mockGameStore.session = state.gameId ? {
        type: 'active-game' as const,
        gameId: state.gameId,
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      } : { type: 'no-game' as const };
          mockGameStore.getCurrentGameId.mockReturnValue(state.gameId);
          
          if (state.gameId) {
          } else if (state.connected) {
          } else {
          }
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
        { gameId: null },           // No game
        { gameId: 'game-1' },       // Game created
        { gameId: null },           // Game deleted
        { gameId: 'game-2' },       // New game created
        { gameId: null }            // Game deleted again
      ];

      for (const state of gameStates) {
        act(() => {
          mockGameStore.session = state.gameId ? {
        type: 'active-game' as const,
        gameId: state.gameId,
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      } : { type: 'no-game' as const };
          mockGameStore.getCurrentGameId.mockReturnValue(state.gameId);
          
          if (state.gameId) {
          } else {
          }
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
      const { rerender } = render(<GameSettings />);

      // Start with game active (toggle button visible)
      act(() => {
        mockGameStore.session = {
        type: 'active-game' as const,
        gameId: 'test-game',
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      };
        mockGameStore.getCurrentGameId.mockReturnValue('test-game');
      });
      rerender(<GameSettings />);

      let toggleButton = screen.getByText('⚙️ Game Settings');
      expect(toggleButton).toBeInTheDocument();

      // Rapid transition: game deleted, immediately recreated
      act(() => {
        mockGameStore.session = { type: 'no-game' as const };
        mockGameStore.getCurrentGameId.mockReturnValue(null);
      });
      rerender(<GameSettings />);

      // Brief moment where settings panel should be visible
      await waitFor(() => {
        expect(screen.getByTestId('start-game-button')).toBeInTheDocument();
      });

      // Immediate game recreation
      act(() => {
        mockGameStore.session = {
        type: 'active-game' as const,
        gameId: 'new-game',
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      };
        mockGameStore.getCurrentGameId.mockReturnValue('new-game');
      });
      rerender(<GameSettings />);

      // Should return to toggle button
      await waitFor(() => {
        toggleButton = screen.getByText('⚙️ Game Settings');
        expect(toggleButton).toBeInTheDocument();
      });

      // Toggle button should still be functional
      await user.click(toggleButton);
      
      // Force a re-render to see the state change
      rerender(<GameSettings />);
      
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
        { connected: true, gameId: null, loading: false },
        { connected: false, gameId: null, loading: true },  // Disconnect during loading
        { connected: false, gameId: 'game-1', loading: false }, // Game created while disconnected
        { connected: true, gameId: 'game-1', loading: false },  // Reconnect with game
        { connected: true, gameId: null, loading: false }      // Game ends
      ];

      for (const [index, state] of complexStateSequence.entries()) {
        act(() => {
          mockGameStore.connection = state.connected 
            ? { type: 'connected' as const, clientId: 'test-client', since: new Date() }
            : { type: 'disconnected' as const };
          mockGameStore.isConnected.mockReturnValue(state.connected);
          mockGameStore.isLoading = state.loading;
          mockGameStore.session = state.gameId ? {
        type: 'active-game' as const,
        gameId: state.gameId,
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      } : { type: 'no-game' as const };
          mockGameStore.getCurrentGameId.mockReturnValue(state.gameId);
          
          if (!state.connected) {
          } else if (state.gameId) {
          } else {
          }
        });
        rerender(<GameSettings />);

        // Verify UI consistency at each step
        if (!state.connected) {
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
      const { rerender } = render(<GameSettings />);

      // Start with game active
      act(() => {
        mockGameStore.session = {
        type: 'active-game' as const,
        gameId: 'test-game',
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      };
        mockGameStore.getCurrentGameId.mockReturnValue('test-game');
      });
      rerender(<GameSettings />);

      // User clicks to expand settings
      const toggleButton = screen.getByText('⚙️ Game Settings');
      await user.click(toggleButton);
      
      // Force a re-render to see the state change
      rerender(<GameSettings />);

      // Verify panel is expanded
      await waitFor(() => {
        expect(screen.getByText('Game Mode')).toBeInTheDocument();
      });

      // Simulate race condition: game state changes while panel is open
      act(() => {
        mockGameStore.session = { type: 'no-game' as const };
        mockGameStore.getCurrentGameId.mockReturnValue(null);
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

      // Rapid loading state changes - include isCreatingGame for proper "Starting..." behavior
      const loadingStates = [
        { loading: false, creating: false, gameId: null },
        { loading: true, creating: true, gameId: null },
        { loading: false, creating: false, gameId: 'game-1' },
        { loading: true, creating: true, gameId: 'game-1' },
        { loading: false, creating: false, gameId: null }
      ];

      for (const state of loadingStates) {
        act(() => {
          mockGameStore.isLoading = state.loading;
          mockGameStore.isCreatingGame = state.creating;
          mockGameStore.session = state.gameId ? {
        type: 'active-game' as const,
        gameId: state.gameId,
        state: {
          board_size: 9,
          current_player: 0,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          walls_remaining: [10, 10],
          legal_moves: [],
          winner: null,
          move_history: []
        },
        lastSync: new Date()
      } : { type: 'no-game' as const };
          mockGameStore.getCurrentGameId.mockReturnValue(state.gameId);
          
          if (state.gameId) {
          } else {
          }
        });
        rerender(<GameSettings />);

        // Verify loading states don't break UI
        if (state.creating && !state.gameId) {
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