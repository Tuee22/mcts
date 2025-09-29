/**
 * Type-safe game store using discriminated unions.
 * All state transitions are immutable and type-checked.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  AppState,
  ConnectionState,
  GameSession,
  PersistedSettings,
  UIState,
  StateAction,
  SettingsUIState,
  isConnected,
  isGameActive,
  canStartGame as canStartGameCheck,
  canMakeMove as canMakeMoveCheck
} from '../types/appState';
import { GameState, GameSettings } from '../types/game';
import { stateReducer, getSettingsUIState } from './stateTransitions';

/**
 * Load persisted settings from localStorage
 */
function loadPersistedSettings(): PersistedSettings {
  try {
    const stored = localStorage.getItem('game-settings-storage');
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.state?.settings || getDefaultSettings();
    }
  } catch (error) {
    console.error('Failed to load persisted settings:', error);
  }
  return getDefaultSettings();
}

/**
 * Get default settings
 */
function getDefaultSettings(): PersistedSettings {
  return {
    gameSettings: {
      mode: 'human_vs_ai',
      ai_difficulty: 'medium',
      ai_time_limit: 5000,
      board_size: 9
    },
    theme: 'light',
    soundEnabled: true
  };
}

/**
 * Get default UI state
 */
function getDefaultUIState(): UIState {
  return {
    settingsExpanded: false,
    selectedHistoryIndex: null,
    notifications: []
  };
}

/**
 * Game store interface with actions and derived getters
 */
interface GameStore extends AppState {
  // Action dispatcher
  dispatch: (action: StateAction) => void;
  
  // Derived getters
  getSettingsUI: () => SettingsUIState;
  canMakeMove: () => boolean;
  canStartGame: () => boolean;
  isGameActive: () => boolean;
  isConnected: () => boolean;
  getCurrentGameId: () => string | null;
  getCurrentGameState: () => GameState | null;
  
  // Legacy compatibility methods (will be removed after migration)
  setGameId: (id: string | null) => void;
  setGameState: (state: GameState | null) => void;
  setGameSettings: (settings: Partial<GameSettings>) => void;
  setIsConnected: (connected: boolean) => void;
  setIsLoading: (loading: boolean) => void;
  setIsCreatingGame: (creating: boolean) => void;
  setError: (error: string | null) => void;
  setSelectedHistoryIndex: (index: number | null) => void;
  reset: () => void;
  
  // Legacy compatibility getters
  gameId: string | null;
  gameState: GameState | null;
  gameSettings: GameSettings;
  isLoading: boolean;
  isCreatingGame: boolean;
  error: string | null;
  selectedHistoryIndex: number | null;
}

/**
 * Create the game store with type-safe state management
 */
export const useGameStore = create<GameStore>()(
  persist(
    (set, get) => ({
      // Initial state
      connection: { type: 'disconnected' } as ConnectionState,
      session: { type: 'no-game' } as GameSession,
      settings: loadPersistedSettings(),
      ui: getDefaultUIState(),
      
      // Main dispatcher
      dispatch: (action: StateAction) => {
        const currentState = get();
        const newState = stateReducer(currentState, action);
        set(newState);
      },
      
      // Derived getters
      getSettingsUI: () => getSettingsUIState(get()),
      
      canMakeMove: () => canMakeMoveCheck(get()),
      
      canStartGame: () => canStartGameCheck(get()),
      
      isGameActive: () => {
        const state = get();
        return isGameActive(state.session);
      },
      
      isConnected: () => {
        const state = get();
        return isConnected(state.connection);
      },
      
      getCurrentGameId: () => {
        const session = get().session;
        switch (session.type) {
          case 'active-game':
          case 'game-ending':
          case 'game-over':
            return session.gameId;
          default:
            return null;
        }
      },
      
      getCurrentGameState: () => {
        const session = get().session;
        switch (session.type) {
          case 'active-game':
          case 'game-over':
            return session.state;
          default:
            return null;
        }
      },
      
      // Legacy compatibility methods
      setGameId: (id: string | null) => {
        if (id) {
          // Simulate game creation
          get().dispatch({ 
            type: 'GAME_CREATED', 
            gameId: id, 
            state: get().gameState || createEmptyGameState() 
          });
        } else {
          // Simulate game ending
          get().dispatch({ type: 'GAME_ENDING_COMPLETE' });
        }
      },
      
      setGameState: (state: GameState | null) => {
        if (state) {
          get().dispatch({ type: 'GAME_STATE_UPDATED', state });
        }
      },
      
      setGameSettings: (settings: Partial<GameSettings>) => {
        get().dispatch({ type: 'SETTINGS_UPDATED', settings });
      },
      
      setIsConnected: (connected: boolean) => {
        if (connected) {
          get().dispatch({ type: 'CONNECTION_START' });
          // Simulate connection established
          setTimeout(() => {
            get().dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'legacy-client' });
          }, 0);
        } else {
          get().dispatch({ type: 'CONNECTION_LOST' });
        }
      },
      
      setIsLoading: (loading: boolean) => {
        // Map to creating-game state
        if (loading && get().session.type === 'no-game') {
          get().dispatch({ type: 'START_GAME' });
        }
      },
      
      setIsCreatingGame: (creating: boolean) => {
        // Map to creating-game state
        if (creating && get().session.type === 'no-game') {
          get().dispatch({ type: 'START_GAME' });
        }
      },
      
      setError: (error: string | null) => {
        if (error) {
          get().dispatch({
            type: 'NOTIFICATION_ADDED',
            notification: {
              id: crypto.randomUUID(),
              type: 'error',
              message: error,
              timestamp: new Date()
            }
          });
        }
      },
      
      setSelectedHistoryIndex: (index: number | null) => {
        get().dispatch({ type: 'HISTORY_INDEX_SET', index });
      },
      
      reset: () => {
        // Reset to no-game state while preserving connection and settings
        const current = get();
        set({
          ...current,
          session: { type: 'no-game' },
          ui: {
            ...current.ui,
            selectedHistoryIndex: null,
            notifications: []
          }
        });
      },
      
      // Legacy compatibility getters
      get gameId() {
        return get().getCurrentGameId();
      },
      
      get gameState() {
        return get().getCurrentGameState();
      },
      
      get gameSettings() {
        return get().settings.gameSettings;
      },
      
      get isLoading() {
        return get().session.type === 'creating-game';
      },
      
      get isCreatingGame() {
        return get().session.type === 'creating-game';
      },
      
      get error() {
        const notifications = get().ui.notifications;
        const lastError = notifications
          .filter(n => n.type === 'error')
          .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())[0];
        return lastError?.message || null;
      },
      
      get selectedHistoryIndex() {
        return get().ui.selectedHistoryIndex;
      }
    }),
    {
      name: 'game-settings-storage',
      partialize: (state) => ({ settings: state.settings }), // Only persist settings
      version: 2, // Bump version to migrate from old format
      migrate: (persistedState: any, version: number) => {
        if (version === 1) {
          // Migrate from old format
          return {
            settings: {
              gameSettings: persistedState.gameSettings || getDefaultSettings().gameSettings,
              theme: 'light',
              soundEnabled: true
            }
          };
        }
        return persistedState;
      }
    }
  )
);

/**
 * Helper function to create an empty game state for legacy compatibility
 */
function createEmptyGameState(): GameState {
  return {
    board_size: 9,
    current_player: 0,
    players: [
      { x: 4, y: 0 },
      { x: 4, y: 8 }
    ],
    walls: [],
    walls_remaining: [10, 10],
    legal_moves: [],
    winner: null,
    move_history: []
  };
}