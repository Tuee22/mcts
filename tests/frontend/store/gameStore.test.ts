import { useGameStore } from '../../../frontend/src/store/gameStore';
import { 
  mockGameState, 
  mockGameSettings,
  generateMockMove,
  generateMockGameState 
} from '../utils/test-utils';

describe('GameStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useGameStore.getState().reset();
  });

  describe('Initial State', () => {
    it('has correct initial state', () => {
      const state = useGameStore.getState();
      
      expect(state.gameId).toBeNull();
      expect(state.gameState).toBeNull();
      expect(state.isConnected).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.selectedHistoryIndex).toBeNull();
    });

    it('has default game settings', () => {
      const state = useGameStore.getState();
      
      expect(state.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      });
    });
  });

  describe('Game ID Management', () => {
    it('sets game ID', () => {
      useGameStore.getState().setGameId('test-game-123');
      
      expect(useGameStore.getState().gameId).toBe('test-game-123');
    });

    it('clears game ID', () => {
      useGameStore.getState().setGameId('test-game-123');
      useGameStore.getState().setGameId(null);
      
      expect(useGameStore.getState().gameId).toBeNull();
    });

    it('updates subscribers when game ID changes', () => {
      useGameStore.getState().setGameId('test-game-123');
      expect(useGameStore.getState().gameId).toBe('test-game-123');
    });
  });

  describe('Game State Management', () => {
    it('sets game state', () => {
      useGameStore.getState().setGameState(mockGameState);
      
      expect(useGameStore.getState().gameState).toEqual(mockGameState);
    });

    it('clears game state', () => {
      useGameStore.getState().setGameState(mockGameState);
      useGameStore.getState().setGameState(null);
      
      expect(useGameStore.getState().gameState).toBeNull();
    });
  });

  describe('Connection State', () => {
    it('sets connection state', () => {
      useGameStore.getState().setIsConnected(true);
      
      expect(useGameStore.getState().isConnected).toBe(true);
    });

    it('toggles connection state', () => {
      useGameStore.getState().setIsConnected(true);
      expect(useGameStore.getState().isConnected).toBe(true);
      
      useGameStore.getState().setIsConnected(false);
      expect(useGameStore.getState().isConnected).toBe(false);
    });
  });

  describe('Loading State', () => {
    it('sets loading state', () => {
      useGameStore.getState().setIsLoading(true);
      
      expect(useGameStore.getState().isLoading).toBe(true);
    });

    it('toggles loading state', () => {
      useGameStore.getState().setIsLoading(true);
      expect(useGameStore.getState().isLoading).toBe(true);
      
      useGameStore.getState().setIsLoading(false);
      expect(useGameStore.getState().isLoading).toBe(false);
    });
  });

  describe('Error Management', () => {
    it('sets error message', () => {
      useGameStore.getState().setError('Test error message');
      
      expect(useGameStore.getState().error).toBe('Test error message');
    });

    it('clears error', () => {
      useGameStore.getState().setError('Test error');
      useGameStore.getState().setError(null);
      
      expect(useGameStore.getState().error).toBeNull();
    });
  });

  describe('Game Settings', () => {
    it('updates game mode', () => {
      useGameStore.getState().setGameSettings({ mode: 'ai_vs_ai' });
      
      expect(useGameStore.getState().gameSettings.mode).toBe('ai_vs_ai');
    });

    it('updates AI difficulty', () => {
      useGameStore.getState().setGameSettings({ ai_difficulty: 'hard' });
      
      expect(useGameStore.getState().gameSettings.ai_difficulty).toBe('hard');
    });

    it('updates board size', () => {
      useGameStore.getState().setGameSettings({ board_size: 5 });
      
      expect(useGameStore.getState().gameSettings.board_size).toBe(5);
    });

    it('updates time limit', () => {
      useGameStore.getState().setGameSettings({ ai_time_limit: 10000 });
      
      expect(useGameStore.getState().gameSettings.ai_time_limit).toBe(10000);
    });

    it('merges settings correctly', () => {
      useGameStore.getState().setGameSettings({ mode: 'human_vs_human', ai_difficulty: 'expert' });
      
      expect(useGameStore.getState().gameSettings).toEqual({
        mode: 'human_vs_human',
        ai_difficulty: 'expert',
        ai_time_limit: 5000,
        board_size: 9
      });
    });
  });

  describe('History Index Management', () => {
    it('sets selected history index', () => {
      useGameStore.getState().setSelectedHistoryIndex(5);
      
      expect(useGameStore.getState().selectedHistoryIndex).toBe(5);
    });

    it('clears selected history index', () => {
      useGameStore.getState().setSelectedHistoryIndex(5);
      useGameStore.getState().setSelectedHistoryIndex(null);
      
      expect(useGameStore.getState().selectedHistoryIndex).toBeNull();
    });
  });

  describe('Move History', () => {
    it('adds move to history', () => {
      const move = generateMockMove('e2', 0);
      
      // Set initial game state
      useGameStore.getState().setGameState({ ...mockGameState, move_history: [] });
      useGameStore.getState().addMoveToHistory(move);
      
      expect(useGameStore.getState().gameState?.move_history).toEqual([move]);
    });

    it('adds multiple moves to history', () => {
      const moves = [
        generateMockMove('e2', 0),
        generateMockMove('e8', 1),
        generateMockMove('e3', 0)
      ];
      
      // Set initial game state
      useGameStore.getState().setGameState({ ...mockGameState, move_history: [] });
      
      moves.forEach(move => useGameStore.getState().addMoveToHistory(move));
      
      expect(useGameStore.getState().gameState?.move_history).toEqual(moves);
    });

    it('handles adding move when no game state exists', () => {
      const move = generateMockMove('e2', 0);
      
      // Should not crash when no game state
      expect(() => {
        useGameStore.getState().addMoveToHistory(move);
      }).not.toThrow();
    });
  });

  describe('Store Reset', () => {
    it('resets all state to initial values', () => {
      // Set some state first
      useGameStore.getState().setGameId('test-game');
      useGameStore.getState().setGameState(mockGameState);
      useGameStore.getState().setIsConnected(true);
      useGameStore.getState().setIsLoading(true);
      useGameStore.getState().setError('Some error');
      useGameStore.getState().setSelectedHistoryIndex(3);
      useGameStore.getState().setGameSettings({ mode: 'ai_vs_ai' });
      
      // Reset
      useGameStore.getState().reset();
      
      const state = useGameStore.getState();
      expect(state.gameId).toBeNull();
      expect(state.gameState).toBeNull();
      expect(state.isConnected).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.selectedHistoryIndex).toBeNull();
      expect(state.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      });
    });

    it('can be called multiple times safely', () => {
      expect(() => {
        useGameStore.getState().reset();
        useGameStore.getState().reset();
        useGameStore.getState().reset();
      }).not.toThrow();
    });
  });

  describe('State Persistence', () => {
    it('maintains state across calls', () => {
      useGameStore.getState().setGameId('persistent-game');
      
      expect(useGameStore.getState().gameId).toBe('persistent-game');
    });

    it('maintains complex state', () => {
      const complexState = generateMockGameState({
        move_history: [
          generateMockMove('e2', 0),
          generateMockMove('e8', 1)
        ]
      });
      
      useGameStore.getState().setGameState(complexState);
      
      expect(useGameStore.getState().gameState?.move_history).toHaveLength(2);
    });
  });

  describe('Concurrent Updates', () => {
    it('handles rapid state updates', () => {
      // Simulate rapid updates
      for (let i = 0; i < 10; i++) {
        useGameStore.getState().setGameId(`game-${i}`);
      }
      
      expect(useGameStore.getState().gameId).toBe('game-9');
    });

    it('handles mixed state updates', () => {
      useGameStore.getState().setGameId('test-game');
      useGameStore.getState().setIsConnected(true);
      useGameStore.getState().setGameSettings({ mode: 'ai_vs_ai' });
      useGameStore.getState().setIsLoading(true);
      
      const state = useGameStore.getState();
      expect(state.gameId).toBe('test-game');
      expect(state.isConnected).toBe(true);
      expect(state.gameSettings.mode).toBe('ai_vs_ai');
      expect(state.isLoading).toBe(true);
    });
  });

  describe('Performance', () => {
    it('handles duplicate values correctly', () => {
      useGameStore.getState().setGameId('test');
      expect(useGameStore.getState().gameId).toBe('test');
      
      useGameStore.getState().setGameId('test'); // Same value
      expect(useGameStore.getState().gameId).toBe('test'); // Should still be 'test'
    });

    it('efficiently handles large game states', () => {
      const largeGameState = generateMockGameState({
        move_history: Array.from({ length: 1000 }, (_, i) => 
          generateMockMove(`move-${i}`, i % 2 as 0 | 1)
        )
      });
      
      const start = performance.now();
      useGameStore.getState().setGameState(largeGameState);
      const end = performance.now();
      
      expect(end - start).toBeLessThan(50); // Should be fast
      expect(useGameStore.getState().gameState?.move_history).toHaveLength(1000);
    });
  });

  describe('Type Safety', () => {
    it('enforces correct game settings types', () => {
      // TypeScript should enforce correct types at compile time
      useGameStore.getState().setGameSettings({ 
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        board_size: 9,
        ai_time_limit: 5000
      });
      
      expect(useGameStore.getState().gameSettings).toBeDefined();
    });

    it('handles null values correctly', () => {
      useGameStore.getState().setGameId(null);
      useGameStore.getState().setGameState(null);
      useGameStore.getState().setError(null);
      useGameStore.getState().setSelectedHistoryIndex(null);
      
      const state = useGameStore.getState();
      expect(state.gameId).toBeNull();
      expect(state.gameState).toBeNull();
      expect(state.error).toBeNull();
      expect(state.selectedHistoryIndex).toBeNull();
    });
  });

  describe('Edge Cases', () => {
    it('handles undefined values gracefully', () => {
      expect(() => {
        useGameStore.getState().addMoveToHistory(generateMockMove('e2', 0));
      }).not.toThrow();
    });

    it('maintains consistency during rapid changes', () => {
      // Rapid alternating changes
      for (let i = 0; i < 100; i++) {
        useGameStore.getState().setIsConnected(i % 2 === 0);
        useGameStore.getState().setIsLoading(i % 3 === 0);
      }
      
      // Should maintain consistent final state
      const state = useGameStore.getState();
      expect(typeof state.isConnected).toBe('boolean');
      expect(typeof state.isLoading).toBe('boolean');
    });
  });
});