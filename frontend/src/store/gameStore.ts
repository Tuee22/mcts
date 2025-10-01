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
import { GameState } from '../types/game';
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
 * Game store interface with pure functional API
 */
interface GameStore extends AppState {
  // Action dispatcher - the only way to change state
  dispatch: (action: StateAction) => void;
  
  // Pure derived getters - the only way to access state
  getSettingsUI: () => SettingsUIState;
  canMakeMove: () => boolean;
  canStartGame: () => boolean;
  isGameActive: () => boolean;
  isConnected: () => boolean;
  getCurrentGameId: () => string | null;
  getCurrentGameState: () => GameState | null;
  getLatestError: () => string | null;
  getSelectedHistoryIndex: () => number | null;
  getIsLoading: () => boolean;
}

/**
 * Create the game store with type-safe state management
 */
export const useGameStore = create<GameStore>()(
  persist(
    (set, get) => ({
      // Initial state
      connection: { type: 'disconnected', canReset: true } as ConnectionState,
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
      
      getLatestError: () => {
        const notifications = get().ui.notifications;
        const lastError = notifications
          .filter(n => n.type === 'error')
          .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())[0];
        return lastError?.message || null;
      },
      
      getSelectedHistoryIndex: () => {
        return get().ui.selectedHistoryIndex;
      },
      
      getIsLoading: () => {
        // In functional design, there are no loading states - transitions are instant
        return false;
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

