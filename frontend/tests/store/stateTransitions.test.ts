/**
 * Tests for type-safe state transitions.
 * Verifies that illegal states are unrepresentable and all transitions are valid.
 */

import { describe, it, expect } from 'vitest';
import {
  AppState,
  ConnectionState,
  GameSession,
  PersistedSettings,
  UIState,
  exhaustiveCheck
} from '@/types/appState';
import { stateReducer, getSettingsUIState } from '@/store/stateTransitions';
import { GameState } from '@/types/game';

// Helper to create default state
function createDefaultState(): AppState {
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

  const defaultUI: UIState = {
    settingsExpanded: false,
    selectedHistoryIndex: null,
    notifications: []
  };

  return {
    connection: { type: 'disconnected' },
    session: { type: 'no-game' as const },
    settings: defaultSettings,
    ui: defaultUI
  };
}

// Helper to create test game state
function createTestGameState(): GameState {
  return {
    board_size: 9,
    current_player: 0,
    players: [
      { x: 4, y: 0 },
      { x: 4, y: 8 }
    ],
    walls: [],
    walls_remaining: [10, 10],
    legal_moves: ['e2', 'e3', 'e4'],
    winner: null,
    move_history: []
  };
}

describe('State Transitions', () => {
  describe('Connection State Machine', () => {
    it('should transition from disconnected to connecting', () => {
      const state = createDefaultState();
      const newState = stateReducer(state, { type: 'CONNECTION_START' });
      
      expect(newState.connection.type).toBe('connecting');
      if (newState.connection.type === 'connecting') {
        expect(newState.connection.attemptNumber).toBe(1);
      }
    });

    it('should transition from connecting to connected', () => {
      const state: AppState = {
        ...createDefaultState(),
        connection: { type: 'connecting', attemptNumber: 1 }
      };
      
      const newState = stateReducer(state, {
        type: 'CONNECTION_ESTABLISHED',
        clientId: 'test-client-123'
      });
      
      expect(newState.connection.type).toBe('connected');
      if (newState.connection.type === 'connected') {
        expect(newState.connection.clientId).toBe('test-client-123');
        expect(newState.connection.since).toBeInstanceOf(Date);
      }
    });

    it('should not allow invalid connection transitions', () => {
      const disconnected = createDefaultState();
      
      // Cannot go directly from disconnected to connected
      const invalid = stateReducer(disconnected, {
        type: 'CONNECTION_ESTABLISHED',
        clientId: 'test-client'
      });
      
      // State should remain unchanged
      expect(invalid.connection.type).toBe('disconnected');
    });

    it('should handle connection loss from any state', () => {
      const connected: AppState = {
        ...createDefaultState(),
        connection: { type: 'connected', clientId: 'test', since: new Date() }
      };
      
      const newState = stateReducer(connected, {
        type: 'CONNECTION_LOST',
        error: 'Network error'
      });
      
      expect(newState.connection.type).toBe('disconnected');
      if (newState.connection.type === 'disconnected') {
        expect(newState.connection.error).toBe('Network error');
      }
    });

    it('should transition to reconnecting state', () => {
      const state = createDefaultState();
      const newState = stateReducer(state, { type: 'CONNECTION_RETRY' });
      
      // From disconnected, should go to connecting (no previous client ID)
      expect(newState.connection.type).toBe('connecting');
    });
  });

  describe('Game Session State Machine', () => {
    it('should only allow game creation when connected and no game exists', () => {
      // Valid: connected + no-game
      const validState: AppState = {
        ...createDefaultState(),
        connection: { type: 'connected', clientId: 'test', since: new Date() },
        session: { type: 'no-game' as const }
      };
      
      const newState = stateReducer(validState, { type: 'START_GAME' });
      expect(newState.session.type).toBe('creating-game');
      
      // Invalid: disconnected
      const disconnectedState = createDefaultState();
      const unchanged = stateReducer(disconnectedState, { type: 'START_GAME' });
      expect(unchanged.session.type).toBe('no-game');
      
      // Invalid: game already exists
      const gameActiveState: AppState = {
        ...validState,
        session: {
          type: 'active-game',
          gameId: 'test-game',
          state: createTestGameState(),
          lastSync: new Date()
        }
      };
      
      const unchanged2 = stateReducer(gameActiveState, { type: 'START_GAME' });
      expect(unchanged2.session.type).toBe('active-game');
    });

    it('should transition from creating-game to active-game', () => {
      const state: AppState = {
        ...createDefaultState(),
        connection: { type: 'connected', clientId: 'test', since: new Date() },
        session: {
          type: 'creating-game',
          requestId: 'req-123',
          settings: createDefaultState().settings.gameSettings
        }
      };
      
      const newState = stateReducer(state, {
        type: 'GAME_CREATED',
        gameId: 'game-456',
        state: createTestGameState()
      });
      
      expect(newState.session.type).toBe('active-game');
      if (newState.session.type === 'active-game') {
        expect(newState.session.gameId).toBe('game-456');
        expect(newState.session.state).toBeDefined();
        expect(newState.session.lastSync).toBeInstanceOf(Date);
      }
    });

    it('should handle game creation failure', () => {
      const state: AppState = {
        ...createDefaultState(),
        session: {
          type: 'creating-game',
          requestId: 'req-123',
          settings: createDefaultState().settings.gameSettings
        }
      };
      
      const newState = stateReducer(state, {
        type: 'GAME_CREATE_FAILED',
        error: 'Server error'
      });
      
      expect(newState.session.type).toBe('no-game');
      expect(newState.ui.notifications).toHaveLength(1);
      expect(newState.ui.notifications[0].type).toBe('error');
    });

    it('should handle new game click transition', () => {
      const state: AppState = {
        ...createDefaultState(),
        session: {
          type: 'active-game',
          gameId: 'game-123',
          state: createTestGameState(),
          lastSync: new Date()
        }
      };
      
      const newState = stateReducer(state, { type: 'NEW_GAME_CLICKED' });
      
      expect(newState.session.type).toBe('game-ending');
      if (newState.session.type === 'game-ending') {
        expect(newState.session.gameId).toBe('game-123');
        expect(newState.session.reason).toBe('new-game');
      }
    });

    it('should complete game ending transition', () => {
      const state: AppState = {
        ...createDefaultState(),
        session: {
          type: 'game-ending',
          gameId: 'game-123',
          reason: 'new-game'
        }
      };
      
      const newState = stateReducer(state, { type: 'GAME_ENDING_COMPLETE' });
      expect(newState.session.type).toBe('no-game');
    });

    it('should transition to game-over when winner detected', () => {
      const gameStateWithWinner: GameState = {
        ...createTestGameState(),
        winner: 0
      };
      
      const state: AppState = {
        ...createDefaultState(),
        session: {
          type: 'active-game',
          gameId: 'game-123',
          state: createTestGameState(),
          lastSync: new Date()
        }
      };
      
      const newState = stateReducer(state, {
        type: 'GAME_STATE_UPDATED',
        state: gameStateWithWinner
      });
      
      expect(newState.session.type).toBe('game-over');
      if (newState.session.type === 'game-over') {
        expect(newState.session.winner).toBe(0);
        expect(newState.session.gameId).toBe('game-123');
      }
    });
  });

  describe('Settings UI State Derivation', () => {
    it('should show panel when no game exists', () => {
      const state: AppState = {
        ...createDefaultState(),
        connection: { type: 'connected', clientId: 'test', since: new Date() },
        session: { type: 'no-game' as const }
      };
      
      const settingsUI = getSettingsUIState(state);
      expect(settingsUI.type).toBe('panel-visible');
      if (settingsUI.type === 'panel-visible') {
        expect(settingsUI.canStartGame).toBe(true);
        expect(settingsUI.isCreating).toBe(false);
      }
    });

    it('should show button when game is active', () => {
      const state: AppState = {
        ...createDefaultState(),
        connection: { type: 'connected', clientId: 'test', since: new Date() },
        session: {
          type: 'active-game',
          gameId: 'game-123',
          state: createTestGameState(),
          lastSync: new Date()
        }
      };
      
      const settingsUI = getSettingsUIState(state);
      expect(settingsUI.type).toBe('button-visible');
      if (settingsUI.type === 'button-visible') {
        expect(settingsUI.enabled).toBe(true);
      }
    });

    it('should disable button when disconnected', () => {
      const state: AppState = {
        ...createDefaultState(),
        connection: { type: 'disconnected' },
        session: {
          type: 'active-game',
          gameId: 'game-123',
          state: createTestGameState(),
          lastSync: new Date()
        }
      };
      
      const settingsUI = getSettingsUIState(state);
      expect(settingsUI.type).toBe('button-visible');
      if (settingsUI.type === 'button-visible') {
        expect(settingsUI.enabled).toBe(false);
      }
    });

    it('should show creating state in panel', () => {
      const state: AppState = {
        ...createDefaultState(),
        connection: { type: 'connected', clientId: 'test', since: new Date() },
        session: {
          type: 'creating-game',
          requestId: 'req-123',
          settings: createDefaultState().settings.gameSettings
        }
      };
      
      const settingsUI = getSettingsUIState(state);
      expect(settingsUI.type).toBe('panel-visible');
      if (settingsUI.type === 'panel-visible') {
        expect(settingsUI.canStartGame).toBe(false);
        expect(settingsUI.isCreating).toBe(true);
      }
    });

    it('should respect explicit settings expansion', () => {
      const state: AppState = {
        ...createDefaultState(),
        connection: { type: 'connected', clientId: 'test', since: new Date() },
        session: {
          type: 'active-game',
          gameId: 'game-123',
          state: createTestGameState(),
          lastSync: new Date()
        },
        ui: {
          ...createDefaultState().ui,
          settingsExpanded: true
        }
      };
      
      const settingsUI = getSettingsUIState(state);
      expect(settingsUI.type).toBe('panel-visible');
    });
  });

  describe('Exhaustiveness Checking', () => {
    it('should handle all connection state types', () => {
      const states: ConnectionState[] = [
        { type: 'disconnected' },
        { type: 'connecting', attemptNumber: 1 },
        { type: 'connected', clientId: 'test', since: new Date() },
        { type: 'reconnecting', lastClientId: 'test', attemptNumber: 2 }
      ];
      
      // This test ensures TypeScript's exhaustiveness checking works
      states.forEach(state => {
        switch (state.type) {
          case 'disconnected':
            expect(state.type).toBe('disconnected');
            break;
          case 'connecting':
            expect(state.type).toBe('connecting');
            break;
          case 'connected':
            expect(state.type).toBe('connected');
            break;
          case 'reconnecting':
            expect(state.type).toBe('reconnecting');
            break;
          default:
            // This will fail to compile if we miss a case
            exhaustiveCheck(state);
        }
      });
    });

    it('should handle all game session types', () => {
      const sessions: GameSession[] = [
        { type: 'no-game' },
        { type: 'creating-game', requestId: 'req', settings: createDefaultState().settings.gameSettings },
        { type: 'joining-game', gameId: 'game-123' },
        { type: 'active-game', gameId: 'game-123', state: createTestGameState(), lastSync: new Date() },
        { type: 'game-ending', gameId: 'game-123', reason: 'new-game' },
        { type: 'game-over', gameId: 'game-123', state: createTestGameState(), winner: 0 }
      ];
      
      sessions.forEach(session => {
        switch (session.type) {
          case 'no-game':
          case 'creating-game':
          case 'joining-game':
          case 'active-game':
          case 'game-ending':
          case 'game-over':
            expect(session.type).toBeDefined();
            break;
          default:
            exhaustiveCheck(session);
        }
      });
    });
  });

  describe('Notification Management', () => {
    it('should add notifications', () => {
      const state = createDefaultState();
      const newState = stateReducer(state, {
        type: 'NOTIFICATION_ADDED',
        notification: {
          id: 'notif-1',
          type: 'info',
          message: 'Test notification',
          timestamp: new Date()
        }
      });
      
      expect(newState.ui.notifications).toHaveLength(1);
      expect(newState.ui.notifications[0].message).toBe('Test notification');
    });

    it('should remove notifications', () => {
      const state: AppState = {
        ...createDefaultState(),
        ui: {
          ...createDefaultState().ui,
          notifications: [
            {
              id: 'notif-1',
              type: 'info',
              message: 'Test 1',
              timestamp: new Date()
            },
            {
              id: 'notif-2',
              type: 'error',
              message: 'Test 2',
              timestamp: new Date()
            }
          ]
        }
      };
      
      const newState = stateReducer(state, {
        type: 'NOTIFICATION_REMOVED',
        id: 'notif-1'
      });
      
      expect(newState.ui.notifications).toHaveLength(1);
      expect(newState.ui.notifications[0].id).toBe('notif-2');
    });
  });

  describe('Settings Persistence', () => {
    it('should update game settings', () => {
      const state = createDefaultState();
      const newState = stateReducer(state, {
        type: 'SETTINGS_UPDATED',
        settings: { mode: 'ai_vs_ai', ai_difficulty: 'expert' }
      });
      
      expect(newState.settings.gameSettings.mode).toBe('ai_vs_ai');
      expect(newState.settings.gameSettings.ai_difficulty).toBe('expert');
      // Other settings should remain unchanged
      expect(newState.settings.gameSettings.ai_time_limit).toBe(5000);
    });

    it('should toggle theme', () => {
      const state = createDefaultState();
      const newState = stateReducer(state, {
        type: 'THEME_CHANGED',
        theme: 'dark'
      });
      
      expect(newState.settings.theme).toBe('dark');
    });

    it('should toggle sound', () => {
      const state = createDefaultState();
      const newState = stateReducer(state, { type: 'SOUND_TOGGLED' });
      
      expect(newState.settings.soundEnabled).toBe(false);
      
      // Toggle again
      const newState2 = stateReducer(newState, { type: 'SOUND_TOGGLED' });
      expect(newState2.settings.soundEnabled).toBe(true);
    });
  });
});