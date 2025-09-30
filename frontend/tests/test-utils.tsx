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
    status: 'connected',
    retryCount: 0,
    lastError: null
  };

  const defaultSession: GameSession | null = null;

  const defaultSettingsUI: SettingsUIState = {
    isVisible: true,
    isExpanded: false,
    canModify: true,
    showStartButton: true,
    isLoading: false
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
    isConnected: vi.fn(() => defaultConnection.status === 'connected'),
    getCurrentGameId: vi.fn(() => defaultSession?.gameId || null),
    getCurrentGameState: vi.fn(() => defaultSession?.gameState || null),
    canStartGame: vi.fn(() => defaultConnection.status === 'connected' && !defaultSession),
    canMakeMove: vi.fn(() => false),
    isGameActive: vi.fn(() => !!defaultSession?.gameState && !defaultSession.gameState.isGameOver),

    // Legacy compatibility methods (for gradual migration)
    setGameId: vi.fn((id: string | null) => {
      if (id) {
        store.session = { 
          gameId: id, 
          gameState: store.session?.gameState || null,
          createdAt: Date.now()
        };
      } else {
        store.session = null;
      }
    }),
    setGameState: vi.fn((state: GameState | null) => {
      if (store.session) {
        store.session.gameState = state;
      }
    }),
    setGameSettings: vi.fn((settings: Partial<GameSettings>) => {
      store.settings.gameSettings = { ...store.settings.gameSettings, ...settings };
    }),
    setIsConnected: vi.fn((connected: boolean) => {
      store.connection.status = connected ? 'connected' : 'disconnected';
    }),
    setIsLoading: vi.fn((loading: boolean) => {
      store.isLoading = loading;
    }),
    setIsCreatingGame: vi.fn((creating: boolean) => {
      store.isCreatingGame = creating;
    }),
    setError: vi.fn((error: string | null) => {
      store.error = error;
    }),
    setSelectedHistoryIndex: vi.fn((index: number | null) => {
      store.ui.selectedHistoryIndex = index;
    }),
    reset: vi.fn(() => {
      store.session = null;
      store.connection.status = 'connected';
      store.ui = defaultUIState;
      store.error = null;
    }),
    addMoveToHistory: vi.fn(),

    // Legacy compatibility getters
    gameId: defaultSession?.gameId || null,
    gameState: defaultSession?.gameState || null,
    gameSettings: defaultSettings.gameSettings,
    isLoading: false,
    isCreatingGame: false,
    error: null,
    selectedHistoryIndex: defaultUIState.selectedHistoryIndex,
    
    // Apply overrides
    ...overrides
  };

  // Update legacy getters to be reactive
  Object.defineProperty(store, 'gameId', {
    get: () => store.session?.gameId || null,
    configurable: true
  });

  Object.defineProperty(store, 'gameState', {
    get: () => store.session?.gameState || null,
    configurable: true
  });

  Object.defineProperty(store, 'gameSettings', {
    get: () => store.settings.gameSettings,
    configurable: true
  });

  Object.defineProperty(store, 'isConnected', {
    get: () => store.connection.status === 'connected',
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
    (store.isConnected as any).mockReturnValue(updates.connection.status === 'connected');
  }
  if (updates.session) {
    (store.getCurrentGameId as any).mockReturnValue(updates.session?.gameId || null);
    (store.getCurrentGameState as any).mockReturnValue(updates.session?.gameState || null);
    (store.isGameActive as any).mockReturnValue(
      !!updates.session?.gameState && !updates.session.gameState.isGameOver
    );
  }
  if (updates.settings) {
    // Settings UI state might need updating based on new settings
    const canModify = store.connection.status === 'connected' && !store.session;
    (store.getSettingsUI as any).mockReturnValue({
      isVisible: true,
      isExpanded: store.ui.settingsExpanded,
      canModify,
      showStartButton: !store.session,
      isLoading: store.isLoading || false
    });
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

  // Legacy compatibility methods
  setGameId: ReturnType<typeof vi.fn>;
  setGameState: ReturnType<typeof vi.fn>;
  setGameSettings: ReturnType<typeof vi.fn>;
  setIsConnected: ReturnType<typeof vi.fn>;
  setIsLoading: ReturnType<typeof vi.fn>;
  setIsCreatingGame: ReturnType<typeof vi.fn>;
  setError: ReturnType<typeof vi.fn>;
  setSelectedHistoryIndex: ReturnType<typeof vi.fn>;
  reset: ReturnType<typeof vi.fn>;
  addMoveToHistory: ReturnType<typeof vi.fn>;

  // Legacy properties
  gameId: string | null;
  gameState: GameState | null;
  gameSettings: GameSettings;
  isLoading: boolean;
  isCreatingGame: boolean;
  error: string | null;
  selectedHistoryIndex: number | null;
}

// Re-export commonly used testing utilities
export * from '@testing-library/react';
export { vi } from 'vitest';