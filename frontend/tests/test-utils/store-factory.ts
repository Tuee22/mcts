/**
 * Test utilities for creating valid store states and converting legacy patterns
 */

import { GameState, GameSettings, ConnectionState, GameSession, AppState } from '@/types/appState';

// Default game settings
export const defaultGameSettings: GameSettings = {
  mode: 'human_vs_ai',
  ai_difficulty: 'medium',
  ai_time_limit: 5000,
  board_size: 9
};

// Default game state
export const defaultGameState: GameState = {
  board_size: 9,
  current_player: 0,
  players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
  walls: [],
  walls_remaining: [10, 10],
  legal_moves: [],
  winner: null,
  move_history: []
};

/**
 * Create a connected store state
 */
export function createConnectedStore(overrides: Partial<AppState> = {}): Partial<AppState> {
  return {
    connection: {
      type: 'connected',
      clientId: 'test-client',
      since: new Date(),
      canReset: true
    },
    session: { type: 'no-game' },
    settings: {
      gameSettings: defaultGameSettings,
      theme: 'light',
      soundEnabled: true
    },
    ui: {
      settingsExpanded: false,
      selectedHistoryIndex: null,
      notifications: []
    },
    ...overrides
  };
}

/**
 * Create a disconnected store state
 */
export function createDisconnectedStore(overrides: Partial<AppState> = {}): Partial<AppState> {
  return {
    ...createConnectedStore(overrides),
    connection: { type: 'disconnected', canReset: true },
    ...overrides
  };
}

/**
 * Create an active game store state
 */
export function createActiveGameStore(
  gameId: string, 
  state: GameState = defaultGameState,
  overrides: Partial<AppState> = {}
): Partial<AppState> {
  return {
    ...createConnectedStore(),
    session: {
      type: 'active-game',
      gameId,
      state,
      lastSync: new Date()
    },
    ...overrides
  };
}

/**
 * Create a game-over store state
 */
export function createGameOverStore(
  gameId: string,
  winner: number,
  finalState: GameState = defaultGameState,
  overrides: Partial<AppState> = {}
): Partial<AppState> {
  return {
    ...createConnectedStore(),
    session: {
      type: 'game-over',
      gameId,
      state: finalState,
      winner
    },
    ...overrides
  };
}


/**
 * Convert legacy setter calls to dispatch actions
 */
export function legacySetterToDispatch(setter: string, value: any): any {
  switch (setter) {
    case 'setGameId':
      if (!value) {
        return { type: 'RESET_GAME' };
      }
      return {
        type: 'GAME_CREATED',
        gameId: value,
        state: defaultGameState
      };
      
    case 'setGameState':
      return {
        type: 'GAME_STATE_UPDATED',
        state: value
      };
      
    case 'setIsConnected':
      return value
        ? { type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' }
        : { type: 'CONNECTION_LOST' };
        
    case 'setError':
      return value
        ? { type: 'NOTIFICATION_ADDED', notification: { id: Math.random().toString(), type: 'error', message: value, timestamp: new Date() } }
        : null; // No action for clearing errors - handled differently in new architecture
        
    case 'setSelectedHistoryIndex':
      return { type: 'HISTORY_INDEX_SET', index: value };
        
    default:
      throw new Error(`Unknown setter: ${setter}`);
  }
}

/**
 * Helper to setup a game creation flow following proper state machine
 */
export function setupGameCreation(dispatch: Function, gameId: string, state: GameState = defaultGameState) {
  // Follow proper connection flow: disconnected -> connecting -> connected
  dispatch({ type: 'CONNECTION_START' });
  dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
  // In simplified state machine, create game directly
  dispatch({ type: 'GAME_CREATED', gameId, state });
}

/**
 * Helper to setup game ending flow
 */
export function setupGameEnding(dispatch: Function, gameId: string, winner: number, finalState: GameState = defaultGameState) {
  // Transition directly to new game (functional design - no intermediate states)
  dispatch({ type: 'NEW_GAME_REQUESTED' });
}

/**
 * Helper to simulate connection loss and recovery
 */
export function simulateConnectionLoss(dispatch: Function) {
  dispatch({ type: 'CONNECTION_LOST' });
}

export function simulateConnectionRecovery(dispatch: Function, clientId: string = 'test-client') {
  dispatch({ type: 'CONNECTION_START' });
  dispatch({ type: 'CONNECTION_ESTABLISHED', clientId });
}

/**
 * Mock getSettingsUI implementation that matches the actual store logic
 */
export function getMockSettingsUI(session: GameSession, connection: ConnectionState) {
  const hasGame = session.type === 'active-game' || 
                  session.type === 'game-over';
  const connected = connection.type === 'connected';
  
  if (hasGame) {
    return { type: 'button-visible' as const, enabled: connected };
  } else if (connected) {
    return { type: 'panel-visible' as const, canStartGame: true };
  } else {
    return { type: 'button-visible' as const, enabled: false };
  }
}