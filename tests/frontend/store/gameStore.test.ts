import { act, renderHook } from '@testing-library/react';
import { useGameStore } from '../../../frontend/src/store/gameStore';
import { 
  mockGameState, 
  mockGameSettings,
  generateMockMove,
  generateMockGameState 
} from '../utils/test-utils';

// Use actual zustand implementation for testing

describe('GameStore', () => {
  beforeEach(() => {
    // Reset store before each test
    act(() => {
      useGameStore.getState().reset();
    });
  });

  describe('Initial State', () => {
    it('has correct initial state', () => {
      const { result } = renderHook(() => useGameStore());
      
      expect(result.current.gameId).toBeNull();
      expect(result.current.gameState).toBeNull();
      expect(result.current.isConnected).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.selectedHistoryIndex).toBeNull();
    });

    it('has default game settings', () => {
      const { result } = renderHook(() => useGameStore());
      
      expect(result.current.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      });
    });
  });

  describe('Game ID Management', () => {
    it('sets game ID', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameId('test-game-123');
      });
      
      expect(result.current.gameId).toBe('test-game-123');
    });

    it('clears game ID', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameId('test-game-123');
        result.current.setGameId(null);
      });
      
      expect(result.current.gameId).toBeNull();
    });

    it('updates subscribers when game ID changes', () => {
      const { result, rerender } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameId('test-game-123');
      });
      
      rerender();
      expect(result.current.gameId).toBe('test-game-123');
    });
  });

  describe('Game State Management', () => {
    it('sets game state', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameState(mockGameState);
      });
      
      expect(result.current.gameState).toEqual(mockGameState);
    });

    it('clears game state', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameState(mockGameState);
        result.current.setGameState(null);
      });
      
      expect(result.current.gameState).toBeNull();
    });

    it('updates game state partially', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameState(mockGameState);
      });
      
      const updatedState = {
        ...mockGameState,
        current_player: 1 as 0 | 1,
        players: [{ x: 4, y: 1 }, { x: 4, y: 8 }]
      };
      
      act(() => {
        result.current.setGameState(updatedState);
      });
      
      expect(result.current.gameState?.current_player).toBe(1);
      expect(result.current.gameState?.players).toEqual([{ x: 4, y: 1 }, { x: 4, y: 8 }]);
    });
  });

  describe('Game Settings Management', () => {
    it('updates game settings partially', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameSettings({ mode: 'ai_vs_ai' });
      });
      
      expect(result.current.gameSettings.mode).toBe('ai_vs_ai');
      expect(result.current.gameSettings.ai_difficulty).toBe('medium'); // Should keep other settings
    });

    it('updates multiple settings at once', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameSettings({
          mode: 'human_vs_human',
          board_size: 7,
          ai_time_limit: 10000
        });
      });
      
      expect(result.current.gameSettings.mode).toBe('human_vs_human');
      expect(result.current.gameSettings.board_size).toBe(7);
      expect(result.current.gameSettings.ai_time_limit).toBe(10000);
    });

    it('validates setting changes', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameSettings({ ai_difficulty: 'expert' });
      });
      
      expect(result.current.gameSettings.ai_difficulty).toBe('expert');
    });
  });

  describe('Connection State Management', () => {
    it('sets connection state', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setIsConnected(true);
      });
      
      expect(result.current.isConnected).toBe(true);
    });

    it('toggles connection state', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setIsConnected(true);
        result.current.setIsConnected(false);
      });
      
      expect(result.current.isConnected).toBe(false);
    });
  });

  describe('Loading State Management', () => {
    it('sets loading state', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setIsLoading(true);
      });
      
      expect(result.current.isLoading).toBe(true);
    });

    it('clears loading state', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setIsLoading(true);
        result.current.setIsLoading(false);
      });
      
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('Error Management', () => {
    it('sets error message', () => {
      const { result } = renderHook(() => useGameStore());
      const errorMessage = 'Connection failed';
      
      act(() => {
        result.current.setError(errorMessage);
      });
      
      expect(result.current.error).toBe(errorMessage);
    });

    it('clears error message', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setError('Some error');
        result.current.setError(null);
      });
      
      expect(result.current.error).toBeNull();
    });

    it('overwrites previous error', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setError('First error');
        result.current.setError('Second error');
      });
      
      expect(result.current.error).toBe('Second error');
    });
  });

  describe('History Index Management', () => {
    it('sets selected history index', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setSelectedHistoryIndex(5);
      });
      
      expect(result.current.selectedHistoryIndex).toBe(5);
    });

    it('clears selected history index', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setSelectedHistoryIndex(3);
        result.current.setSelectedHistoryIndex(null);
      });
      
      expect(result.current.selectedHistoryIndex).toBeNull();
    });

    it('updates to different history index', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setSelectedHistoryIndex(2);
        result.current.setSelectedHistoryIndex(7);
      });
      
      expect(result.current.selectedHistoryIndex).toBe(7);
    });
  });

  describe('Move History Management', () => {
    beforeEach(() => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameState(mockGameState);
      });
    });

    it('adds move to history', () => {
      const { result } = renderHook(() => useGameStore());
      const move = generateMockMove('e2', 0);
      
      act(() => {
        result.current.addMoveToHistory(move);
      });
      
      expect(result.current.gameState?.move_history).toContain(move);
      expect(result.current.gameState?.move_history).toHaveLength(1);
    });

    it('adds multiple moves to history', () => {
      const { result } = renderHook(() => useGameStore());
      const move1 = generateMockMove('e2', 0);
      const move2 = generateMockMove('e8', 1);
      
      act(() => {
        result.current.addMoveToHistory(move1);
        result.current.addMoveToHistory(move2);
      });
      
      expect(result.current.gameState?.move_history).toEqual([move1, move2]);
    });

    it('maintains move order in history', () => {
      const { result } = renderHook(() => useGameStore());
      const moves = [
        generateMockMove('e2', 0),
        generateMockMove('e8', 1),
        generateMockMove('e3', 0)
      ];
      
      act(() => {
        moves.forEach(move => result.current.addMoveToHistory(move));
      });
      
      expect(result.current.gameState?.move_history).toEqual(moves);
    });

    it('handles adding move when no game state exists', () => {
      const { result } = renderHook(() => useGameStore());
      const move = generateMockMove('e2', 0);
      
      act(() => {
        result.current.setGameState(null);
        result.current.addMoveToHistory(move);
      });
      
      expect(result.current.gameState).toBeNull();
    });
  });

  describe('Store Reset', () => {
    it('resets all state to initial values', () => {
      const { result } = renderHook(() => useGameStore());
      
      // Set some state first
      act(() => {
        result.current.setGameId('test-game');
        result.current.setGameState(mockGameState);
        result.current.setIsConnected(true);
        result.current.setIsLoading(true);
        result.current.setError('Some error');
        result.current.setSelectedHistoryIndex(3);
        result.current.setGameSettings({ mode: 'ai_vs_ai' });
      });
      
      // Reset
      act(() => {
        result.current.reset();
      });
      
      expect(result.current.gameId).toBeNull();
      expect(result.current.gameState).toBeNull();
      expect(result.current.isConnected).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.selectedHistoryIndex).toBeNull();
      expect(result.current.gameSettings).toEqual({
        mode: 'human_vs_ai',
        ai_difficulty: 'medium',
        ai_time_limit: 5000,
        board_size: 9
      });
    });

    it('can be called multiple times safely', () => {
      const { result } = renderHook(() => useGameStore());
      
      expect(() => {
        act(() => {
          result.current.reset();
          result.current.reset();
          result.current.reset();
        });
      }).not.toThrow();
    });
  });

  describe('State Persistence', () => {
    it('maintains state across re-renders', () => {
      const { result, rerender } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameId('persistent-game');
      });
      
      rerender();
      
      expect(result.current.gameId).toBe('persistent-game');
    });

    it('maintains complex state across re-renders', () => {
      const { result, rerender } = renderHook(() => useGameStore());
      
      const complexState = generateMockGameState({
        move_history: [
          generateMockMove('e2', 0),
          generateMockMove('e8', 1)
        ]
      });
      
      act(() => {
        result.current.setGameState(complexState);
      });
      
      rerender();
      
      expect(result.current.gameState?.move_history).toHaveLength(2);
    });
  });

  describe('Concurrent Updates', () => {
    it('handles rapid state updates', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        // Simulate rapid updates
        for (let i = 0; i < 10; i++) {
          result.current.setGameId(`game-${i}`);
        }
      });
      
      expect(result.current.gameId).toBe('game-9');
    });

    it('handles mixed state updates', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameId('test-game');
        result.current.setIsConnected(true);
        result.current.setError('Error');
        result.current.setIsLoading(true);
        result.current.setSelectedHistoryIndex(5);
      });
      
      expect(result.current.gameId).toBe('test-game');
      expect(result.current.isConnected).toBe(true);
      expect(result.current.error).toBe('Error');
      expect(result.current.isLoading).toBe(true);
      expect(result.current.selectedHistoryIndex).toBe(5);
    });
  });

  describe('Edge Cases', () => {
    it('handles setting undefined values', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameId(undefined as any);
        result.current.setError(undefined as any);
      });
      
      expect(result.current.gameId).toBeUndefined();
      expect(result.current.error).toBeUndefined();
    });

    it('handles invalid game settings', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameSettings({
          mode: 'invalid_mode' as any,
          ai_difficulty: 'invalid' as any
        });
      });
      
      expect(result.current.gameSettings.mode).toBe('invalid_mode');
      expect(result.current.gameSettings.ai_difficulty).toBe('invalid');
    });

    it('handles malformed game state', () => {
      const { result } = renderHook(() => useGameStore());
      
      const malformedState = {
        ...mockGameState,
        players: null as any,
        walls: undefined as any
      };
      
      act(() => {
        result.current.setGameState(malformedState);
      });
      
      expect(result.current.gameState?.players).toBeNull();
      expect(result.current.gameState?.walls).toBeUndefined();
    });

    it('handles negative history index', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setSelectedHistoryIndex(-1);
      });
      
      expect(result.current.selectedHistoryIndex).toBe(-1);
    });
  });

  describe('Performance', () => {
    it('does not create unnecessary re-renders', () => {
      let renderCount = 0;
      
      const { result } = renderHook(() => {
        renderCount++;
        return useGameStore();
      });
      
      act(() => {
        result.current.setGameId('test');
        result.current.setGameId('test'); // Same value
      });
      
      // Should not cause extra re-renders for same value
      expect(renderCount).toBeLessThanOrEqual(3); // Initial + 1 change
    });

    it('efficiently handles large game states', () => {
      const { result } = renderHook(() => useGameStore());
      
      const largeHistory = Array.from({ length: 1000 }, (_, i) =>
        generateMockMove(`move${i}`, i % 2 as 0 | 1)
      );
      
      const largeGameState = generateMockGameState({
        move_history: largeHistory
      });
      
      const start = performance.now();
      
      act(() => {
        result.current.setGameState(largeGameState);
      });
      
      const end = performance.now();
      const updateTime = end - start;
      
      // Should handle large states efficiently (less than 10ms)
      expect(updateTime).toBeLessThan(10);
      expect(result.current.gameState?.move_history).toHaveLength(1000);
    });
  });

  describe('Type Safety', () => {
    it('enforces correct types for game state', () => {
      const { result } = renderHook(() => useGameStore());
      
      const typedGameState = {
        ...mockGameState,
        current_player: 1 as 0 | 1,
        winner: 0 as 0 | 1
      };
      
      act(() => {
        result.current.setGameState(typedGameState);
      });
      
      expect(typeof result.current.gameState?.current_player).toBe('number');
      expect(typeof result.current.gameState?.winner).toBe('number');
    });

    it('enforces correct types for game settings', () => {
      const { result } = renderHook(() => useGameStore());
      
      act(() => {
        result.current.setGameSettings({
          mode: 'human_vs_ai',
          ai_difficulty: 'expert',
          ai_time_limit: 10000,
          board_size: 9
        });
      });
      
      expect(typeof result.current.gameSettings.mode).toBe('string');
      expect(typeof result.current.gameSettings.ai_difficulty).toBe('string');
      expect(typeof result.current.gameSettings.ai_time_limit).toBe('number');
      expect(typeof result.current.gameSettings.board_size).toBe('number');
    });
  });
});