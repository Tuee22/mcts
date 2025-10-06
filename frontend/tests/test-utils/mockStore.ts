/**
 * Unified mock store for testing that simulates the real store behavior
 */

import { vi } from 'vitest';
import { GameState, GameSettings } from '@/types/game';

export interface MockStoreState {
  // Core state
  gameId: string | null;
  gameState: GameState | null;
  isConnected: boolean;
  error: string | null;
  selectedHistoryIndex: number | null;
  
  // Structured state matching real store
  connection: {
    type: 'disconnected' | 'connecting' | 'connected' | 'reconnecting';
    clientId?: string;
    since?: Date;
    canReset: boolean;
  };
  
  session: {
    type: 'no-game' | 'active-game' | 'game-over';
    gameId?: string;
    state?: GameState;
    winner?: number;
    lastSync?: Date;
  };
  
  settings: {
    gameSettings: GameSettings;
    theme: 'light' | 'dark';
    soundEnabled: boolean;
  };
  
  ui: {
    settingsExpanded: boolean;
    selectedHistoryIndex: number | null;
    notifications: Array<{
      id: string;
      type: 'info' | 'success' | 'warning' | 'error';
      message: string;
      timestamp: Date;
    }>;
  };
}

export function createMockGameStore() {
  const state: MockStoreState = {
    // Simple state
    gameId: null,
    gameState: null,
    isConnected: false,
    error: null,
    selectedHistoryIndex: null,
    
    // Structured state
    connection: { type: 'disconnected', canReset: true },
    session: { type: 'no-game' },
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
    }
  };
  
  const subscribers = new Set<() => void>();
  
  const notify = () => {
    subscribers.forEach(fn => fn());
  };
  
  const store = {
    // Direct state access
    getState: () => state,
    
    // Core getters matching real store
    getCurrentGameId: vi.fn(() => {
      switch (state.session.type) {
        case 'active-game':
        case 'game-over':
          return state.session.gameId || null;
        default:
          return null;
      }
    }),
    
    getCurrentGameState: vi.fn(() => {
      switch (state.session.type) {
        case 'active-game':
        case 'game-over':
          return state.session.state || null;
        default:
          return null;
      }
    }),
    
    isConnected: vi.fn(() => state.connection.type === 'connected'),
    
    getSettingsUI: vi.fn(() => {
      const hasGame = state.session.type === 'active-game' || 
                     state.session.type === 'game-over';
      const connected = state.connection.type === 'connected';
      
      // If settings are explicitly expanded, show panel
      if (state.ui.settingsExpanded) {
        const canStart = connected && !hasGame;
        return { type: 'panel-visible', canStartGame: canStart };
      }
      
      // Otherwise, determine based on session state
      // For no game, always show panel (with disabled controls if disconnected)
      if (!hasGame) {
        return { type: 'panel-visible' as const, canStartGame: connected };
      } else {
        // For active game, show toggle button
        return { type: 'button-visible' as const, enabled: connected };
      }
    }),
    
    canStartGame: vi.fn(() => {
      return state.connection.type === 'connected' && 
             state.session.type === 'no-game';
    }),
    
    canMakeMove: vi.fn(() => {
      return state.connection.type === 'connected' && 
             state.session.type === 'active-game' &&
             state.session.state !== null;
    }),
    
    isGameActive: vi.fn(() => {
      return state.session.type === 'active-game';
    }),
    
    getSelectedHistoryIndex: vi.fn(() => {
      return state.ui.selectedHistoryIndex;
    }),
    
    getLatestError: vi.fn(() => {
      const errorNotifications = state.ui.notifications.filter(n => n.type === 'error');
      if (errorNotifications.length > 0) {
        const latest = errorNotifications.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())[0];
        return latest.message;
      }
      return null;
    }),
    
    getIsLoading: vi.fn(() => false),
    
    
    // Main dispatch method
    dispatch: vi.fn((action: any) => {
      switch (action.type) {
        case 'CONNECTION_START':
          state.connection = { type: 'connecting' };
          state.isConnected = false;
          break;
          
        case 'CONNECTION_ESTABLISHED':
          state.connection = { 
            type: 'connected', 
            clientId: action.clientId,
            since: new Date()
          };
          state.isConnected = true;
          break;
          
        case 'CONNECTION_LOST':
          state.connection = { type: 'disconnected', canReset: true };
          state.isConnected = false;
          // Always add error notification to match real store behavior
          state.ui.notifications.push({
            id: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(),
            type: 'error',
            message: action.error || 'Connection lost',
            timestamp: new Date()
          });
          break;
          
        case 'GAME_CREATED':
          if (state.session.type === 'no-game') {
            state.session = {
              type: 'active-game',
              gameId: action.gameId,
              state: action.state,
              lastSync: new Date()
            };
            state.gameId = action.gameId;
            state.gameState = action.state;
          }
          break;
          
        case 'GAME_CREATE_FAILED':
          state.session = { type: 'no-game' };
          state.ui.notifications.push({
            id: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(),
            type: 'error',
            message: action.error,
            timestamp: new Date()
          });
          break;
          
        case 'GAME_STATE_UPDATED':
          if (state.session.type === 'active-game') {
            state.session.state = action.state;
            state.gameState = action.state;
            
            // Check for game end
            if (action.state.winner !== null) {
              state.session = {
                type: 'game-over',
                gameId: state.session.gameId!,
                state: action.state,
                winner: action.state.winner,
                endedAt: new Date()
              };
            }
          }
          break;
          
        case 'NEW_GAME_REQUESTED':
          state.session = { type: 'no-game' };
          state.gameId = null;
          state.gameState = null;
          break;
          
        case 'RESET_GAME':
          state.session = { type: 'no-game' };
          state.gameId = null;
          state.gameState = null;
          state.selectedHistoryIndex = null;
          state.ui.selectedHistoryIndex = null;
          state.ui.notifications = [];
          state.error = null;
          // Reset settings to defaults
          state.settings.gameSettings = {
            mode: 'human_vs_ai',
            ai_difficulty: 'medium',
            ai_time_limit: 5000,
            board_size: 9
          };
          break;
          
        case 'HISTORY_INDEX_SET':
          state.selectedHistoryIndex = action.index;
          state.ui.selectedHistoryIndex = action.index;
          break;
          
        case 'NOTIFICATION_ADDED':
          state.ui.notifications.push(action.notification);
          if (action.notification.type === 'error') {
            state.error = action.notification.message;
          }
          break;
          
        case 'NOTIFICATION_REMOVED':
          state.ui.notifications = state.ui.notifications.filter(n => n.id !== action.id);
          // Clear error if it was the removed notification
          const removedNotif = state.ui.notifications.find(n => n.id === action.id);
          if (removedNotif?.type === 'error' && removedNotif.message === state.error) {
            state.error = null;
          }
          break;
          
        case 'SETTINGS_UPDATED':
          state.settings.gameSettings = {
            ...state.settings.gameSettings,
            ...action.settings
          };
          break;
          
        case 'SETTINGS_TOGGLED':
          state.ui.settingsExpanded = !state.ui.settingsExpanded;
          break;
          
        default:
          // For unhandled actions in tests, just log
          console.warn('Unhandled action in mock store:', action.type);
      }
      
      notify();
    }),
    
    // Legacy compatibility methods
    setError: vi.fn((error: string | null) => {
      if (error) {
        store.dispatch({
          type: 'NOTIFICATION_ADDED',
          notification: {
            id: Math.random().toString(),
            type: 'error',
            message: error,
            timestamp: new Date()
          }
        });
      } else {
        state.error = null;
        // Clear error notifications
        state.ui.notifications = state.ui.notifications.filter(n => n.type !== 'error');
      }
    }),
    
    setGameSettings: vi.fn((settings: Partial<GameSettings>) => {
      store.dispatch({ type: 'SETTINGS_UPDATED', settings });
    }),
    
    setSelectedHistoryIndex: vi.fn((index: number | null) => {
      store.dispatch({ type: 'HISTORY_INDEX_SET', index });
    }),
    
    reset: vi.fn(() => {
      store.dispatch({ type: 'RESET_GAME' });
    }),
    
    // Legacy getters
    get gameId() { return state.gameId; },
    get gameState() { return state.gameState; },
    get error() { return state.error; },
    get selectedHistoryIndex() { return state.selectedHistoryIndex; },
    get settings() { return state.settings; },
    get connection() { return state.connection; },
    get session() { return state.session; },
    get ui() { return state.ui; },
    
    // Subscription
    subscribe: (fn: () => void) => {
      subscribers.add(fn);
      return () => subscribers.delete(fn);
    }
  };
  
  return store;
}

// Export a factory for creating mocked useGameStore hooks
export function createMockUseGameStore() {
  const store = createMockGameStore();
  const useGameStore = vi.fn(() => store) as any;
  useGameStore.getState = () => store;
  useGameStore.subscribe = store.subscribe;
  
  return { mockStore: store, useGameStore };
}

/**
 * Creates a proper GameState object matching the actual type definition
 */
export function createMockGameState(overrides: Partial<GameState> = {}): GameState {
  return {
    board_size: 9,
    current_player: 0,
    players: [
      { row: 8, col: 4 },
      { row: 0, col: 4 }
    ],
    walls: [],
    walls_remaining: [10, 10],
    legal_moves: [],
    winner: null,
    move_history: [],
    ...overrides
  };
}