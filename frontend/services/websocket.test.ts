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

      // Simulate disconnect event
      const disconnectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'disconnect')[1];
      disconnectHandler('transport close');

      expect(mockSetIsConnected).toHaveBeenCalledWith(false);
    });

    it('handles connection errors', () => {
      const mockSetError = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setIsConnected: vi.fn(),
        setError: mockSetError
      });

      wsService.connect();

      // Simulate error event
      const errorHandler = mockSocket.on.mock.calls.find(call => call[0] === 'error')[1];
      errorHandler(new Error('Connection failed'));

      expect(mockSetError).toHaveBeenCalledWith('Connection failed: Connection failed');
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
      mockSocket.connected = true;
      
      const gameSettings = {
        mode: 'human_vs_human' as const,
        board_size: 9
      };

      await wsService.createGame(gameSettings);

      expect(mockSocket.emit).toHaveBeenCalledWith('create_game', gameSettings);
    });

    it('creates game with AI vs AI settings', async () => {
      mockSocket.connected = true;
      
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

      expect(mockSocket.emit).toHaveBeenCalledWith('create_game', gameSettings);
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
      const gameCreatedHandler = mockSocket.on.mock.calls.find(call => call[0] === 'game_created')[1];
      gameCreatedHandler({
        game_id: 'test-game-123',
        initial_state: mockInitialGameState
      });

      expect(mockSetGameId).toHaveBeenCalledWith('test-game-123');
      expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    });

    it('rejects when not connected', async () => {
      mockSocket.connected = false;

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
      const errorHandler = mockSocket.on.mock.calls.find(call => call[0] === 'error')[1];
      errorHandler(new Error('Failed to create game'));

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
      mockSocket.connected = true;

      await wsService.makeMove('test-game-123', 'c5h');

      expect(mockSocket.emit).toHaveBeenCalledWith('make_move', {
        game_id: 'test-game-123',
        move: 'c5h'
      });
    });

    it('rejects move when not connected', async () => {
      mockSocket.connected = false;

      await expect(wsService.makeMove('test-game-123', 'e2')).rejects.toThrow('Not connected to server');
    });

    it('handles move confirmation', () => {
      const mockAddMoveToHistory = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        addMoveToHistory: mockAddMoveToHistory,
        setError: vi.fn()
      });

      wsService.connect();

      // Simulate move_made event
      const moveMadeHandler = mockSocket.on.mock.calls.find(call => call[0] === 'move_made')[1];
      moveMadeHandler({
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
      mockSocket.connected = true;

      await wsService.getAIMove('test-game-123');

      expect(mockSocket.emit).toHaveBeenCalledWith('get_ai_move', {
        game_id: 'test-game-123'
      });
    });

    it('rejects AI move request when not connected', async () => {
      mockSocket.connected = false;

      await expect(wsService.getAIMove('test-game-123')).rejects.toThrow('Not connected to server');
    });

    it('handles AI move response', () => {
      const mockSetGameState = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setGameState: mockSetGameState,
        setError: vi.fn()
      });

      wsService.connect();

      // Simulate ai_move event
      const aiMoveHandler = mockSocket.on.mock.calls.find(call => call[0] === 'ai_move')[1];
      aiMoveHandler({
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
      const gameUpdatedHandler = mockSocket.on.mock.calls.find(call => call[0] === 'game_updated')[1];
      gameUpdatedHandler({
        game_id: 'test-game-123',
        state: mockInitialGameState
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
      const gameUpdatedHandler = mockSocket.on.mock.calls.find(call => call[0] === 'game_updated')[1];
      gameUpdatedHandler({
        game_id: 'other-game-123', // Different game
        state: mockInitialGameState
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
      const gameUpdatedHandler = mockSocket.on.mock.calls.find(call => call[0] === 'game_updated')[1];
      gameUpdatedHandler(null); // Invalid data

      // Should handle gracefully without crashing
      expect(() => gameUpdatedHandler(null)).not.toThrow();
    });

    it('handles server errors for specific actions', () => {
      const mockSetError = vi.fn();
      mockUseGameStore.getState.mockReturnValue({
        setError: mockSetError
      });

      wsService.connect();

      // Simulate server error
      const errorHandler = mockSocket.on.mock.calls.find(call => call[0] === 'error')[1];
      errorHandler({ 
        type: 'game_error', 
        message: 'Invalid move',
        game_id: 'test-game-123'
      });

      expect(mockSetError).toHaveBeenCalledWith('Game error: Invalid move');
    });

    it('handles network timeout gracefully', async () => {
      mockSocket.connected = true;
      
      // Mock emit to simulate timeout
      mockSocket.emit.mockImplementation(() => {
        setTimeout(() => {
          const errorHandler = mockSocket.on.mock.calls.find(call => call[0] === 'error')[1];
          if (errorHandler) {
            errorHandler(new Error('Request timeout'));
          }
        }, 0);
      });

      await wsService.makeMove('test-game-123', 'e2');

      // Should emit the move despite potential timeout
      expect(mockSocket.emit).toHaveBeenCalledWith('make_move', {
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

      // Simulate disconnect
      const disconnectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'disconnect')[1];
      disconnectHandler('transport error');

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
      const connectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'connect')[1];
      connectHandler();

      expect(mockSetIsConnected).toHaveBeenCalledWith(true);
      expect(mockSetError).toHaveBeenCalledWith(null); // Clear any previous errors
    });
  });

  describe('Memory Management', () => {
    it('cleans up event listeners on disconnect', () => {
      wsService.connect();
      wsService.disconnect();

      expect(mockSocket.removeAllListeners).toHaveBeenCalled();
    });

    it('prevents memory leaks with multiple connect/disconnect cycles', () => {
      // Multiple connect/disconnect cycles
      for (let i = 0; i < 5; i++) {
        wsService.connect();
        wsService.disconnect();
      }

      // Should call removeAllListeners each time
      expect(mockSocket.removeAllListeners).toHaveBeenCalledTimes(5);
    });

    it('does not accumulate event listeners on multiple connections', () => {
      wsService.connect();
      const initialOnCalls = mockSocket.on.mock.calls.length;

      wsService.connect(); // Connect again
      const secondOnCalls = mockSocket.on.mock.calls.length;

      // Should not double the event listeners
      expect(secondOnCalls).toBeLessThanOrEqual(initialOnCalls * 2);
    });
  });

  describe('Data Validation', () => {
    it('validates game ID format', async () => {
      mockSocket.connected = true;

      // Empty game ID
      await expect(wsService.makeMove('', 'e2')).rejects.toThrow();
      
      // Null game ID
      await expect(wsService.makeMove(null as any, 'e2')).rejects.toThrow();
    });

    it('validates move notation format', async () => {
      mockSocket.connected = true;

      // Empty move
      await expect(wsService.makeMove('test-game-123', '')).rejects.toThrow();
      
      // Invalid move format
      await expect(wsService.makeMove('test-game-123', '???')).rejects.toThrow();
    });

    it('validates game settings before creation', async () => {
      mockSocket.connected = true;

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