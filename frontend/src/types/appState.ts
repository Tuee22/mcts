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
 */
export function exhaustiveCheck(value: never): never {
  throw new Error(`Unhandled value: ${JSON.stringify(value)}`);
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

/**
 * Pure functional derivations for UI state
 * These functions make UI state predictable and testable
 */

export function deriveSettingsUIState(state: AppState): SettingsUIState {
  // Settings are a panel when no game is active
  if (state.session.type === 'no-game') {
    return {
      type: 'panel-visible',
      canStartGame: isConnected(state.connection),
      isCreating: false
    };
  }

  // Settings are a button during active gameplay or game over
  if (state.session.type === 'active-game' || state.session.type === 'game-over') {
    return {
      type: 'button-visible',
      enabled: isConnected(state.connection)
    };
  }

  // This case should never happen with the simplified state machine
  return exhaustiveCheck(state.session);
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