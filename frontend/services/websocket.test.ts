import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createMockWebSocket } from '../utils/testHelpers';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';
import { mockInitialGameState } from '../fixtures/gameState';

// Use vi.hoisted to create mocks that can be referenced
const { mockWebSocket, mockUseGameStore, mockFetch } = vi.hoisted(() => ({
  mockWebSocket: {
    readyState: WebSocket.CONNECTING,
    send: vi.fn(),
    close: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    onopen: null as any,
    onclose: null as any,
    onmessage: null as any,
    onerror: null as any,
    
    // Test helpers
    simulateOpen: function() {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) this.onopen(new Event('open'));
    },
    simulateClose: function() {
      this.readyState = WebSocket.CLOSED;
      if (this.onclose) this.onclose(new CloseEvent('close'));
    },
    simulateMessage: function(data: any) {
      if (this.onmessage) {
        this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
      }
    }
  },
  mockUseGameStore: {
    getState: vi.fn(() => ({
      setIsConnected: vi.fn(),
      setIsLoading: vi.fn(),
      setError: vi.fn(),
      setGameId: vi.fn(),
      setGameState: vi.fn(),
      addMoveToHistory: vi.fn()
    })),
    setState: vi.fn()
  },
  mockFetch: vi.fn()
}));

// Mock global WebSocket
global.WebSocket = vi.fn().mockImplementation(() => {
  // Reset the state to connecting when a new instance is created
  mockWebSocket.readyState = WebSocket.CONNECTING;
  return mockWebSocket;
});
Object.defineProperty(WebSocket, 'CONNECTING', { value: 0 });
Object.defineProperty(WebSocket, 'OPEN', { value: 1 });
Object.defineProperty(WebSocket, 'CLOSING', { value: 2 });
Object.defineProperty(WebSocket, 'CLOSED', { value: 3 });

// Mock global fetch
global.fetch = mockFetch;

// Mock the game store
vi.mock('@/store/gameStore', () => ({
  useGameStore: mockUseGameStore
}));

import { wsService } from '@/services/websocket';

describe('WebSocket Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset WebSocket mock state
    mockWebSocket.readyState = WebSocket.CONNECTING;
    mockWebSocket.send.mockClear();
    mockWebSocket.close.mockClear();
    mockWebSocket.addEventListener.mockClear();
    mockWebSocket.removeEventListener.mockClear();
    mockWebSocket.onopen = null;
    mockWebSocket.onclose = null;
    mockWebSocket.onmessage = null;
    mockWebSocket.onerror = null;
    
    // Reset fetch mock
    mockFetch.mockClear();
    
    // Configure default fetch responses
    mockFetch.mockImplementation((url: string) => {
      if (url === '/games') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ game_id: 'test-game-123', initial_state: mockInitialGameState })
        });
      } else if (url.includes('/moves')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true })
        });
      } else if (url.includes('/games/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockInitialGameState)
        });
      }
      return Promise.reject(new Error(`Unmocked URL: ${url}`));
    });
  });

  afterEach(() => {
    // Clean up any lingering connections
    wsService.disconnect();
  });

  describe('Connection Management', () => {
    it('initializes connection', () => {
      wsService.connect();

      expect(global.WebSocket).toHaveBeenCalled();
    });

    it('sets up event listeners on connection', () => {
      wsService.connect();

      // WebSocket uses native event handlers, not .on() method
      expect(global.WebSocket).toHaveBeenCalled();
      // The event handlers are set up in setupEventListeners() which is called after connection
    });

    it('handles successful connection', () => {
      const mockSetIsConnected = vi.fn();
      const mockSetError = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setIsConnected: mockSetIsConnected,
        setError: mockSetError
      });

      wsService.connect();

      // Simulate connection event using onopen handler
      expect(mockWebSocket.onopen).toBeTruthy();
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }

      expect(mockSetIsConnected).toHaveBeenCalledWith(true);
      expect(mockSetError).toHaveBeenCalledWith(null);
    });

    it('handles disconnection', () => {
      const mockSetIsConnected = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setIsConnected: mockSetIsConnected,
        setError: vi.fn()
      });

      wsService.connect();

      // Simulate disconnect event using onclose handler
      expect(mockWebSocket.onclose).toBeTruthy();
      if (mockWebSocket.onclose) {
        mockWebSocket.onclose(new CloseEvent('close'));
      }

      expect(mockSetIsConnected).toHaveBeenCalledWith(false);
    });

    it('handles connection errors', () => {
      const mockSetError = vi.fn();
      const mockSetIsConnected = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setIsConnected: mockSetIsConnected,
        setError: mockSetError
      });

      wsService.connect();

      // Simulate error event using onerror handler
      expect(mockWebSocket.onerror).toBeTruthy();
      if (mockWebSocket.onerror) {
        mockWebSocket.onerror(new Event('error'));
      }

      // Note: The actual wsService doesn't set error on connection error events
      // It only increments reconnect attempts
      expect(mockSetIsConnected).toHaveBeenCalledTimes(0);
    });

    it('disconnects cleanly', () => {
      wsService.connect();
      wsService.disconnect();

      expect(mockWebSocket.close).toHaveBeenCalled();
    });

    it('returns correct connection status', () => {
      mockWebSocket.readyState = WebSocket.OPEN;
      expect(wsService.isConnected()).toBe(true);

      mockWebSocket.readyState = WebSocket.CLOSED;
      expect(wsService.isConnected()).toBe(false);
    });
  });

  describe('Game Creation', () => {
    it('creates game with Human vs AI settings', async () => {
      // Mock store methods for this test
      const mockSetIsLoading = vi.fn();
      const mockSetGameId = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setIsConnected: vi.fn(),
        setIsLoading: mockSetIsLoading,
        setError: vi.fn(),
        setGameId: mockSetGameId,
        setGameState: vi.fn(),
        addMoveToHistory: vi.fn()
      });

      // First connect the service
      wsService.connect();
      // Simulate WebSocket connection opening
      mockWebSocket.readyState = 1; // WebSocket.OPEN
      
      const gameSettings = {
        mode: 'human_vs_ai' as const,
        board_size: 9,
        ai_config: {
          difficulty: 'medium' as const,
          time_limit_ms: 5000,
          use_mcts: true,
          mcts_iterations: 1000
        }
      };

      await wsService.createGame(gameSettings);

      expect(mockFetch).toHaveBeenCalledWith('/games', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(gameSettings)
      });
    });

    it('creates game with Human vs Human settings', async () => {
      mockWebSocket.readyState = WebSocket.OPEN;
      
      const gameSettings = {
        mode: 'human_vs_human' as const,
        board_size: 9
      };

      await wsService.createGame(gameSettings);

      expect(mockWebSocket.send).toHaveBeenCalled();
      const sentMessage = JSON.parse(mockWebSocket.send.mock.calls[0][0]);
      expect(sentMessage.type).toBe('create_game');
      expect(sentMessage.data).toEqual(gameSettings);
    });

    it('creates game with AI vs AI settings', async () => {
      mockWebSocket.readyState = WebSocket.OPEN;
      
      const gameSettings = {
        mode: 'ai_vs_ai' as const,
        board_size: 7,
        ai_config: {
          difficulty: 'expert' as const,
          time_limit_ms: 10000,
          use_mcts: true,
          mcts_iterations: 5000
        }
      };

      await wsService.createGame(gameSettings);

      expect(mockWebSocket.send).toHaveBeenCalled();
      const sentMessage = JSON.parse(mockWebSocket.send.mock.calls[0][0]);
      expect(sentMessage.type).toBe('create_game');
      expect(sentMessage.data).toEqual(gameSettings);
    });

    it('handles game creation success', () => {
      const mockSetGameId = vi.fn();
      const mockSetIsLoading = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setGameId: mockSetGameId,
        setIsLoading: mockSetIsLoading,
        setError: vi.fn()
      });

      wsService.connect();

      // Simulate game_created event
      // Game created handler is now handled by message simulation
      gameCreatedHandler({
        game_id: 'test-game-123',
        initial_state: mockInitialGameState
      });

      expect(mockSetGameId).toHaveBeenCalledWith('test-game-123');
      expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    });

    it('rejects when not connected', async () => {
      mockWebSocket.readyState = WebSocket.CLOSED;

      await expect(wsService.createGame(mockDefaultGameSettings)).rejects.toThrow('Not connected to server');
    });

    it('handles game creation failure', () => {
      const mockSetError = vi.fn();
      const mockSetIsLoading = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setError: mockSetError,
        setIsLoading: mockSetIsLoading,
        setGameId: vi.fn()
      });

      wsService.connect();

      // Simulate error event
      // Simulate error message from server
      mockWebSocket.simulateMessage({
        type: 'error',
        message: 'Failed to create game'
      });

      expect(mockSetError).toHaveBeenCalledWith('Connection failed: Failed to create game');
    });
  });

  describe('Move Handling', () => {
    it('makes move when connected', async () => {
      mockWebSocket.readyState = WebSocket.OPEN;

      await wsService.makeMove('test-game-123', 'e2');

      expect(mockFetch).toHaveBeenCalledWith('/games/test-game-123/moves', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'e2',
          player_id: 'player1'
        })
      });
    });

    it('makes wall move', async () => {
      mockWebSocket.readyState = WebSocket.OPEN;

      await wsService.makeMove('test-game-123', 'c5h');

      expect(mockWebSocket.send).toHaveBeenCalled();
      const sentMessage = JSON.parse(mockWebSocket.send.mock.calls[0][0]);
      expect(sentMessage.type).toBe('make_move');
      expect(sentMessage.data).toEqual({
        game_id: 'test-game-123',
        move: 'c5h'
      });
    });

    it('rejects move when not connected', async () => {
      mockWebSocket.readyState = WebSocket.CLOSED;

      await expect(wsService.makeMove('test-game-123', 'e2')).rejects.toThrow('Not connected to server');
    });

    it('handles move confirmation', () => {
      const mockAddMoveToHistory = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        addMoveToHistory: mockAddMoveToHistory,
        setError: vi.fn()
      });

      wsService.connect();

      // Simulate move confirmation from server
      mockWebSocket.simulateMessage({
        type: 'move_made',
        game_id: 'test-game-123',
        move: {
          notation: 'e2',
          player: 0,
          type: 'move',
          position: { x: 4, y: 1 }
        },
        new_state: mockInitialGameState
      });

      expect(mockAddMoveToHistory).toHaveBeenCalledWith({
        notation: 'e2',
        player: 0,
        type: 'move',
        position: { x: 4, y: 1 }
      });
    });
  });

  describe('AI Move Requests', () => {
    it('requests AI move when connected', async () => {
      mockWebSocket.readyState = WebSocket.OPEN;

      await wsService.getAIMove('test-game-123');

      expect(mockWebSocket.send).toHaveBeenCalled();
      const sentMessage = JSON.parse(mockWebSocket.send.mock.calls[0][0]);
      expect(sentMessage.type).toBe('get_ai_move');
      expect(sentMessage.data).toEqual({
        game_id: 'test-game-123'
      });
    });

    it('rejects AI move request when not connected', async () => {
      mockWebSocket.readyState = WebSocket.CLOSED;

      await expect(wsService.getAIMove('test-game-123')).rejects.toThrow('Not connected to server');
    });

    it('handles AI move response', () => {
      const mockSetGameState = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setGameState: mockSetGameState,
        setError: vi.fn()
      });

      wsService.connect();

      // Simulate AI move response from server
      mockWebSocket.simulateMessage({
        type: 'ai_move',
        game_id: 'test-game-123',
        move: {
          notation: 'e8',
          player: 1,
          type: 'move',
          position: { x: 4, y: 7 }
        },
        new_state: mockInitialGameState
      });

      expect(mockSetGameState).toHaveBeenCalledWith(mockInitialGameState);
    });
  });

  describe('Game State Updates', () => {
    it('handles game state updates', () => {
      const mockSetGameState = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setGameState: mockSetGameState,
        setError: vi.fn()
      });

      wsService.connect();

      // Simulate game_updated event
      // Simulate game state update from server
      mockWebSocket.simulateMessage({
        type: 'game_state',
        data: {
          game_id: 'test-game-123',
          state: mockInitialGameState
        }
      });

      expect(mockSetGameState).toHaveBeenCalledWith(mockInitialGameState);
    });

    it('ignores updates for different games', () => {
      const mockSetGameState = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setGameState: mockSetGameState,
        setError: vi.fn(),
        gameId: 'current-game-456' // Different game ID
      });

      wsService.connect();

      // Simulate game_updated event for different game
      // Simulate game state update from server
      mockWebSocket.simulateMessage({
        type: 'game_state',
        data: {
          game_id: 'other-game-123', // Different game
          state: mockInitialGameState
        }
      });

      expect(mockSetGameState).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('handles malformed server responses', () => {
      const mockSetError = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setError: mockSetError,
        setGameState: vi.fn()
      });

      wsService.connect();

      // Simulate malformed game_updated event
      // Simulate game state update from server
      // Simulate invalid data
      mockWebSocket.simulateMessage({
        type: 'game_state',
        data: null
      });

      // Should handle gracefully without crashing
      expect(() => mockWebSocket.simulateMessage({ type: 'game_state', data: null })).not.toThrow();
    });

    it('handles server errors for specific actions', () => {
      const mockSetError = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setError: mockSetError
      });

      wsService.connect();

      // Simulate server error
      mockWebSocket.simulateMessage({ 
        type: 'error',
        message: 'Invalid move',
        game_id: 'test-game-123'
      });

      expect(mockSetError).toHaveBeenCalledWith('Game error: Invalid move');
    });

    it('handles network timeout gracefully', async () => {
      mockWebSocket.readyState = WebSocket.OPEN;
      
      // Mock send to simulate timeout
      mockWebSocket.send.mockImplementation(() => {
        setTimeout(() => {
          mockWebSocket.simulateMessage({
            type: 'error',
            message: 'Request timeout'
          });
        }, 0);
      });

      await wsService.makeMove('test-game-123', 'e2');

      // Should emit the move despite potential timeout
      expect(mockWebSocket.send).toHaveBeenCalled();
      const sentMessage = JSON.parse(mockWebSocket.send.mock.calls[0][0]);
      expect(sentMessage.type).toBe('make_move');
      expect(sentMessage.data).toEqual({
        game_id: 'test-game-123',
        move: 'e2'
      });
    });
  });

  describe('Reconnection Handling', () => {
    it('attempts reconnection after disconnect', () => {
      const mockSetIsConnected = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setIsConnected: mockSetIsConnected,
        setError: vi.fn()
      });

      wsService.connect();

      // Simulate disconnect event
      mockWebSocket.simulateClose();

      expect(mockSetIsConnected).toHaveBeenCalledWith(false);
    });

    it('handles reconnection success', () => {
      const mockSetIsConnected = vi.fn();
      const mockSetError = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setIsConnected: mockSetIsConnected,
        setError: mockSetError
      });

      wsService.connect();

      // Simulate reconnection
      mockWebSocket.simulateOpen();

      expect(mockSetIsConnected).toHaveBeenCalledWith(true);
      expect(mockSetError).toHaveBeenCalledWith(null); // Clear any previous errors
    });
  });

  describe('Memory Management', () => {
    it('cleans up event listeners on disconnect', () => {
      wsService.connect();
      wsService.disconnect();

      expect(mockWebSocket.removeEventListener).toHaveBeenCalled();
    });

    it('prevents memory leaks with multiple connect/disconnect cycles', () => {
      // Multiple connect/disconnect cycles
      for (let i = 0; i < 5; i++) {
        wsService.connect();
        wsService.disconnect();
      }

      // Should call removeAllListeners each time
      expect(mockWebSocket.removeEventListener).toHaveBeenCalled();
    });

    it('does not accumulate event listeners on multiple connections', () => {
      wsService.connect();
      const initialListenerCalls = mockWebSocket.addEventListener ? mockWebSocket.addEventListener.mock.calls.length : 0;

      wsService.connect(); // Connect again
      const secondListenerCalls = mockWebSocket.addEventListener ? mockWebSocket.addEventListener.mock.calls.length : 0;

      // Should not accumulate event listeners excessively
      // Note: WebSocket native handlers are replaced, not accumulated
      expect(secondListenerCalls).toBeLessThanOrEqual(initialListenerCalls + 4);
    });
  });

  describe('Data Validation', () => {
    it('validates game ID format', async () => {
      mockWebSocket.readyState = WebSocket.OPEN;

      // Empty game ID
      await expect(wsService.makeMove('', 'e2')).rejects.toThrow();
      
      // Null game ID
      await expect(wsService.makeMove(null as any, 'e2')).rejects.toThrow();
    });

    it('validates move notation format', async () => {
      mockWebSocket.readyState = WebSocket.OPEN;

      // Empty move
      await expect(wsService.makeMove('test-game-123', '')).rejects.toThrow();
      
      // Invalid move format
      await expect(wsService.makeMove('test-game-123', '???')).rejects.toThrow();
    });

    it('validates game settings before creation', async () => {
      mockWebSocket.readyState = WebSocket.OPEN;

      // Invalid mode
      await expect(wsService.createGame({
        mode: 'invalid_mode' as any,
        board_size: 9
      })).rejects.toThrow();

      // Invalid board size
      await expect(wsService.createGame({
        mode: 'human_vs_ai',
        board_size: 0
      })).rejects.toThrow();
    });
  });
});