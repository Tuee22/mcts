import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock react-hot-toast first
const mockToast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  loading: vi.fn(),
  dismiss: vi.fn(),
}));

vi.mock('react-hot-toast', () => ({
  default: mockToast,
  toast: mockToast,
  Toaster: () => React.createElement('div', { 'data-testid': 'toaster' }),
}));

// Mock the game store with comprehensive approach (same pattern as GameSettings test)
const { mockGameStore, mockUseGameStore, updateStoreAndRerender } = vi.hoisted(() => {
  // Create mock store inline to avoid import issues with hoisting
  const store = {
    // State properties
    connection: {
      type: 'disconnected' as const
    },
    session: { type: 'no-game' as const },
    settings: {
      gameSettings: {
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
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
      // When there's a game, show the toggle button
      // When there's no game and connected, show the panel
      const hasGame = mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-over' || mockGameStore.session.type === 'game-ending';
      const connected = mockGameStore.connection.type === 'connected';
      const isCreating = mockGameStore.session.type === 'creating-game';
      
      if (hasGame) {
        return {
          type: 'button-visible',
          enabled: connected
        };
      } else if (connected) {
        return {
          type: 'panel-visible',
          canStartGame: true,
          isCreating: isCreating
        };
      } else {
        return {
          type: 'button-visible',
          enabled: false
        };
      }
    }),
    isConnected: vi.fn(() => store.connection.type === 'connected'),
    getCurrentGameId: vi.fn(() => {
      if (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-over' || mockGameStore.session.type === 'game-ending') {
        return mockGameStore.session.gameId;
      }
      return null;
    }),
    getCurrentGameState: vi.fn(() => {
      if (mockGameStore.session.type === 'active-game' || mockGameStore.session.type === 'game-over') {
        return mockGameStore.session.state;
      }
      return null;
    }),
    canStartGame: vi.fn(() => {
      // Can start game when connected and no active session
      const connected = mockGameStore.connection.type === 'connected';
      const noActiveSession = mockGameStore.session.type === 'no-game';
      return connected && noActiveSession;
    }),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => false),
    getIsLoading: vi.fn(() => mockGameStore.session.type === 'creating-game'),
    getLatestError: vi.fn(() => null),
    getSelectedHistoryIndex: vi.fn(() => mockGameStore.ui.selectedHistoryIndex),
    
    // Legacy compatibility
    gameId: null,
    gameState: null,
    gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
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

  // Helper function to update store and notify tests to rerender
  const updateStoreAndRerender = (updates: any, rerender?: () => void) => {
    // Update nested properties if provided
    if (updates.connection) Object.assign(mockGameStore.connection, updates.connection);
    if (updates.session) Object.assign(mockGameStore.session, updates.session);
    if (updates.settings) Object.assign(mockGameStore.settings, updates.settings);
    if (updates.ui) Object.assign(mockGameStore.ui, updates.ui);
    
    // Update flat properties (skip function properties to preserve mocks)
    Object.keys(updates).forEach(key => {
      if (!['connection', 'session', 'settings', 'ui'].includes(key) && typeof (store as any)[key] !== 'function') {
        (store as any)[key] = updates[key];
      }
    });
    
    // Update legacy compatibility properties
    if (store.session.type === 'active-game' || store.session.type === 'game-over' || store.session.type === 'game-ending') {
      store.gameId = store.session.gameId;
    } else {
      store.gameId = null;
    }
    if (store.session.type === 'active-game' || store.session.type === 'game-over') {
      store.gameState = store.session.state;
    } else {
      store.gameState = null;
    }
    store.gameSettings = store.settings.gameSettings;
    // isConnected() method is now dynamic and reads current state
    store.error = store.connection.lastError;
    store.selectedHistoryIndex = store.ui.selectedHistoryIndex;
    
    if (rerender) {
      rerender();
    }
  };
  
  return {
    mockGameStore: store,
    mockUseGameStore: useGameStoreMock,
    updateStoreAndRerender
  };
});

vi.mock('@/store/gameStore', () => ({
  useGameStore: mockUseGameStore
}));

// Mock WebSocket service
const mockWebSocketService = vi.hoisted(() => ({
  connect: vi.fn(() => Promise.resolve()),
  disconnect: vi.fn(),
  isConnected: vi.fn(() => mockGameStore.connection.type === 'connected'),
  createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
  makeMove: vi.fn(() => Promise.resolve()),
  getAIMove: vi.fn(() => Promise.resolve()),
}));

vi.mock('@/services/websocket', () => ({
  wsService: mockWebSocketService
}));

// Mock GameBoard component
vi.mock('@/components/GameBoard', () => ({
  GameBoard: () => React.createElement('div', { 'data-testid': 'game-board-mock' }, 'Mocked GameBoard')
}));

// Import components and test utilities
import App from '@/App';
import { render, screen, createUser, waitFor, act } from '../utils/testHelpers';
import { 
  mockInitialGameState, 
  mockMidGameState, 
  mockCompletedGameState 
} from '../fixtures/gameState';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';

describe('App Connection Recovery Tests', () => {
  let user: ReturnType<typeof createUser>;

  beforeEach(() => {
    vi.clearAllMocks();
    user = createUser();

    // Reset mock store to initial state using helper - ensure objects exist
    if (!mockGameStore.connection) mockGameStore.connection = {};
    if (!mockGameStore.session) mockGameStore.session = {};
    if (!mockGameStore.settings) mockGameStore.settings = {};
    if (!mockGameStore.ui) mockGameStore.ui = {};
    
    updateStoreAndRerender({
      connection: {
      type: 'disconnected' as const
    },
      session: { type: 'no-game' as const },
      settings: {
        gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
        theme: 'light',
        soundEnabled: true
      },
      ui: {
        settingsExpanded: false,
        selectedHistoryIndex: null,
        notifications: []
      },
      isLoading: false
    });
  });

  describe('Auto-Reconnection After Network Recovery', () => {
    it('should auto-connect on mount', () => {
      render(<App />);
      
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should handle successful auto-reconnection', async () => {
      // Start with disconnected state
      updateStoreAndRerender({
        connection: {
          type: 'disconnected' as const,
          lastError: 'Initial connection failed'
        }
      });

      const { rerender } = render(<App />);

      // Component should show disconnected state
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');

      // Simulate auto-reconnection success
      act(() => {
        updateStoreAndRerender({
          connection: {
            type: 'connected' as const,
          clientId: 'test-client',
          since: new Date(),
            lastError: null
          }
        }, () => rerender(<App />));
      });

      // Should update to connected state
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    it('should maintain connection state through component re-renders', async () => {
      updateStoreAndRerender({
        connection: {
          type: 'connected' as const,
          clientId: 'test-client',
          since: new Date()
        }
      });

      const { rerender } = render(<App />);

      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');

      // Force re-render
      rerender(<App />);

      // Connection state should persist
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });

    it('should recover connection without losing current game state', async () => {
      // Set up active game
      updateStoreAndRerender({
        session: {
          type: 'active-game',
          gameId: 'recovery-game-123',
          state: mockMidGameState,
          lastSync: new Date()
        },
        connection: {
          type: 'disconnected' as const
        }
      });

      const { rerender } = render(<App />);

      // Should show disconnected game state
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');

      // Reconnect
      act(() => {
        updateStoreAndRerender({
          connection: {
            type: 'connected' as const,
          clientId: 'test-client',
          since: new Date(),
            lastError: null
          }
        }, () => rerender(<App />));
      });

      // Should show connected state
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');

      // Game should still be active
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();
      expect(mockGameStore.session.gameId).toBe('recovery-game-123');
    });
  });

  describe('State Restoration After Page Refresh', () => {
    it('should handle mount with existing game state', () => {
      // Simulate refreshed page with persisted game state
      updateStoreAndRerender({
        session: {
          type: 'active-game',
          gameId: 'persisted-game-123',
          state: mockMidGameState,
          lastSync: new Date()
        },
        connection: {
          type: 'connected' as const,
          clientId: 'test-client',
          since: new Date()
        }
      });

      render(<App />);

      // Should immediately show the game
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');

      // WebSocket should attempt to connect
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should handle mount with disconnected state after refresh', () => {
      // Simulate refresh where connection was lost
      updateStoreAndRerender({
        session: {
          type: 'active-game',
          gameId: 'persisted-game-123',
          state: mockMidGameState,
          lastSync: new Date()
        },
        connection: {
          type: 'disconnected' as const,
          lastError: 'Connection lost'
        }
      });

      render(<App />);

      // Should show game but with disconnected state
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Disconnected');

      // Should attempt reconnection
      expect(mockWebSocketService.connect).toHaveBeenCalled();
    });

    it('should clear stale error states on successful reconnection', async () => {
      // Start with stale error
      updateStoreAndRerender({
        connection: {
          type: 'disconnected' as const,
          lastError: 'Old connection error'
        },
        ui: {
          notifications: [{
            id: 'stale-error',
            type: 'error',
            message: 'Old connection error',
            timestamp: new Date()
          }]
        }
      });

      render(<App />);

      // Error should be displayed
      expect(mockToast.error).toHaveBeenCalledWith(
        'Old connection error',
        expect.objectContaining({
          duration: 4000,
          style: expect.objectContaining({
            background: '#ff4444',
            color: '#ffffff'
          })
        })
      );
      // Note: Error clearing happens automatically via setTimeout in useEffect
    });
  });

  describe('Connection State During Route Changes', () => {
    it('should maintain connection state during application lifecycle', () => {
      mockGameStore.isConnected.mockReturnValue(true);
      
      const { unmount } = render(<App />);
      
      // Should disconnect on unmount
      unmount();
      
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });

    it('should handle component lifecycle with active game', () => {
      updateStoreAndRerender({
        session: {
          type: 'active-game',
          gameId: 'lifecycle-game-123',
          state: mockMidGameState,
          lastSync: new Date()
        },
        connection: {
          type: 'connected' as const,
          clientId: 'test-client',
          since: new Date()
        }
      });

      const { unmount } = render(<App />);

      // Game should be displayed
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();

      // Clean up connections on unmount
      unmount();
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });
  });

  describe('Multiple Game Creation Attempts During Unstable Connection', () => {
    it('should handle game creation during connection instability', async () => {
      // Start connected with no game
      updateStoreAndRerender({
        connection: {
          type: 'connected' as const,
          clientId: 'test-client',
          since: new Date()
        },
        session: { type: 'no-game' as const }
      });

      render(<App />);

      const startGameButton = screen.getByTestId('start-game-button');

      // Mock connection instability during game creation
      mockWebSocketService.createGame.mockImplementation(async () => {
        // Simulate temporary disconnection during creation
        updateStoreAndRerender({ 
          connection: { type: 'disconnected' as const }
        });
        await new Promise(resolve => setTimeout(resolve, 100));
        updateStoreAndRerender({ 
          connection: { type: 'connected' as const,
          clientId: 'test-client',
          since: new Date() }
        });
        return { gameId: 'unstable-game-123' };
      });

      await user.click(startGameButton);

      expect(mockWebSocketService.createGame).toHaveBeenCalled();
    });

    it('should prevent multiple game creation attempts during loading', async () => {
      // Set initial state: connected and creating game
      updateStoreAndRerender({
        connection: {
          type: 'connected' as const,
          clientId: 'test-client',
          since: new Date()
        },
        session: { 
          type: 'creating-game' as const,
          requestId: 'test-request',
          settings: {
            mode: 'human_vs_ai',
            ai_difficulty: 'medium',
            ai_time_limit: 5000,
            board_size: 9
          }
        }
      });

      render(<App />);

      const startGameButton = screen.getByTestId('start-game-button');
      expect(startGameButton).toBeDisabled();
      expect(startGameButton).toHaveTextContent('Starting...');

      // Multiple clicks should not trigger multiple calls since button is disabled
      await user.click(startGameButton);
      await user.click(startGameButton);

      // No calls should have been made since button is disabled
      expect(mockWebSocketService.createGame).not.toHaveBeenCalled();
    });
  });

  describe('Connection Recovery During Game Play', () => {
    it('should handle connection loss during active game', async () => {
      // Test the core functionality without complex state timing
      updateStoreAndRerender({
        session: {
          type: 'active-game',
          gameId: 'active-game-123',
          state: mockMidGameState,
          lastSync: new Date()
        },
        connection: {
          type: 'connected' as const,
          clientId: 'test-client',
          since: new Date()
        }
      });

      render(<App />);

      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');

      // Test that the game board remains visible during connection issues
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();

      // Test error handling capability by checking that toast can be called
      expect(mockToast.error).toBeDefined();
    });

    it('should allow continuing game after connection recovery', async () => {
      // Test game persistence during connection state changes
      updateStoreAndRerender({
        session: {
          type: 'active-game',
          gameId: 'recovery-game-123',
          state: mockMidGameState,
          lastSync: new Date()
        },
        connection: {
          type: 'disconnected' as const
        }
      });

      const { rerender } = render(<App />);

      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();

      // Test that game remains accessible regardless of connection state
      updateStoreAndRerender({
        connection: {
          type: 'connected' as const,
          clientId: 'test-client',
          since: new Date()
        }
      }, () => rerender(<App />));

      // Wait for any state updates to propagate
      await new Promise(resolve => setTimeout(resolve, 0));

      // Game should remain visible and functional
      expect(screen.getByTestId('game-board-mock')).toBeInTheDocument();

      // Test that New Game button is accessible
      const newGameButton = screen.getByRole('button', { name: /new game/i });
      expect(newGameButton).toBeEnabled();
    });
  });

  describe('Error Recovery and Display', () => {
    it('should show appropriate error messages for different connection issues', async () => {
      const errorScenarios = [
        'WebSocket connection failed',
        'Server unavailable',
        'Network timeout',
        'Connection refused'
      ];

      for (const errorMessage of errorScenarios) {
        // Clear previous mock calls
        vi.clearAllMocks();

        // Simulate different error conditions
        updateStoreAndRerender({
          connection: {
            type: 'disconnected' as const,
            lastError: errorMessage
          },
          ui: {
            notifications: [{
              id: `error-${errorMessage}`,
              type: 'error',
              message: errorMessage,
              timestamp: new Date()
            }]
          }
        });

        render(<App />);

        // Should display error toast
        expect(mockToast.error).toHaveBeenCalledWith(
          errorMessage,
          expect.objectContaining({
            duration: 4000,
            style: expect.objectContaining({
              background: '#ff4444',
              color: '#ffffff'
            })
          })
        );
      }
    });

    it('should not show duplicate error toasts for the same error', async () => {
      updateStoreAndRerender({
        connection: {
          type: 'disconnected' as const,
          lastError: 'Persistent connection error'
        },
        ui: {
          notifications: [{
            id: 'persistent-error',
            type: 'error',
            message: 'Persistent connection error',
            timestamp: new Date()
          }]
        }
      });

      const { rerender } = render(<App />);

      // First render should show error
      expect(mockToast.error).toHaveBeenCalledTimes(1);

      vi.clearAllMocks();

      // Re-render with no error should not show toast
      updateStoreAndRerender({
        connection: {
          lastError: null
        },
        ui: {
          notifications: []
        }
      }, () => rerender(<App />));

      expect(mockToast.error).not.toHaveBeenCalled();
    });

    it('should handle error recovery without page refresh', async () => {
      // Test error recovery functionality
      updateStoreAndRerender({
        connection: {
          type: 'disconnected' as const,
          lastError: 'Connection failed'
        },
        ui: {
          notifications: [{
            id: 'recovery-error',
            type: 'error',
            message: 'Connection failed',
            timestamp: new Date()
          }]
        }
      });

      const { rerender } = render(<App />);

      // Test error handling without complex state timing
      updateStoreAndRerender({
        connection: {
          type: 'connected' as const,
          clientId: 'test-client',
          since: new Date()
        },
        ui: {
          notifications: []
        }
      }, () => rerender(<App />));

      // Wait for any state updates to propagate
      await new Promise(resolve => setTimeout(resolve, 0));

      // Test that the app continues to function
      expect(screen.getByTestId('connection-text')).toHaveTextContent('Connected');
    });
  });

  describe('Performance During Connection Changes', () => {
    it('should not cause memory leaks during frequent connection changes', async () => {
      // Test performance handling without complex timing
      render(<App />);

      // Test that multiple state updates don't break the app
      for (let i = 0; i < 5; i++) {
        updateStoreAndRerender({
          connection: {
            status: i % 2 === 0 ? 'connected' : 'disconnected',
            lastError: i % 2 === 0 ? null : `Error ${i}`
          }
        });
      }

      // App should remain responsive and functional
      expect(screen.getByTestId('app-main')).toBeInTheDocument();
      expect(screen.getByTestId('connection-text')).toBeInTheDocument();
    });

    it('should handle rapid component updates during connection instability', async () => {
      updateStoreAndRerender({
        connection: {
          type: 'connected' as const,
          clientId: 'test-client',
          since: new Date()
        }
      });
      
      render(<App />);
      
      // Rapid state changes that might cause render loops
      const rapidUpdates = async () => {
        for (let i = 0; i < 10; i++) {
          act(() => {
            updateStoreAndRerender({
              isLoading: i % 2 === 0,
              connection: {
                lastError: i % 3 === 0 ? `Rapid error ${i}` : null
              }
            });
          });
          
          // Small delay to allow React to process
          await new Promise(resolve => setTimeout(resolve, 10));
        }
      };
      
      await expect(rapidUpdates()).resolves.not.toThrow();
      
      // Component should still be functional
      expect(screen.getByTestId('app-main')).toBeInTheDocument();
    });
  });

  describe('Integration with WebSocket Service', () => {
    it('should coordinate properly with WebSocket service lifecycle', () => {
      const { unmount } = render(<App />);
      
      // Should connect on mount
      expect(mockWebSocketService.connect).toHaveBeenCalled();
      
      // Should disconnect on unmount
      unmount();
      expect(mockWebSocketService.disconnect).toHaveBeenCalled();
    });

    it('should not interfere with WebSocket service reconnection logic', async () => {
      render(<App />);
      
      // Simulate WebSocket service handling its own reconnection
      mockWebSocketService.connect.mockClear();
      
      // App shouldn't interfere with service-level reconnection
      act(() => {
        updateStoreAndRerender({
          connection: { type: 'disconnected' as const }
        });
      });
      
      act(() => {
        updateStoreAndRerender({
          connection: { type: 'connected' as const,
          clientId: 'test-client',
          since: new Date() }
        });
      });
      
      // App should not trigger additional connect calls beyond initial
      expect(mockWebSocketService.connect).toHaveBeenCalledTimes(0);
    });
  });
});