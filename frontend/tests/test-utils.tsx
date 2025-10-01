/**
 * Centralized test utilities for frontend tests.
 * Provides mock store factory and common test helpers.
 */

import React from 'react';
import { vi } from 'vitest';
import { render as rtlRender } from '@testing-library/react';
import type { 
  AppState, 
  ConnectionState, 
  GameSession, 
  PersistedSettings, 
  UIState, 
  SettingsUIState 
} from '../src/types/appState';
import type { GameState, GameSettings } from '../src/types/game';

/**
 * Create a mock game store with all required methods and properties
 */
export function createMockStore(overrides?: Partial<MockGameStore>) {
  const defaultSettings: PersistedSettings = {
    gameSettings: {
      mode: 'human_vs_ai',
      ai_difficulty: 'medium',
      ai_time_limit: 5000,
      board_size: 9
    },
    theme: 'light',
    soundEnabled: true
  };

  const defaultUIState: UIState = {
    settingsExpanded: false,
    selectedHistoryIndex: null,
    notifications: []
  };

  const defaultConnection: ConnectionState = {
    type: 'connected',
    clientId: 'test-client-123',
    since: new Date(),
    canReset: true
  };

  const defaultSession: GameSession = { type: 'no-game' };

  const defaultSettingsUI: SettingsUIState = {
    type: 'panel-visible',
    canStartGame: true
  };

  const store: MockGameStore = {
    // State properties
    connection: defaultConnection,
    session: defaultSession,
    settings: defaultSettings,
    ui: defaultUIState,

    // Action dispatcher
    dispatch: vi.fn(),

    // Derived getters
    getSettingsUI: vi.fn(() => defaultSettingsUI),
    isConnected: vi.fn(() => defaultConnection.type === 'connected'),
    getCurrentGameId: vi.fn(() => defaultSession.type === 'active-game' || defaultSession.type === 'game-over' ? defaultSession.gameId : null),
    getCurrentGameState: vi.fn(() => defaultSession.type === 'active-game' || defaultSession.type === 'game-over' ? defaultSession.state : null),
    canStartGame: vi.fn(() => defaultConnection.type === 'connected' && defaultSession.type === 'no-game'),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => defaultSession.type === 'active-game'),
    getSelectedHistoryIndex: vi.fn(() => defaultUIState.selectedHistoryIndex),
    getLatestError: vi.fn(() => null),
    getIsLoading: vi.fn(() => false),

    // Legacy compatibility methods (for gradual migration)
    setGameId: vi.fn((id: string | null) => {
      if (id) {
        store.session = { 
          type: 'active-game',
          gameId: id, 
          state: store.session.type === 'active-game' || store.session.type === 'game-over' ? store.session.state : null,
          lastSync: new Date()
        };
      } else {
        store.session = { type: 'no-game' };
      }
    }),
    setGameState: vi.fn((state: GameState | null) => {
      if (store.session.type === 'active-game') {
        store.session = {
          ...store.session,
          state
        };
      }
    }),
    setGameSettings: vi.fn((settings: Partial<GameSettings>) => {
      store.settings.gameSettings = { ...store.settings.gameSettings, ...settings };
    }),
    setIsConnected: vi.fn((connected: boolean) => {
      store.connection = connected 
        ? { type: 'connected', clientId: 'test-client', since: new Date(), canReset: true }
        : { type: 'disconnected', canReset: true };
    }),
    setError: vi.fn((error: string | null) => {
      store.error = error;
    }),
    setSelectedHistoryIndex: vi.fn((index: number | null) => {
      store.ui.selectedHistoryIndex = index;
    }),
    reset: vi.fn(() => {
      store.session = { type: 'no-game' };
      store.connection = { type: 'connected', clientId: 'test-client', since: new Date(), canReset: true };
      store.ui = defaultUIState;
      store.error = null;
    }),
    addMoveToHistory: vi.fn(),

    // Legacy compatibility getters  
    gameId: null,
    gameState: null,
    gameSettings: defaultSettings.gameSettings,
    error: null,
    selectedHistoryIndex: defaultUIState.selectedHistoryIndex,
    
    // Apply overrides
    ...overrides
  };

  // Update legacy getters to be reactive
  Object.defineProperty(store, 'gameId', {
    get: () => store.session.type === 'active-game' || store.session.type === 'game-over' ? store.session.gameId : null,
    configurable: true
  });

  Object.defineProperty(store, 'gameState', {
    get: () => store.session.type === 'active-game' || store.session.type === 'game-over' ? store.session.state : null,
    configurable: true
  });

  Object.defineProperty(store, 'gameSettings', {
    get: () => store.settings.gameSettings,
    configurable: true
  });

  Object.defineProperty(store, 'isConnected', {
    get: () => store.connection.type === 'connected',
    configurable: true
  });

  Object.defineProperty(store, 'selectedHistoryIndex', {
    get: () => store.ui.selectedHistoryIndex,
    configurable: true
  });

  return store;
}

/**
 * Create a mock useGameStore hook
 */
export function createMockUseGameStore(store?: MockGameStore) {
  const mockStore = store || createMockStore();
  const useGameStoreMock = vi.fn(() => mockStore);
  useGameStoreMock.getState = vi.fn(() => mockStore);
  return { mockStore, useGameStoreMock };
}

/**
 * Helper to update mock store state
 */
export function updateMockStore(store: MockGameStore, updates: Partial<MockGameStore>) {
  Object.assign(store, updates);
  
  // Update method return values if needed
  if (updates.connection) {
    (store.isConnected as any).mockReturnValue(updates.connection.type === 'connected');
  }
  if (updates.session) {
    const gameId = updates.session.type === 'active-game' || updates.session.type === 'game-over' ? updates.session.gameId : null;
    const gameState = updates.session.type === 'active-game' || updates.session.type === 'game-over' ? updates.session.state : null;
    (store.getCurrentGameId as any).mockReturnValue(gameId);
    (store.getCurrentGameState as any).mockReturnValue(gameState);
    (store.isGameActive as any).mockReturnValue(updates.session.type === 'active-game');
  }
  if (updates.settings) {
    // Settings UI state might need updating based on new settings
    const connected = store.connection.type === 'connected';
    const hasGame = store.session.type === 'active-game' || store.session.type === 'game-over';
    
    if (hasGame) {
      (store.getSettingsUI as any).mockReturnValue({
        type: 'button-visible',
        enabled: connected
      });
    } else {
      (store.getSettingsUI as any).mockReturnValue({
        type: 'panel-visible',
        canStartGame: connected
      });
    }
  }
}

/**
 * Custom render function that includes common providers
 */
export function renderWithProviders(
  ui: React.ReactElement,
  {
    preloadedState,
    ...renderOptions
  }: {
    preloadedState?: Partial<MockGameStore>;
  } = {}
) {
  const store = createMockStore(preloadedState);

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
  }

  return { 
    ...rtlRender(ui, { wrapper: Wrapper, ...renderOptions }), 
    store 
  };
}

/**
 * Mock game store interface combining new and legacy APIs
 */
export interface MockGameStore extends Partial<AppState> {
  // New API methods
  dispatch: ReturnType<typeof vi.fn>;
  getSettingsUI: ReturnType<typeof vi.fn>;
  isConnected: ReturnType<typeof vi.fn>;
  getCurrentGameId: ReturnType<typeof vi.fn>;
  getCurrentGameState: ReturnType<typeof vi.fn>;
  canStartGame: ReturnType<typeof vi.fn>;
  canMakeMove: ReturnType<typeof vi.fn>;
  isGameActive: ReturnType<typeof vi.fn>;
  getSelectedHistoryIndex: ReturnType<typeof vi.fn>;
  getLatestError: ReturnType<typeof vi.fn>;
  getIsLoading: ReturnType<typeof vi.fn>;

  // Legacy compatibility methods
  setGameId: ReturnType<typeof vi.fn>;
  setGameState: ReturnType<typeof vi.fn>;
  setGameSettings: ReturnType<typeof vi.fn>;
  setIsConnected: ReturnType<typeof vi.fn>;
  setError: ReturnType<typeof vi.fn>;
  setSelectedHistoryIndex: ReturnType<typeof vi.fn>;
  reset: ReturnType<typeof vi.fn>;
  addMoveToHistory: ReturnType<typeof vi.fn>;

  // Legacy properties
  gameId: string | null;
  gameState: GameState | null;
  gameSettings: GameSettings;
  error: string | null;
  selectedHistoryIndex: number | null;
}

// Re-export commonly used testing utilities
export * from '@testing-library/react';
export { vi } from 'vitest';