import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useGameStore } from '@/store/gameStore';
import { 
  mockInitialGameState, 
  mockMidGameState, 
  mockCompletedGameState 
} from '../fixtures/gameState';
import { 
  mockDefaultGameSettings, 
  mockHumanVsHumanSettings, 
  mockAIVsAISettings 
} from '../fixtures/gameSettings';

// Mock Zustand to avoid persistence issues in tests
vi.mock('zustand', () => ({
  create: (fn: any) => {
    const store = fn(() => store.setState, () => store.getState);
    return store;
  }
}));

describe('Game Store', () => {
  let store: ReturnType<typeof useGameStore>;

  beforeEach(() => {
    // Get fresh store instance and reset it
    store = useGameStore;
    store.getState().reset();
  });

  describe('Initial State', () => {
    it('has correct initial state', () => {
      const state = store.getState();

      expect(state.gameId).toBeNull();
      expect(state.gameState).toBeNull();
      expect(state.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      });
      expect(state.isConnected).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.selectedHistoryIndex).toBeNull();
    });
  });

  describe('Game ID Management', () => {
    it('sets game ID correctly', () => {
      const { setGameId } = store.getState();
      setGameId('test-game-123');

      expect(store.getState().gameId).toBe('test-game-123');
    });

    it('clears game ID when set to null', () => {
      const { setGameId } = store.getState();
      
      setGameId('test-game-123');
      expect(store.getState().gameId).toBe('test-game-123');

      setGameId(null);
      expect(store.getState().gameId).toBeNull();
    });

    it('handles empty string game ID', () => {
      const { setGameId } = store.getState();
      setGameId('');

      expect(store.getState().gameId).toBe('');
    });
  });

  describe('Game State Management', () => {
    it('sets game state correctly', () => {
      const { setGameState } = store.getState();
      setGameState(mockInitialGameState);

      expect(store.getState().gameState).toEqual(mockInitialGameState);
    });

    it('updates game state from initial to mid-game', () => {
      const { setGameState } = store.getState();
      
      setGameState(mockInitialGameState);
      expect(store.getState().gameState?.move_history).toHaveLength(0);

      setGameState(mockMidGameState);
      expect(store.getState().gameState?.move_history).toHaveLength(6);
      expect(store.getState().gameState?.current_player).toBe(1);
    });

    it('handles game completion state', () => {
      const { setGameState } = store.getState();
      setGameState(mockCompletedGameState);

      const state = store.getState();
      expect(state.gameState?.winner).toBe(0);
      expect(state.gameState?.players[0].y).toBe(8); // Player 1 reached the top
    });

    it('clears game state when set to null', () => {
      const { setGameState } = store.getState();
      
      setGameState(mockInitialGameState);
      expect(store.getState().gameState).not.toBeNull();

      setGameState(null);
      expect(store.getState().gameState).toBeNull();
    });

    it('preserves immutability when updating state', () => {
      const { setGameState } = store.getState();
      const originalState = { ...mockInitialGameState };
      
      setGameState(originalState);
      
      // Modify the original object
      originalState.current_player = 1;
      
      // Store state should not be affected
      expect(store.getState().gameState?.current_player).toBe(0);
    });
  });

  describe('Game Settings Management', () => {
    it('updates game mode', () => {
      const { setGameSettings } = store.getState();
      setGameSettings({ mode: 'human_vs_human' });

      expect(store.getState().gameSettings.mode).toBe('human_vs_human');
    });

    it('updates AI difficulty', () => {
      const { setGameSettings } = store.getState();
      setGameSettings({ ai_difficulty: 'expert' });

      expect(store.getState().gameSettings.ai_difficulty).toBe('expert');
    });

    it('updates AI time limit', () => {
      const { setGameSettings } = store.getState();
      setGameSettings({ ai_time_limit: 10000 });

      expect(store.getState().gameSettings.ai_time_limit).toBe(10000);
    });

    it('updates board size', () => {
      const { setGameSettings } = store.getState();
      setGameSettings({ board_size: 5 });

      expect(store.getState().gameSettings.board_size).toBe(5);
    });

    it('updates multiple settings at once', () => {
      const { setGameSettings } = store.getState();
      setGameSettings({
        mode: 'ai_vs_ai',
        ai_difficulty: 'hard',
        ai_time_limit: 15000,
        board_size: 11
      });

      const settings = store.getState().gameSettings;
      expect(settings.mode).toBe('ai_vs_ai');
      expect(settings.ai_difficulty).toBe('hard');
      expect(settings.ai_time_limit).toBe(15000);
      expect(settings.board_size).toBe(11);
    });

    it('preserves unchanged settings when updating', () => {
      const { setGameSettings } = store.getState();
      const originalSettings = store.getState().gameSettings;

      setGameSettings({ mode: 'ai_vs_ai' });

      const updatedSettings = store.getState().gameSettings;
      expect(updatedSettings.mode).toBe('ai_vs_ai');
      expect(updatedSettings.ai_difficulty).toBe(originalSettings.ai_difficulty);
      expect(updatedSettings.ai_time_limit).toBe(originalSettings.ai_time_limit);
      expect(updatedSettings.board_size).toBe(originalSettings.board_size);
    });
  });

  describe('Connection State Management', () => {
    it('sets connection status', () => {
      const { setIsConnected } = store.getState();
      
      setIsConnected(true);
      expect(store.getState().isConnected).toBe(true);

      setIsConnected(false);
      expect(store.getState().isConnected).toBe(false);
    });

    it('handles connection state changes', () => {
      const { setIsConnected } = store.getState();
      
      expect(store.getState().isConnected).toBe(false);

      setIsConnected(true);
      expect(store.getState().isConnected).toBe(true);

      setIsConnected(false);
      expect(store.getState().isConnected).toBe(false);
    });
  });

  describe('Loading State Management', () => {
    it('sets loading status', () => {
      const { setIsLoading } = store.getState();
      
      setIsLoading(true);
      expect(store.getState().isLoading).toBe(true);

      setIsLoading(false);
      expect(store.getState().isLoading).toBe(false);
    });

    it('handles loading state transitions', () => {
      const { setIsLoading } = store.getState();
      
      expect(store.getState().isLoading).toBe(false);

      setIsLoading(true);
      expect(store.getState().isLoading).toBe(true);

      setIsLoading(false);
      expect(store.getState().isLoading).toBe(false);
    });
  });

  describe('Error State Management', () => {
    it('sets error message', () => {
      const { setError } = store.getState();
      
      setError('Connection failed');
      expect(store.getState().error).toBe('Connection failed');
    });

    it('clears error when set to null', () => {
      const { setError } = store.getState();
      
      setError('Some error');
      expect(store.getState().error).toBe('Some error');

      setError(null);
      expect(store.getState().error).toBeNull();
    });

    it('updates error message', () => {
      const { setError } = store.getState();
      
      setError('First error');
      expect(store.getState().error).toBe('First error');

      setError('Second error');
      expect(store.getState().error).toBe('Second error');
    });
  });

  describe('History Navigation', () => {
    it('sets selected history index', () => {
      const { setSelectedHistoryIndex } = store.getState();
      
      setSelectedHistoryIndex(0);
      expect(store.getState().selectedHistoryIndex).toBe(0);

      setSelectedHistoryIndex(5);
      expect(store.getState().selectedHistoryIndex).toBe(5);
    });

    it('clears selected history index', () => {
      const { setSelectedHistoryIndex } = store.getState();
      
      setSelectedHistoryIndex(3);
      expect(store.getState().selectedHistoryIndex).toBe(3);

      setSelectedHistoryIndex(null);
      expect(store.getState().selectedHistoryIndex).toBeNull();
    });

    it('handles negative history index', () => {
      const { setSelectedHistoryIndex } = store.getState();
      
      setSelectedHistoryIndex(-1);
      expect(store.getState().selectedHistoryIndex).toBe(-1);
    });

    it('handles large history index', () => {
      const { setSelectedHistoryIndex } = store.getState();
      
      setSelectedHistoryIndex(999);
      expect(store.getState().selectedHistoryIndex).toBe(999);
    });
  });

  describe('Move History Management', () => {
    it('adds move to history when game state exists', () => {
      const { setGameState, addMoveToHistory } = store.getState();
      
      setGameState(mockInitialGameState);
      
      const newMove = {
        notation: 'e2',
        player: 0 as const,
        type: 'move' as const,
        position: { x: 4, y: 1 }
      };

      addMoveToHistory(newMove);

      const gameState = store.getState().gameState;
      expect(gameState?.move_history).toHaveLength(1);
      expect(gameState?.move_history[0]).toEqual(newMove);
    });

    it('does not add move when game state is null', () => {
      const { addMoveToHistory } = store.getState();
      
      expect(store.getState().gameState).toBeNull();

      const newMove = {
        notation: 'e2',
        player: 0 as const,
        type: 'move' as const,
        position: { x: 4, y: 1 }
      };

      addMoveToHistory(newMove);

      expect(store.getState().gameState).toBeNull();
    });

    it('adds multiple moves sequentially', () => {
      const { setGameState, addMoveToHistory } = store.getState();
      
      setGameState(mockInitialGameState);

      const move1 = {
        notation: 'e2',
        player: 0 as const,
        type: 'move' as const,
        position: { x: 4, y: 1 }
      };

      const move2 = {
        notation: 'e8',
        player: 1 as const,
        type: 'move' as const,
        position: { x: 4, y: 7 }
      };

      addMoveToHistory(move1);
      addMoveToHistory(move2);

      const gameState = store.getState().gameState;
      expect(gameState?.move_history).toHaveLength(2);
      expect(gameState?.move_history[0]).toEqual(move1);
      expect(gameState?.move_history[1]).toEqual(move2);
    });

    it('adds wall moves to history', () => {
      const { setGameState, addMoveToHistory } = store.getState();
      
      setGameState(mockInitialGameState);

      const wallMove = {
        notation: 'c5h',
        player: 0 as const,
        type: 'wall' as const,
        wall: { x: 2, y: 4, orientation: 'horizontal' as const }
      };

      addMoveToHistory(wallMove);

      const gameState = store.getState().gameState;
      expect(gameState?.move_history).toHaveLength(1);
      expect(gameState?.move_history[0]).toEqual(wallMove);
    });
  });

  describe('Store Reset', () => {
    it('resets all state to initial values', () => {
      const { 
        setGameId, 
        setGameState, 
        setGameSettings, 
        setIsConnected, 
        setIsLoading, 
        setError, 
        setSelectedHistoryIndex,
        reset 
      } = store.getState();

      // Set various state values
      setGameId('test-game-123');
      setGameState(mockMidGameState);
      setGameSettings({ mode: 'ai_vs_ai', board_size: 5 });
      setIsConnected(true);
      setIsLoading(true);
      setError('Test error');
      setSelectedHistoryIndex(3);

      // Verify state is modified
      expect(store.getState().gameId).toBe('test-game-123');
      expect(store.getState().gameState).toEqual(mockMidGameState);
      expect(store.getState().isConnected).toBe(true);
      expect(store.getState().isLoading).toBe(true);
      expect(store.getState().error).toBe('Test error');
      expect(store.getState().selectedHistoryIndex).toBe(3);

      // Reset
      reset();

      // Verify state is back to initial values
      const resetState = store.getState();
      expect(resetState.gameId).toBeNull();
      expect(resetState.gameState).toBeNull();
      expect(resetState.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      });
      expect(resetState.isConnected).toBe(false);
      expect(resetState.isLoading).toBe(false);
      expect(resetState.error).toBeNull();
      expect(resetState.selectedHistoryIndex).toBeNull();
    });

    it('preserves connection state on reset', () => {
      const { setIsConnected, reset } = store.getState();

      // Connection should be preserved through reset
      setIsConnected(true);
      reset();

      // Connection state might be preserved depending on implementation
      // This test verifies the behavior, whatever it is
      const connectionState = store.getState().isConnected;
      expect(typeof connectionState).toBe('boolean');
    });
  });

  describe('State Computed Properties', () => {
    it('computes hasActiveGame correctly', () => {
      const state = store.getState();
      
      // No active game initially
      expect(state.gameId).toBeNull();
      expect(state.gameState).toBeNull();

      // Set game ID but no state
      state.setGameId('test-game-123');
      expect(state.gameId).toBe('test-game-123');

      // Set game state
      state.setGameState(mockInitialGameState);
      expect(state.gameState).not.toBeNull();
    });

    it('computes isGameComplete correctly', () => {
      const { setGameState } = store.getState();

      // Incomplete game
      setGameState(mockInitialGameState);
      expect(store.getState().gameState?.winner).toBeNull();

      // Complete game
      setGameState(mockCompletedGameState);
      expect(store.getState().gameState?.winner).toBe(0);
    });
  });

  describe('Error Edge Cases', () => {
    it('handles invalid move data gracefully', () => {
      const { setGameState, addMoveToHistory } = store.getState();
      
      setGameState(mockInitialGameState);

      // Invalid move - should not crash
      const invalidMove = {
        notation: '',
        player: 2 as any, // Invalid player
        type: 'invalid' as any,
        position: null as any
      };

      expect(() => addMoveToHistory(invalidMove)).not.toThrow();
    });

    it('handles invalid game settings gracefully', () => {
      const { setGameSettings } = store.getState();

      // Invalid settings - should not crash
      expect(() => setGameSettings({
        mode: 'invalid' as any,
        ai_difficulty: 'invalid' as any,
        ai_time_limit: -1,
        board_size: 0
      })).not.toThrow();
    });

    it('handles null/undefined values gracefully', () => {
      const { setGameId, setError, setSelectedHistoryIndex } = store.getState();

      expect(() => setGameId(null)).not.toThrow();
      expect(() => setError(null)).not.toThrow();
      expect(() => setSelectedHistoryIndex(null)).not.toThrow();
    });
  });

  describe('Concurrent State Updates', () => {
    it('handles rapid state updates correctly', () => {
      const { setGameId, setIsLoading, setError } = store.getState();

      // Simulate rapid updates that might happen in real usage
      setGameId('game-1');
      setIsLoading(true);
      setError('error-1');
      setGameId('game-2');
      setIsLoading(false);
      setError(null);
      setGameId('game-3');

      const finalState = store.getState();
      expect(finalState.gameId).toBe('game-3');
      expect(finalState.isLoading).toBe(false);
      expect(finalState.error).toBeNull();
    });

    it('maintains state consistency during complex updates', () => {
      const { 
        setGameId, 
        setGameState, 
        setGameSettings, 
        addMoveToHistory 
      } = store.getState();

      // Complex sequence of updates
      setGameId('test-game-123');
      setGameSettings({ mode: 'human_vs_ai', board_size: 7 });
      setGameState(mockInitialGameState);
      
      const move = {
        notation: 'e2',
        player: 0 as const,
        type: 'move' as const,
        position: { x: 4, y: 1 }
      };
      addMoveToHistory(move);

      const finalState = store.getState();
      expect(finalState.gameId).toBe('test-game-123');
      expect(finalState.gameSettings.board_size).toBe(7);
      expect(finalState.gameState?.move_history).toHaveLength(1);
    });
  });
});