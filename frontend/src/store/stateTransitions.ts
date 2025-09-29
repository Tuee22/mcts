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
import { GameState } from '../types/game';

/**
 * Main state reducer - handles all state transitions
 */
export function stateReducer(state: AppState, action: StateAction): AppState {
  switch (action.type) {
    // Connection actions
    case 'CONNECTION_START':
      return handleConnectionStart(state);
    
    case 'CONNECTION_ESTABLISHED':
      return handleConnectionEstablished(state, action.clientId);
    
    case 'CONNECTION_LOST':
      return handleConnectionLost(state, action.error);
    
    case 'CONNECTION_RETRY':
      return handleConnectionRetry(state);
    
    // Game session actions
    case 'START_GAME':
      return handleStartGame(state);
    
    case 'GAME_CREATED':
      return handleGameCreated(state, action.gameId, action.state);
    
    case 'GAME_CREATE_FAILED':
      return handleGameCreateFailed(state, action.error);
    
    case 'NEW_GAME_CLICKED':
      return handleNewGameClick(state);
    
    case 'GAME_ENDED':
      return handleGameEnded(state, action.reason);
    
    case 'GAME_STATE_UPDATED':
      return handleGameStateUpdated(state, action.state);
    
    case 'GAME_ENDING_COMPLETE':
      return handleGameEndingComplete(state);
    
    // Settings actions
    case 'SETTINGS_TOGGLED':
      return handleSettingsToggled(state);
    
    case 'SETTINGS_UPDATED':
      return handleSettingsUpdated(state, action.settings);
    
    case 'THEME_CHANGED':
      return handleThemeChanged(state, action.theme);
    
    case 'SOUND_TOGGLED':
      return handleSoundToggled(state);
    
    // UI actions
    case 'HISTORY_INDEX_SET':
      return handleHistoryIndexSet(state, action.index);
    
    case 'NOTIFICATION_ADDED':
      return handleNotificationAdded(state, action.notification);
    
    case 'NOTIFICATION_REMOVED':
      return handleNotificationRemoved(state, action.id);
    
    // Move actions
    case 'MOVE_MADE':
      return handleMoveMade(state, action.move);
    
    case 'MOVE_FAILED':
      return handleMoveFailed(state, action.error);
    
    default:
      return exhaustiveCheck(action);
  }
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
    connection: { type: 'connecting', attemptNumber }
  };
}

function handleConnectionEstablished(state: AppState, clientId: string): AppState {
  if (state.connection.type !== 'connecting' && state.connection.type !== 'reconnecting') {
    return state; // Invalid transition
  }
  
  return {
    ...state,
    connection: { type: 'connected', clientId, since: new Date() }
  };
}

function handleConnectionLost(state: AppState, error?: string): AppState {
  // If game was creating, mark it as failed
  const session = state.session.type === 'creating-game'
    ? { type: 'no-game' } as GameSession
    : state.session;
  
  return {
    ...state,
    connection: { type: 'disconnected', error },
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
    connection: { type: 'reconnecting', lastClientId, attemptNumber: 1 }
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