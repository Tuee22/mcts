import { describe, it, expect, beforeEach, vi } from 'vitest';

// Test the functional store implementation
import { useGameStore } from '@/store/gameStore';
import { GameState } from '@/types/game';
import { defaultGameState } from '../test-utils/store-factory';

describe('GameStore Reset Behavior', () => {
  beforeEach(() => {
    // Reset store to initial state using functional API
    const store = useGameStore.getState();
    store.dispatch({ type: 'RESET_GAME' });
  });

  describe('Connection State Preservation', () => {
    it('should NOT reset connection state when reset is called', () => {
      const store = useGameStore.getState();
      
      // Set up connection following proper state machine: disconnected -> connecting -> connected
      store.dispatch({ type: 'CONNECTION_START' });
      store.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      // In simplified state machine, create game directly instead of START_GAME
      store.dispatch({ 
        type: 'GAME_CREATED', 
        gameId: 'test-game-123', 
        state: {
          board_size: 9,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          legal_moves: [],
          current_player: 0,
          winner: null,
          move_history: [],
          walls_remaining: [10, 10]
        } as GameState
      });

      // Verify pre-conditions
      expect(store.isConnected()).toBe(true);
      expect(store.getCurrentGameId()).toBe('test-game-123');

      // Call reset using functional API
      store.dispatch({ type: 'RESET_GAME' });

      // Connection state should be preserved
      expect(store.isConnected()).toBe(true); // Should remain connected
      expect(store.getCurrentGameId()).toBe(null); // Game data should be cleared
      expect(store.getCurrentGameState()).toBe(null); // Game data should be cleared
    });

    it('should preserve connection state across multiple resets', () => {
      const store = useGameStore.getState();
      
      // Establish connection properly
      store.dispatch({ type: 'CONNECTION_START' });
      store.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      // Reset multiple times using functional API
      store.dispatch({ type: 'RESET_GAME' });
      store.dispatch({ type: 'RESET_GAME' });
      store.dispatch({ type: 'RESET_GAME' });

      // Connection should remain stable
      expect(store.isConnected()).toBe(true);
      expect(store.getLatestError()).toBe(null);
    });

    it('should preserve disconnected state when reset is called while disconnected', () => {
      const store = useGameStore.getState();
      
      // Trigger connection lost first (adds "Connection lost" message)
      store.dispatch({ type: 'CONNECTION_LOST' });
      
      // Create a game while disconnected (for testing)
      store.dispatch({ 
        type: 'GAME_CREATED', 
        gameId: 'test-game-123', 
        state: {
          board_size: 9,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          legal_moves: [],
          current_player: 0,
          winner: null,
          move_history: [],
          walls_remaining: [10, 10]
        } as GameState
      });

      store.dispatch({ type: 'RESET_GAME' });

      // Should preserve the disconnected state, not force it
      expect(store.isConnected()).toBe(false);
      // The error should be preserved from CONNECTION_LOST
      expect(store.getLatestError()).toBe('Connection lost'); // Should preserve error state too
    });
  });

  describe('Game Data Reset', () => {
    it('should clear all game-related data', () => {
      const store = useGameStore.getState();
      
      // Set connection state that should be preserved
      store.dispatch({ type: 'CONNECTION_START' });
      store.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      // Set up a complete game state using functional API
      // In simplified state machine, create game directly instead of START_GAME
      store.dispatch({ 
        type: 'GAME_CREATED', 
        gameId: 'test-game-123', 
        state: {
          board_size: 9,
          players: [{ x: 3, y: 2 }, { x: 5, y: 6 }],
          walls: [{ x: 2, y: 1, orientation: 'horizontal' }],
          legal_moves: ['move1', 'move2'],
          current_player: 1,
          winner: null,
          move_history: [{ notation: 'e2', player: 0, timestamp: Date.now() }],
          walls_remaining: [9, 8]
        } as GameState
      });
      
      // Update settings before reset
      store.dispatch({ 
        type: 'SETTINGS_UPDATED', 
        settings: {
          mode: 'ai_vs_ai',
          ai_difficulty: 'expert',
          ai_time_limit: 10000,
          board_size: 5
        }
      });
      
      // Set history index while game is active (valid - within range of move_history which has 1 item)
      store.dispatch({ type: 'HISTORY_INDEX_SET', index: 0 });

      store.dispatch({ type: 'RESET_GAME' });

      // Game data should be cleared
      expect(store.getCurrentGameId()).toBe(null);
      expect(store.getCurrentGameState()).toBe(null);
      expect(store.getIsLoading()).toBe(false);
      expect(store.getSelectedHistoryIndex()).toBe(null);
      
      // Game settings should be reset to defaults
      expect(store.settings.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9,
      });

      // Connection state should be preserved
      expect(store.isConnected()).toBe(true);
    });

    it('should reset game settings to defaults', () => {
      const store = useGameStore.getState();
      
      store.dispatch({ 
        type: 'SETTINGS_UPDATED',
        settings: {
          mode: 'ai_vs_ai',
          ai_difficulty: 'expert',
          ai_time_limit: 10000,
          board_size: 5,
        }
      });

      store.dispatch({ type: 'RESET_GAME' });

      expect(store.settings.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9,
      });
    });
  });

  describe('Error State Handling', () => {
    it('should preserve error state when resetting', () => {
      const store = useGameStore.getState();
      
      // Trigger connection lost (which adds "Connection lost" message)
      store.dispatch({ type: 'CONNECTION_LOST' });
      
      // Create game for testing
      store.dispatch({ 
        type: 'GAME_CREATED', 
        gameId: 'test-game-123', 
        state: {
          board_size: 9,
          players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
          walls: [],
          legal_moves: [],
          current_player: 0,
          winner: null,
          move_history: [],
          walls_remaining: [10, 10]
        } as GameState
      });

      store.dispatch({ type: 'RESET_GAME' });

      // Error information should be preserved from CONNECTION_LOST action
      expect(store.getLatestError()).toBe('Connection lost');
      expect(store.isConnected()).toBe(false);
      
      // But game data should be cleared
      expect(store.getCurrentGameId()).toBe(null);
    });

    it('should NOT clear errors that might help user understand disconnection', () => {
      const store = useGameStore.getState();
      
      store.dispatch({
        type: 'NOTIFICATION_ADDED',
        notification: {
          id: crypto.randomUUID(),
          type: 'error',
          message: 'Connection lost during game creation',
          timestamp: new Date()
        }
      });
      store.dispatch({ type: 'CONNECTION_LOST' });
      
      store.dispatch({ type: 'RESET_GAME' });
      
      // Keep error state to help user diagnose issues
      expect(store.getLatestError()).toBe('Connection lost during game creation');
    });
  });

  describe('Loading State', () => {
    it('should clear loading state on reset', () => {
      const store = useGameStore.getState();
      
      store.dispatch({ type: 'CONNECTION_START' });
      store.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      // In simplified state machine, create game directly instead of START_GAME
      store.dispatch({ type: 'GAME_CREATED', gameId: 'test-game', state: defaultGameState });
      
      store.dispatch({ type: 'RESET_GAME' });
      
      expect(store.getIsLoading()).toBe(false);
      expect(store.isConnected()).toBe(true); // But preserve connection
    });
  });
});