/**
 * Pure functions for state transitions.
 * All functions are immutable and return new state objects.
 */

import {
  AppState,
  ConnectionState,
  GameSession,
  SettingsUIState,
  StateAction,
  exhaustiveCheck,
  isConnected,
  isGameActive,
  Notification
} from '../types/appState';
import { GameState, GameSettings, Move } from '../types/game';

/**
 * Main state reducer - handles all state transitions
 */
export function stateReducer(state: AppState, action: StateAction): AppState {
  let newState: AppState;
  
  switch (action.type) {
    // Connection actions
    case 'CONNECTION_START':
      newState = handleConnectionStart(state);
      break;
    
    case 'CONNECTION_ESTABLISHED':
      newState = handleConnectionEstablished(state, action.clientId);
      break;
    
    case 'CONNECTION_LOST':
      newState = handleConnectionLost(state, action.error);
      break;
    
    case 'CONNECTION_RETRY':
      newState = handleConnectionRetry(state);
      break;
    
    // Game session actions
    case 'START_GAME':
      newState = handleStartGame(state);
      break;
    
    case 'GAME_CREATED':
      newState = handleGameCreated(state, action.gameId, action.state);
      break;
    
    case 'GAME_CREATE_FAILED':
      newState = handleGameCreateFailed(state, action.error);
      break;
    
    case 'NEW_GAME_CLICKED':
      newState = handleNewGameClick(state);
      break;
    
    case 'GAME_ENDED':
      newState = handleGameEnded(state, action.reason);
      break;
    
    case 'GAME_STATE_UPDATED':
      newState = handleGameStateUpdated(state, action.state);
      break;
    
    case 'GAME_ENDING_COMPLETE':
      newState = handleGameEndingComplete(state);
      break;
    
    case 'RESET_GAME':
      newState = handleResetGame(state);
      break;
    
    // Settings actions
    case 'SETTINGS_TOGGLED':
      newState = handleSettingsToggled(state);
      break;
    
    case 'SETTINGS_UPDATED':
      newState = handleSettingsUpdated(state, action.settings);
      break;
    
    case 'THEME_CHANGED':
      newState = handleThemeChanged(state, action.theme);
      break;
    
    case 'SOUND_TOGGLED':
      newState = handleSoundToggled(state);
      break;
    
    // UI actions
    case 'HISTORY_INDEX_SET':
      newState = handleHistoryIndexSet(state, action.index);
      break;
    
    case 'NOTIFICATION_ADDED':
      newState = handleNotificationAdded(state, action.notification);
      break;
    
    case 'NOTIFICATION_REMOVED':
      newState = handleNotificationRemoved(state, action.id);
      break;
    
    // Move actions
    case 'MOVE_MADE':
      newState = handleMoveMade(state, action.move);
      break;
    
    case 'MOVE_FAILED':
      newState = handleMoveFailed(state, action.error);
      break;
    
    default:
      return exhaustiveCheck(action);
  }
  
  // Validate the new state in development
  if (process.env.NODE_ENV !== 'production') {
    try {
      validateAppState(newState);
      validateStateTransition(state, newState, action);
    } catch (error) {
      console.error('State validation failed:', error);
      console.error('Action:', action);
      console.error('Previous state:', state);
      console.error('New state:', newState);
      // In development, we log but don't throw to avoid breaking the app
      // In production, validation is skipped entirely for performance
    }
  }
  
  return newState;
}

// Connection state transitions

function handleConnectionStart(state: AppState): AppState {
  if (state.connection.type === 'connected') {
    return state; // Already connected
  }
  
  const attemptNumber = state.connection.type === 'reconnecting' 
    ? state.connection.attemptNumber + 1 
    : 1;
  
  return {
    ...state,
    connection: { type: 'connecting', attemptNumber, canReset: false }
  };
}

function handleConnectionEstablished(state: AppState, clientId: string): AppState {
  if (state.connection.type !== 'connecting' && state.connection.type !== 'reconnecting') {
    return state; // Invalid transition
  }
  
  return {
    ...state,
    connection: { type: 'connected', clientId, since: new Date(), canReset: true }
  };
}

function handleConnectionLost(state: AppState, error?: string): AppState {
  // If game was creating, mark it as failed
  const session = state.session.type === 'creating-game'
    ? { type: 'no-game' } as GameSession
    : state.session;
  
  return {
    ...state,
    connection: { type: 'disconnected', error, canReset: true },
    session,
    ui: {
      ...state.ui,
      notifications: [
        ...state.ui.notifications,
        createNotification('error', error || 'Connection lost')
      ]
    }
  };
}

function handleConnectionRetry(state: AppState): AppState {
  if (state.connection.type !== 'disconnected') {
    return state;
  }
  
  const lastClientId = state.connection.type === 'disconnected' ? undefined :
                       state.connection.type === 'connected' ? state.connection.clientId :
                       state.connection.type === 'reconnecting' ? state.connection.lastClientId :
                       undefined;
  
  if (!lastClientId) {
    return handleConnectionStart(state);
  }
  
  return {
    ...state,
    connection: { type: 'reconnecting', lastClientId, attemptNumber: 1, canReset: false }
  };
}

// Game session state transitions

function handleStartGame(state: AppState): AppState {
  // Can only start from no-game state when connected
  if (!isConnected(state.connection) || state.session.type !== 'no-game') {
    return state;
  }
  
  const requestId = crypto.randomUUID();
  return {
    ...state,
    session: { 
      type: 'creating-game', 
      requestId, 
      settings: state.settings.gameSettings 
    }
  };
}

function handleGameCreated(state: AppState, gameId: string, gameState: GameState): AppState {
  if (state.session.type !== 'creating-game') {
    return state; // Unexpected game creation
  }
  
  return {
    ...state,
    session: {
      type: 'active-game',
      gameId,
      state: gameState,
      lastSync: new Date()
    },
    ui: {
      ...state.ui,
      notifications: [
        ...state.ui.notifications,
        createNotification('success', 'Game created successfully')
      ]
    }
  };
}

function handleGameCreateFailed(state: AppState, error: string): AppState {
  if (state.session.type !== 'creating-game') {
    return state;
  }
  
  return {
    ...state,
    session: { type: 'no-game' },
    ui: {
      ...state.ui,
      notifications: [
        ...state.ui.notifications,
        createNotification('error', `Failed to create game: ${error}`)
      ]
    }
  };
}

function handleNewGameClick(state: AppState): AppState {
  if (!isGameActive(state.session)) {
    return state;
  }
  
  return {
    ...state,
    session: {
      type: 'game-ending',
      gameId: state.session.gameId,
      reason: 'new-game'
    }
  };
}

function handleGameEnded(state: AppState, reason: 'complete' | 'disconnect'): AppState {
  if (!isGameActive(state.session)) {
    return state;
  }
  
  const winner = state.session.state.winner;
  
  if (winner !== null) {
    return {
      ...state,
      session: {
        type: 'game-over',
        gameId: state.session.gameId,
        state: state.session.state,
        winner
      }
    };
  }
  
  return {
    ...state,
    session: {
      type: 'game-ending',
      gameId: state.session.gameId,
      reason
    }
  };
}

function handleGameStateUpdated(state: AppState, gameState: GameState): AppState {
  if (!isGameActive(state.session)) {
    return state;
  }
  
  // Check if game ended
  if (gameState.winner !== null) {
    return {
      ...state,
      session: {
        type: 'game-over',
        gameId: state.session.gameId,
        state: gameState,
        winner: gameState.winner
      }
    };
  }
  
  return {
    ...state,
    session: {
      ...state.session,
      state: gameState,
      lastSync: new Date()
    }
  };
}

function handleGameEndingComplete(state: AppState): AppState {
  if (state.session.type !== 'game-ending') {
    return state;
  }
  
  return {
    ...state,
    session: { type: 'no-game' }
  };
}

function handleResetGame(state: AppState): AppState {
  // Only allow reset in valid connection states
  if (!state.connection.canReset) {
    console.warn('Cannot reset during connection state:', state.connection.type);
    return state; // No-op if reset not allowed
  }
  
  // Preserve connection state and error notifications based on connection type
  const preservedNotifications = state.connection.type === 'disconnected' 
    ? state.ui.notifications.filter(n => n.type === 'error') // Keep error info when disconnected
    : []; // Clear notifications when connected
  
  // Reset to no-game state while preserving connection and settings
  return {
    ...state,
    connection: state.connection, // Preserve entire connection state
    session: { type: 'no-game' },
    settings: state.settings, // Preserve user settings for better UX
    ui: {
      ...state.ui,
      selectedHistoryIndex: null,
      settingsExpanded: false,
      notifications: preservedNotifications
    }
  };
}

// Settings state transitions

function handleSettingsToggled(state: AppState): AppState {
  return {
    ...state,
    ui: {
      ...state.ui,
      settingsExpanded: !state.ui.settingsExpanded
    }
  };
}

function handleSettingsUpdated(state: AppState, settings: Partial<GameSettings>): AppState {
  return {
    ...state,
    settings: {
      ...state.settings,
      gameSettings: {
        ...state.settings.gameSettings,
        ...settings
      }
    }
  };
}

function handleThemeChanged(state: AppState, theme: 'light' | 'dark'): AppState {
  return {
    ...state,
    settings: {
      ...state.settings,
      theme
    }
  };
}

function handleSoundToggled(state: AppState): AppState {
  return {
    ...state,
    settings: {
      ...state.settings,
      soundEnabled: !state.settings.soundEnabled
    }
  };
}

// UI state transitions

function handleHistoryIndexSet(state: AppState, index: number | null): AppState {
  return {
    ...state,
    ui: {
      ...state.ui,
      selectedHistoryIndex: index
    }
  };
}

function handleNotificationAdded(state: AppState, notification: Notification): AppState {
  return {
    ...state,
    ui: {
      ...state.ui,
      notifications: [...state.ui.notifications, notification]
    }
  };
}

function handleNotificationRemoved(state: AppState, id: string): AppState {
  return {
    ...state,
    ui: {
      ...state.ui,
      notifications: state.ui.notifications.filter(n => n.id !== id)
    }
  };
}

// Move state transitions

function handleMoveMade(state: AppState, move: Move): AppState {
  if (!isGameActive(state.session)) {
    return state;
  }
  
  // Move will be reflected when game state is updated
  return state;
}

function handleMoveFailed(state: AppState, error: string): AppState {
  return {
    ...state,
    ui: {
      ...state.ui,
      notifications: [
        ...state.ui.notifications,
        createNotification('error', `Move failed: ${error}`)
      ]
    }
  };
}

// Derived state selectors

/**
 * Get the appropriate settings UI state based on current app state
 */
export function getSettingsUIState(state: AppState): SettingsUIState {
  const connected = isConnected(state.connection);
  
  // If settings are explicitly expanded, show panel
  if (state.ui.settingsExpanded) {
    const isCreating = state.session.type === 'creating-game';
    const canStart = connected && state.session.type === 'no-game';
    return { type: 'panel-visible', canStartGame: canStart, isCreating };
  }
  
  // Otherwise, determine based on session state
  switch (state.session.type) {
    case 'no-game':
      return { 
        type: 'panel-visible', 
        canStartGame: connected,
        isCreating: false 
      };
    
    case 'creating-game':
      return { 
        type: 'panel-visible', 
        canStartGame: false,
        isCreating: true 
      };
    
    case 'joining-game':
    case 'active-game':
    case 'game-ending':
    case 'game-over':
      return { 
        type: 'button-visible', 
        enabled: connected 
      };
    
    default:
      return exhaustiveCheck(state.session);
  }
}

// Helper functions

/**
 * Validates that a state transition is legal
 * Throws if the transition violates state machine rules
 */
export function validateStateTransition(
  prevState: AppState,
  nextState: AppState,
  action: StateAction
): void {
  // Validate connection state transitions
  const prevConn = prevState.connection.type;
  const nextConn = nextState.connection.type;
  
  // Connection state machine rules
  if (prevConn === 'disconnected' && nextConn === 'connected') {
    throw new Error(`Invalid transition: cannot go directly from disconnected to connected (must go through connecting)`);
  }
  if (prevConn === 'connecting' && nextConn === 'disconnected' && action.type !== 'CONNECTION_LOST') {
    throw new Error(`Invalid transition: connecting can only go to disconnected via CONNECTION_LOST`);
  }
  
  // Session state machine rules  
  const prevSession = prevState.session.type;
  const nextSession = nextState.session.type;
  
  if (prevSession === 'no-game' && nextSession === 'active-game') {
    throw new Error(`Invalid transition: cannot go directly from no-game to active-game (must go through creating-game)`);
  }
  if (prevSession === 'active-game' && nextSession === 'no-game' && action.type !== 'RESET_GAME') {
    throw new Error(`Invalid transition: active-game can only go directly to no-game via RESET_GAME`);
  }
  if (prevSession === 'game-over' && nextSession === 'active-game') {
    throw new Error(`Invalid transition: cannot go from game-over to active-game (must start new game)`);
  }
  
  // Validate reset action constraints
  if (action.type === 'RESET_GAME' && !prevState.connection.canReset) {
    throw new Error(`Invalid action: RESET_GAME not allowed when canReset is false`);
  }
  
  // Validate game creation constraints
  if (nextSession === 'creating-game' && !isConnected(nextState.connection)) {
    throw new Error(`Invalid state: cannot be creating-game while disconnected`);
  }
}

/**
 * Validates that the app state is internally consistent
 * Throws if any invariants are violated
 */
export function validateAppState(state: AppState): void {
  // Connection state validation
  switch (state.connection.type) {
    case 'disconnected':
      // No session allowed when disconnected except game-over
      if (state.session.type === 'creating-game' || state.session.type === 'joining-game') {
        throw new Error('Cannot create or join game while disconnected');
      }
      break;
    case 'connecting':
    case 'reconnecting':
      // Creating game not allowed during connection attempts
      if (state.session.type === 'creating-game') {
        throw new Error('Cannot create game while connecting');
      }
      break;
    case 'connected':
      // All session states valid when connected
      break;
    default:
      exhaustiveCheck(state.connection);
  }

  // Session state validation
  switch (state.session.type) {
    case 'no-game':
      // No game-specific UI state should be active
      if (state.ui.selectedHistoryIndex !== null) {
        throw new Error('Cannot have history index without active game');
      }
      break;
    case 'creating-game':
      // Must be connected to create game
      if (!isConnected(state.connection)) {
        throw new Error('Must be connected to create game');
      }
      break;
    case 'joining-game':
      // Must be connected to join game
      if (!isConnected(state.connection)) {
        throw new Error('Must be connected to join game');
      }
      break;
    case 'active-game':
      // Game state must be present and not terminal
      if (state.session.state.winner !== null) {
        throw new Error('Active game cannot have winner');
      }
      break;
    case 'game-ending':
      // Transitional state - no specific validation
      break;
    case 'game-over':
      // Must have a winner
      if (state.session.state.winner === null) {
        throw new Error('Game over must have winner');
      }
      if (state.session.winner !== state.session.state.winner) {
        throw new Error('Session winner must match game state winner');
      }
      break;
    default:
      exhaustiveCheck(state.session);
  }

  // Settings validation
  if (state.settings.gameSettings.board_size < 5 || state.settings.gameSettings.board_size > 19) {
    throw new Error('Board size must be between 5 and 19');
  }
  if (state.settings.gameSettings.ai_time_limit < 100) {
    throw new Error('AI time limit must be at least 100ms');
  }

  // UI state validation
  if (state.ui.selectedHistoryIndex !== null) {
    if (!isGameActive(state.session) && state.session.type !== 'game-over') {
      throw new Error('Cannot have history selection without game');
    }
    if (isGameActive(state.session)) {
      const historyLength = state.session.state.move_history?.length || 0;
      if (state.ui.selectedHistoryIndex < 0 || state.ui.selectedHistoryIndex >= historyLength) {
        throw new Error('History index out of bounds');
      }
    }
  }
}

function createNotification(
  type: 'info' | 'success' | 'warning' | 'error',
  message: string
): Notification {
  return {
    id: crypto.randomUUID(),
    type,
    message,
    timestamp: new Date()
  };
}