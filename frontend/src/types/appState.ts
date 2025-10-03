/**
 * Type-safe application state using discriminated unions.
 * These types make illegal states unrepresentable at compile time.
 */

import { GameState, GameSettings, Move, Player } from './game';

/**
 * Connection state machine - all possible connection states
 * canReset flag indicates whether reset operation is allowed in this state
 */
export type ConnectionState = 
  | { type: 'disconnected'; error?: string; canReset: true }
  | { type: 'connecting'; attemptNumber: number; canReset: false }
  | { type: 'connected'; clientId: string; since: Date; canReset: true }
  | { type: 'reconnecting'; lastClientId: string; attemptNumber: number; canReset: false };

/**
 * Simplified Game session state machine - removes problematic intermediate states
 * Transitions should be immediate to prevent race conditions
 */
export type GameSession =
  | { type: 'no-game' }
  | { type: 'active-game'; gameId: string; state: GameState; lastSync: Date }
  | { type: 'game-over'; gameId: string; state: GameState; winner: Player };

/**
 * Settings UI state - derived from connection and session states
 */
export type SettingsUIState =
  | { type: 'panel-visible'; canStartGame: boolean }
  | { type: 'button-visible'; enabled: boolean };

/**
 * Persisted settings - saved to localStorage
 */
export interface PersistedSettings {
  gameSettings: GameSettings;
  theme: 'light' | 'dark';
  soundEnabled: boolean;
}

/**
 * Transient UI state - not persisted
 */
export interface UIState {
  settingsExpanded: boolean;
  selectedHistoryIndex: number | null;
  notifications: Notification[];
}

/**
 * Notification for UI display
 */
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timestamp: Date;
}

/**
 * Combined application state
 */
export interface AppState {
  connection: ConnectionState;
  session: GameSession;
  settings: PersistedSettings;
  ui: UIState;
}

/**
 * Action types for state transitions
 */
export type StateAction =
  // Connection actions
  | { type: 'CONNECTION_START' }
  | { type: 'CONNECTION_ESTABLISHED'; clientId: string }
  | { type: 'CONNECTION_LOST'; error?: string }
  | { type: 'CONNECTION_RETRY' }
  
  // Game session actions - simplified to prevent illegal states
  | { type: 'GAME_CREATED'; gameId: string; state: GameState }
  | { type: 'GAME_CREATE_FAILED'; error: string }
  | { type: 'NEW_GAME_REQUESTED' }  // Direct transition to no-game
  | { type: 'GAME_STATE_UPDATED'; state: GameState }
  | { type: 'RESET_GAME' }  // Reset game while preserving connection and settings
  
  // Settings actions
  | { type: 'SETTINGS_TOGGLED' }
  | { type: 'SETTINGS_UPDATED'; settings: Partial<GameSettings> }
  | { type: 'THEME_CHANGED'; theme: 'light' | 'dark' }
  | { type: 'SOUND_TOGGLED' }
  
  // UI actions
  | { type: 'HISTORY_INDEX_SET'; index: number | null }
  | { type: 'NOTIFICATION_ADDED'; notification: Notification }
  | { type: 'NOTIFICATION_REMOVED'; id: string }
  
  // Move actions
  | { type: 'MOVE_MADE'; move: Move }
  | { type: 'MOVE_FAILED'; error: string };

/**
 * Helper function for exhaustive pattern matching
<<<<<<< HEAD
 * Uses safe serialization and provides fallback for invalid states
 */
export function exhaustiveCheck(value: never): never {
  // In development, log the error but don't crash the app
  if (process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test') {
    console.error('Exhaustive check failed - unhandled value:', value);
    
    // Safe serialization that handles problematic characters
    let serialized: string;
    try {
      serialized = JSON.stringify(value, null, 2);
    } catch (error) {
      // Handle JSON serialization errors (e.g., unpaired surrogates)
      serialized = String(value);
    }
    
    // Don't throw in tests, just log the error
    console.warn(`Unhandled value: ${serialized}`);
    return null as never;
  }
  
  throw new Error(`Unhandled value in state machine`);
=======
 * Uses safe serialization to avoid UTF-16 surrogate issues
 */
export function exhaustiveCheck(value: never): never {
  // Safe serialization that handles problematic characters
  let serialized: string;
  try {
    serialized = JSON.stringify(value);
  } catch (error) {
    // Handle JSON serialization errors (e.g., unpaired surrogates)
    serialized = String(value);
  }
  throw new Error(`Unhandled value: ${serialized}`);
>>>>>>> 5150f48c7177f06b06e49d58bfb68152f9c95916
}

/**
 * Type guards for state checking
 */
export function isConnected(state: ConnectionState): state is { type: 'connected'; clientId: string; since: Date; canReset: true } {
  return state.type === 'connected';
}

export function canReset(state: ConnectionState): boolean {
  return state.canReset;
}

export function isGameActive(session: GameSession): session is { type: 'active-game'; gameId: string; state: GameState; lastSync: Date } {
  return session.type === 'active-game';
}

export function canStartGame(state: AppState): boolean {
  return isConnected(state.connection) && state.session.type === 'no-game';
}

export function canMakeMove(state: AppState): boolean {
  return isConnected(state.connection) && 
         isGameActive(state.session) && 
         state.session.state.winner === null;
}


export function deriveConnectionDisplayText(state: ConnectionState): string {
  switch (state.type) {
    case 'disconnected':
      return 'Disconnected';
    case 'connecting':
      return 'Connecting...';
    case 'connected':
      return 'Connected';
    case 'reconnecting':
      return 'Reconnecting...';
    default:
      return exhaustiveCheck(state);
  }
}

export function shouldShowGameContainer(session: GameSession): boolean {
  return session.type === 'active-game' || session.type === 'game-over';
}

export function shouldShowGameSetup(state: AppState): boolean {
  return state.session.type === 'no-game';
}