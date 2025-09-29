/**
 * Type-safe application state using discriminated unions.
 * These types make illegal states unrepresentable at compile time.
 */

import { GameState, GameSettings, Move, Player } from './game';

/**
 * Connection state machine - all possible connection states
 */
export type ConnectionState = 
  | { type: 'disconnected'; error?: string }
  | { type: 'connecting'; attemptNumber: number }
  | { type: 'connected'; clientId: string; since: Date }
  | { type: 'reconnecting'; lastClientId: string; attemptNumber: number };

/**
 * Game session state machine - all possible game states
 */
export type GameSession =
  | { type: 'no-game' }
  | { type: 'creating-game'; requestId: string; settings: GameSettings }
  | { type: 'joining-game'; gameId: string }
  | { type: 'active-game'; gameId: string; state: GameState; lastSync: Date }
  | { type: 'game-ending'; gameId: string; reason: 'new-game' | 'disconnect' | 'complete' }
  | { type: 'game-over'; gameId: string; state: GameState; winner: Player };

/**
 * Settings UI state - derived from connection and session states
 */
export type SettingsUIState =
  | { type: 'panel-visible'; canStartGame: boolean; isCreating: boolean }
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
  
  // Game session actions
  | { type: 'START_GAME' }
  | { type: 'GAME_CREATED'; gameId: string; state: GameState }
  | { type: 'GAME_CREATE_FAILED'; error: string }
  | { type: 'NEW_GAME_CLICKED' }
  | { type: 'GAME_ENDED'; reason: 'complete' | 'disconnect' }
  | { type: 'GAME_STATE_UPDATED'; state: GameState }
  | { type: 'GAME_ENDING_COMPLETE' }
  
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
 */
export function exhaustiveCheck(value: never): never {
  throw new Error(`Unhandled value: ${JSON.stringify(value)}`);
}

/**
 * Type guards for state checking
 */
export function isConnected(state: ConnectionState): state is { type: 'connected'; clientId: string; since: Date } {
  return state.type === 'connected';
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