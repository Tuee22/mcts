import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock the game store first with vi.hoisted
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  const store = {
    gameId: null,
    gameState: null,
    gameSettings: { mode: 'human_vs_ai', ai_difficulty: 'medium', ai_time_limit: 5000, board_size: 9 },
    isConnected: false,
    isLoading: false,
    error: null,
    selectedHistoryIndex: null,
    setGameId: vi.fn(),
    setGameState: vi.fn(),
    setGameSettings: vi.fn(),
    setIsConnected: vi.fn(),
    setIsLoading: vi.fn(),
    setError: vi.fn(),
    setSelectedHistoryIndex: vi.fn(),
    addMoveToHistory: vi.fn(),
    reset: vi.fn()
  };

  const useGameStoreMock = vi.fn(() => store);
  useGameStoreMock.getState = vi.fn(() => store);
  
  return {
    mockGameStore: store,
    mockUseGameStore: useGameStoreMock
  };
});

vi.mock('@/store/gameStore', () => ({
  useGameStore: mockUseGameStore
}));

// Import test fixtures first
import { createMockWebSocket, createMockFetch } from '../fixtures/mocks';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';
import { mockInitialGameState } from '../fixtures/gameState';

// Create WebSocket mock instance
const mockSocket = createMockWebSocket();
mockSocket._testId = 'enhanced-websocket-instance';

global.WebSocket = vi.fn().mockImplementation((url) => {
  mockSocket.url = url; // Track the URL that was used
  return mockSocket;
});

// Define WebSocket constants
Object.defineProperty(WebSocket, 'CONNECTING', { value: 0 });
Object.defineProperty(WebSocket, 'OPEN', { value: 1 });
Object.defineProperty(WebSocket, 'CLOSING', { value: 2 });
Object.defineProperty(WebSocket, 'CLOSED', { value: 3 });

// Mock fetch globally
const mockFetch = createMockFetch();
global.fetch = mockFetch;

// Import the service after all mocks are set up
import { wsService } from '@/services/websocket';

describe.skip('WebSocket Service Enhanced Tests', () => {
  let consoleErrorSpy: any;
  
  beforeEach(() => {
    vi.clearAllMocks();
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    // Reset WebSocket service state
    wsService.disconnect();
    
    // Reset WebSocket mock state
    mockSocket.reset();
    mockSocket.url = '';
    
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
    wsService.disconnect();
    consoleErrorSpy.mockRestore();
  });

  describe('connectToGame Method (Previously Untested)', () => {
    it('should connect to game-specific WebSocket endpoint', () => {
      const gameId = 'test-game-123';

      wsService.connectToGame(gameId);

      // Force the service to use our mock socket
      (wsService as any).socket = mockSocket;

      expect(global.WebSocket).toHaveBeenCalledWith(
        expect.stringContaining(`/games/${gameId}/ws`)
      );
      expect(mockSocket.url).toContain(`/games/${gameId}/ws`);
    });

    it('should close existing connection before connecting to new game', () => {
      // First establish a general connection
      wsService.connect();
      const firstSocket = mockSocket;
      
      // Mock that the first socket is open
      firstSocket.readyState = WebSocket.OPEN;
      
      // Connect to a specific game
      wsService.connectToGame('game-123');
      
      expect(firstSocket.close).toHaveBeenCalled();
    });

    it('should use HTTPS protocol when page is served over HTTPS', () => {
      // Mock HTTPS location
      Object.defineProperty(window, 'location', {
        value: { protocol: 'https:', host: 'example.com' },
        writable: true
      });
      
      wsService.connectToGame('game-123');
      
      expect(mockSocket.url).toMatch(/^wss:/);
      expect(mockSocket.url).toContain('example.com/games/game-123/ws');
    });

    it('should use HTTP protocol when page is served over HTTP', () => {
      // Mock HTTP location
      Object.defineProperty(window, 'location', {
        value: { protocol: 'http:', host: 'localhost:3000' },
        writable: true
      });
      
      wsService.connectToGame('game-123');
      
      expect(mockSocket.url).toMatch(/^ws:/);
      expect(mockSocket.url).toContain('localhost:3000/games/game-123/ws');
    });

    it('should handle connection errors gracefully when connecting to game', () => {
      // Mock WebSocket constructor to throw
      global.WebSocket = vi.fn().mockImplementation(() => {
        throw new Error('Network error');
      });
      
      wsService.connectToGame('game-123');
      
      expect(mockGameStore.setError).toHaveBeenCalledWith('Failed to connect to game');
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    it('should setup event listeners for game-specific connection', () => {
      wsService.connectToGame('game-123');
      
      // Verify event listeners are set up
      expect(mockSocket.onopen).toBeTypeOf('function');
      expect(mockSocket.onclose).toBeTypeOf('function');
      expect(mockSocket.onerror).toBeTypeOf('function');
      expect(mockSocket.onmessage).toBeTypeOf('function');
    });
  });

  describe('Reconnection Logic', () => {
    it('should track reconnection attempts', () => {
      wsService.connect();
      
      // Simulate connection errors
      for (let i = 0; i < 3; i++) {
        mockSocket.simulateError(new Error('Connection failed'));
      }
      
      // Should still be attempting to reconnect (max is 5)
      expect(mockGameStore.setIsConnected).not.toHaveBeenCalledWith(false);
    });

    it('should stop reconnecting after max attempts', () => {
      wsService.connect();
      
      // Simulate 5 connection errors (max attempts)
      for (let i = 0; i < 5; i++) {
        mockSocket.simulateError(new Error('Connection failed'));
      }
      
      // Should give up and mark as disconnected
      expect(mockGameStore.setIsConnected).toHaveBeenCalledWith(false);
    });

    it('should reset reconnection attempts on successful connection', () => {
      wsService.connect();
      
      // Fail a few times
      mockSocket.simulateError(new Error('Temp failure'));
      mockSocket.simulateError(new Error('Temp failure'));
      
      // Then succeed
      mockSocket.simulateOpen();
      
      // Should reset attempts and allow future reconnections
      expect(mockGameStore.setIsConnected).toHaveBeenCalledWith(true);
      
      // Simulate errors again - should not immediately disconnect
      mockSocket.simulateError(new Error('New failure'));
      expect(mockGameStore.setIsConnected).toHaveBeenCalledTimes(1); // Only the success call
    });
  });

  describe('WebSocket Message Handling', () => {
    beforeEach(() => {
      wsService.connect();
      mockSocket.simulateOpen();
    });

    it('should handle "connect" message type', () => {
      const connectMessage = { type: 'connect' };
      
      mockSocket.simulateMessage(connectMessage);
      
      expect(mockGameStore.setIsConnected).toHaveBeenCalledWith(true);
      expect(mockGameStore.setError).toHaveBeenCalledWith(null);
    });

    it('should handle "game_created" message type', () => {
      const gameCreatedMessage = { 
        type: 'game_created', 
        game_id: 'new-game-456' 
      };
      
      mockSocket.simulateMessage(gameCreatedMessage);
      
      expect(mockGameStore.setGameId).toHaveBeenCalledWith('new-game-456');
      expect(mockGameStore.setIsLoading).toHaveBeenCalledWith(false);
    });

    it('should handle "pong" message type', () => {
      const pongMessage = { type: 'pong' };
      
      // Should not throw or cause side effects
      expect(() => mockSocket.simulateMessage(pongMessage)).not.toThrow();
    });

    it('should handle "game_state" message type', () => {
      const gameStateMessage = { 
        type: 'game_state', 
        data: {
          board_size: 9,
          current_turn: 1,
          player1: { walls_remaining: 10 },
          player2: { walls_remaining: 10 },
          board_display: "simple board",
          legal_moves: [],
          move_count: 0
        }
      };
      
      mockSocket.simulateMessage(gameStateMessage);
      
      expect(mockGameStore.setGameState).toHaveBeenCalled();
    });

    it('should handle "move" message type and request game state update', () => {
      const moveMessage = { 
        type: 'move', 
        data: { game_id: 'game-123' }
      };
      
      mockSocket.simulateMessage(moveMessage);
      
      // Should trigger a game state fetch
      expect(mockFetch).toHaveBeenCalledWith('/games/game-123');
    });

    it('should handle "game_ended" message type', () => {
      const gameEndedMessage = { 
        type: 'game_ended', 
        data: {
          board_size: 9,
          current_turn: 1,
          player1: { walls_remaining: 8 },
          player2: { walls_remaining: 7 },
          winner: 1,
          board_display: "final board",
          legal_moves: [],
          move_count: 25
        }
      };
      
      mockSocket.simulateMessage(gameEndedMessage);
      
      expect(mockGameStore.setGameState).toHaveBeenCalled();
    });

    it('should handle "player_connected" and "player_disconnected" messages gracefully', () => {
      const playerConnectedMessage = { type: 'player_connected', player_id: 'player-1' };
      const playerDisconnectedMessage = { type: 'player_disconnected', player_id: 'player-2' };
      
      // Should not throw
      expect(() => mockSocket.simulateMessage(playerConnectedMessage)).not.toThrow();
      expect(() => mockSocket.simulateMessage(playerDisconnectedMessage)).not.toThrow();
    });

    it('should handle unknown message types gracefully', () => {
      const unknownMessage = { type: 'unknown_type', data: 'random data' };
      
      expect(() => mockSocket.simulateMessage(unknownMessage)).not.toThrow();
    });

    it('should handle malformed JSON messages', () => {
      // Simulate malformed message
      const malformedEvent = { data: 'invalid json {' };
      
      if (mockSocket.onmessage) {
        mockSocket.onmessage(malformedEvent as MessageEvent);
      }
      
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Error parsing WebSocket message:', 
        expect.any(Error)
      );
    });

    it('should handle empty message data', () => {
      const emptyMessage = { type: 'game_state', data: null };
      
      expect(() => mockSocket.simulateMessage(emptyMessage)).not.toThrow();
    });
  });

  describe('API Response Transformation', () => {
    beforeEach(() => {
      wsService.connect();
      mockSocket.simulateOpen();
    });

    it('should transform API response with board display', () => {
      const apiResponse = {
        board_size: 7,
        current_turn: 2,
        player1: { walls_remaining: 8 },
        player2: { walls_remaining: 9 },
        board_display: "sample board display",
        legal_moves: ['e2', 'e4'],
        move_count: 3,
        winner: null
      };
      
      const gameStateMessage = { type: 'game_state', data: apiResponse };
      mockSocket.simulateMessage(gameStateMessage);
      
      expect(mockGameStore.setGameState).toHaveBeenCalledWith(
        expect.objectContaining({
          board_size: 7,
          current_player: 1, // current_turn 2 -> current_player 1 (0-based)
          walls_remaining: [8, 9],
          legal_moves: ['e2', 'e4'],
          winner: null
        })
      );
    });

    it('should handle API response without board display', () => {
      const apiResponse = {
        board_size: 5,
        current_turn: 1,
        player1: { walls_remaining: 10 },
        player2: { walls_remaining: 10 },
        legal_moves: [],
        move_count: 0
      };
      
      const gameStateMessage = { type: 'game_state', data: apiResponse };
      mockSocket.simulateMessage(gameStateMessage);
      
      expect(mockGameStore.setGameState).toHaveBeenCalledWith(
        expect.objectContaining({
          board_size: 5,
          current_player: 0,
          players: [
            { x: 2, y: 4 }, // Center bottom for 5x5 board
            { x: 2, y: 0 }  // Center top for 5x5 board
          ]
        })
      );
    });

    it('should handle malformed API response gracefully', () => {
      const malformedResponse = {
        // Missing required fields
        current_turn: "invalid",
        player1: "not an object"
      };
      
      const gameStateMessage = { type: 'game_state', data: malformedResponse };
      
      mockSocket.simulateMessage(gameStateMessage);
      
      // Should handle gracefully, possibly setting null gameState
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    it('should handle API response with winner', () => {
      const apiResponse = {
        board_size: 9,
        current_turn: 1,
        player1: { walls_remaining: 5 },
        player2: { walls_remaining: 7 },
        winner: 0, // Player 1 wins
        move_count: 47
      };
      
      const gameEndedMessage = { type: 'game_ended', data: apiResponse };
      mockSocket.simulateMessage(gameEndedMessage);
      
      expect(mockGameStore.setGameState).toHaveBeenCalledWith(
        expect.objectContaining({
          winner: 0
        })
      );
    });
  });

  describe('Connection State Management', () => {
    it('should track connection state correctly during connect flow', () => {
      // Start disconnected
      expect(mockGameStore.isConnected).toBe(false);
      
      wsService.connect();
      
      // Should still be disconnected until onopen fires
      expect(mockGameStore.setIsConnected).not.toHaveBeenCalledWith(true);
      
      mockSocket.simulateOpen();
      
      // Now should be connected
      expect(mockGameStore.setIsConnected).toHaveBeenCalledWith(true);
    });

    it('should mark as disconnected when socket closes', () => {
      wsService.connect();
      mockSocket.simulateOpen();
      
      // Verify connected
      expect(mockGameStore.setIsConnected).toHaveBeenCalledWith(true);
      
      mockSocket.simulateClose();
      
      expect(mockGameStore.setIsConnected).toHaveBeenCalledWith(false);
    });

    it('should not attempt connection if already open', () => {
      wsService.connect();
      mockSocket.readyState = WebSocket.OPEN;
      
      const connectionCountBefore = (global.WebSocket as any).mock.calls.length;
      
      // Try to connect again
      wsService.connect();
      
      const connectionCountAfter = (global.WebSocket as any).mock.calls.length;
      
      // Should not create a new connection
      expect(connectionCountAfter).toBe(connectionCountBefore);
    });
  });

  describe('Disconnect Method', () => {
    it('should close socket and reset internal state', () => {
      wsService.connect();
      mockSocket.simulateOpen();
      
      wsService.disconnect();
      
      expect(mockSocket.close).toHaveBeenCalled();
    });

    it('should handle disconnect when no socket exists', () => {
      // Should not throw
      expect(() => wsService.disconnect()).not.toThrow();
    });

    it('should handle disconnect multiple times', () => {
      wsService.connect();
      
      wsService.disconnect();
      wsService.disconnect();
      
      // Should not throw on subsequent calls
      expect(() => wsService.disconnect()).not.toThrow();
    });
  });

  describe('Connection During Reset (Disconnection Bug Context)', () => {
    it('should maintain WebSocket connection when game store is reset', () => {
      wsService.connect();
      mockSocket.simulateOpen();
      
      // Verify connected
      expect(mockGameStore.setIsConnected).toHaveBeenCalledWith(true);
      
      // Reset game store (this is what triggers the disconnection bug)
      mockGameStore.reset();
      
      // WebSocket should still be open (this tests the service independence)
      expect(mockSocket.close).not.toHaveBeenCalled();
      expect(mockSocket.readyState).toBe(WebSocket.OPEN);
    });

    it('should allow game creation after store reset without reconnection', () => {
      wsService.connect();
      mockSocket.simulateOpen();
      
      // Reset store
      mockGameStore.reset();
      
      // Should still be able to create game without new connection
      const createGamePromise = wsService.createGame(mockDefaultGameSettings);
      
      expect(mockFetch).toHaveBeenCalledWith('/games', expect.any(Object));
      expect(createGamePromise).toBeDefined();
    });
  });
});