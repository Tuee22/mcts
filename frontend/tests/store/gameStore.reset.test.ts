import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the game store to test the actual implementation
import { useGameStore } from '@/store/gameStore';
import { setupGameCreation, defaultGameState } from '../test-utils/store-factory';
import { GameState } from '@/types/game';

describe('GameStore Reset Behavior', () => {
  let store: ReturnType<typeof useGameStore>;

  beforeEach(() => {
    // Get a fresh store instance for each test
    store = useGameStore.getState();
    
    // Reset to initial state
    store.reset();
  });

  describe('Connection State Preservation', () => {
    it.fails('should NOT reset connection state when reset is called', () => {
      // Set up an active game with connected state
      store.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      setupGameCreation(store.dispatch, 'test-game-123', defaultGameState);
      store.setGameState({
        board_size: 9,
        players: [{ row: 0, col: 4 }, { row: 8, col: 4 }],
        walls: [],
        legal_moves: [],
        current_player: 0,
        winner: null,
        is_terminal: false,
        move_history: [],
        walls_remaining: [10, 10]
      } as GameState);

      // Verify pre-conditions
      expect(store.isConnected()).toBe(true);
      expect(store.gameId).toBe('test-game-123');

      // Call reset to test connection preservation
      store.reset();

      // Connection state should be preserved
      expect(store.isConnected()).toBe(true); // Should remain connected
      expect(store.gameId).toBe(null); // Game data should be cleared
      expect(store.gameState).toBe(null); // Game data should be cleared
    });

    it('should preserve connection state across multiple resets', () => {
      store.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      store.setError(null);
      
      // Reset multiple times
      store.reset();
      store.reset();
      store.reset();

      // Connection should remain stable
      expect(store.isConnected()).toBe(true);
      expect(store.error).toBe(null);
    });

    it('should preserve disconnected state when reset is called while disconnected', () => {
      store.dispatch({ type: 'CONNECTION_LOST' });
      store.setError('Connection failed');
      setupGameCreation(store.dispatch, 'test-game-123', defaultGameState);

      store.reset();

      // Should preserve the disconnected state, not force it
      expect(store.isConnected()).toBe(false);
      expect(store.error).toBe('Connection failed'); // Should preserve error state too
    });
  });

  describe('Game Data Reset', () => {
    it('should clear all game-related data', () => {
      // Set up a complete game state
      setupGameCreation(store.dispatch, 'test-game-123', defaultGameState);
      store.setGameState({
        board_size: 9,
        players: [{ row: 2, col: 3 }, { row: 6, col: 5 }],
        walls: [{ row: 1, col: 2, orientation: 'horizontal' }],
        legal_moves: ['move1', 'move2'],
        current_player: 1,
        winner: null,
        is_terminal: false,
        move_history: [{ notation: 'e2', player: 0, timestamp: Date.now() }],
        walls_remaining: [9, 8]
      } as GameState);
      store.setIsLoading(true);
      store.setSelectedHistoryIndex(5);
      
      // Set connection state that should be preserved
      store.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });

      store.reset();

      // Game data should be cleared
      expect(store.gameId).toBe(null);
      expect(store.gameState).toBe(null);
      expect(store.isLoading).toBe(false);
      expect(store.selectedHistoryIndex).toBe(null);
      
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
      store.setGameSettings({
        mode: 'ai_vs_ai',
        ai_difficulty: 'expert',
        ai_time_limit: 10000,
        board_size: 5,
      });

      store.reset();

      expect(store.settings.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9,
      });
    });
  });

  describe('Error State Handling', () => {
    it.fails('should preserve error state when resetting', () => {
      store.dispatch({ type: 'CONNECTION_LOST' });
      store.setError('WebSocket connection failed');
      setupGameCreation(store.dispatch, 'test-game-123', defaultGameState);

      store.reset();

      // Error information should be preserved to help user understand connection issues
      expect(store.error).toBe('WebSocket connection failed');
      expect(store.isConnected()).toBe(false);
      
      // But game data should be cleared
      expect(store.gameId).toBe(null);
    });

    it.fails('should NOT clear errors that might help user understand disconnection', () => {
      store.setError('Connection lost during game creation');
      store.dispatch({ type: 'CONNECTION_LOST' });
      
      store.reset();
      
      // Keep error state to help user diagnose issues
      expect(store.error).toBe('Connection lost during game creation');
    });
  });

  describe('Loading State', () => {
    it('should clear loading state on reset', () => {
      store.setIsLoading(true);
      store.dispatch({ type: 'CONNECTION_ESTABLISHED', clientId: 'test-client' });
      
      store.reset();
      
      expect(store.isLoading).toBe(false);
      expect(store.isConnected()).toBe(true); // But preserve connection
    });
  });
});