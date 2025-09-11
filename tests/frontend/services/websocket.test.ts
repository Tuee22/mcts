import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createMockWebSocket, createMockGameStore, createMockFetch } from '../fixtures/mocks';
import { mockDefaultGameSettings } from '../fixtures/gameSettings';
import { mockInitialGameState } from '../fixtures/gameState';

// Use vi.hoisted to create properly scoped mocks
const { mockGameStore, mockUseGameStore } = vi.hoisted(() => {
  const gameStore = createMockGameStore({
    setIsConnected: vi.fn(),
    setIsLoading: vi.fn(),
    setError: vi.fn(),
    setGameId: vi.fn(),
    setGameState: vi.fn(),
    addMoveToHistory: vi.fn()
  });

  // Create a proper Zustand-style mock
  const useGameStoreMock = vi.fn(() => gameStore);
  useGameStoreMock.getState = vi.fn(() => gameStore);
  
  return {
    mockGameStore: gameStore,
    mockUseGameStore: useGameStoreMock
  };
});

vi.mock('@/store/gameStore', () => ({
  useGameStore: mockUseGameStore
}));

// Mock WebSocket globally
const mockSocket = createMockWebSocket();
global.WebSocket = vi.fn().mockImplementation(() => mockSocket);
Object.defineProperty(WebSocket, 'CONNECTING', { value: 0 });
Object.defineProperty(WebSocket, 'OPEN', { value: 1 });
Object.defineProperty(WebSocket, 'CLOSING', { value: 2 });
Object.defineProperty(WebSocket, 'CLOSED', { value: 3 });

// Mock fetch globally
const mockFetch = createMockFetch();
global.fetch = mockFetch;

import { wsService } from '@/services/websocket';

describe('WebSocket Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset WebSocket mock state
    mockSocket.reset();
    
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

    it('handles successful connection', () => {
      wsService.connect();

      // Simulate connection event using our mock helper
      mockSocket.simulateOpen();

      expect(mockGameStore.setIsConnected).toHaveBeenCalledWith(true);
    });

    it('handles disconnection', () => {
      wsService.connect();

      // Simulate disconnect event
      mockSocket.simulateClose();

      expect(mockGameStore.setIsConnected).toHaveBeenCalledWith(false);
    });

    it('disconnects cleanly', () => {
      wsService.connect();
      wsService.disconnect();

      expect(mockSocket.close).toHaveBeenCalled();
    });

    it('reports connection status correctly', () => {
      // Initially disconnected
      expect(wsService.isConnected()).toBe(false);

      wsService.connect();
      mockSocket.simulateOpen();

      expect(wsService.isConnected()).toBe(true);
    });
  });

  describe('Game Creation', () => {
    it('creates game with default settings', async () => {
      const result = await wsService.createGame(mockDefaultGameSettings);

      expect(mockFetch).toHaveBeenCalledWith('/games', expect.any(Object));
      expect(result).toEqual({ gameId: 'test-game-123' });
    });

    it('rejects when not connected', async () => {
      // Mock as disconnected
      mockSocket.readyState = WebSocket.CLOSED;
      
      await expect(wsService.createGame(mockDefaultGameSettings))
        .rejects.toThrow('WebSocket not connected');
    });

    it('handles game creation failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Server error'));

      await expect(wsService.createGame(mockDefaultGameSettings))
        .rejects.toThrow('Server error');
    });
  });

  describe('Move Handling', () => {
    it('makes move when connected', async () => {
      mockSocket.readyState = WebSocket.OPEN;

      await wsService.makeMove('test-game-123', 'e2e4');

      expect(mockFetch).toHaveBeenCalledWith('/games/test-game-123/moves', expect.any(Object));
    });

    it('rejects move when not connected', async () => {
      mockSocket.readyState = WebSocket.CLOSED;

      await expect(wsService.makeMove('test-game-123', 'e2e4'))
        .rejects.toThrow('WebSocket not connected');
    });
  });

  describe('Error Handling', () => {
    it('handles network timeout gracefully', async () => {
      mockSocket.readyState = WebSocket.OPEN;
      mockFetch.mockRejectedValueOnce(new Error('Network timeout'));

      await expect(wsService.makeMove('test-game-123', 'e2e4'))
        .rejects.toThrow('Network timeout');
    });
  });
});