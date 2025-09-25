/**
 * WebSocket Service Connection Tests
 *
 * Integration tests for WebSocket service connection handling, message queuing,
 * and reconnection logic that could affect E2E test stability.
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { wsService } from '../../src/services/websocket';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  private messageQueue: string[] = [];
  private shouldFailConnection = false;
  private shouldFailSend = false;

  constructor(url: string) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;

    // Simulate connection process
    setTimeout(() => {
      if (this.shouldFailConnection) {
        this.readyState = MockWebSocket.CLOSED;
        this.onerror?.(new Event('error'));
      } else {
        this.readyState = MockWebSocket.OPEN;
        this.onopen?.(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    if (this.shouldFailSend) {
      throw new Error('WebSocket send failed');
    }
    this.messageQueue.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: 1000, reason: 'Normal closure' }));
  }

  // Test helpers
  simulateMessage(message: string) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: message }));
    }
  }

  getLastMessage(): string | null {
    return this.messageQueue[this.messageQueue.length - 1] || null;
  }

  getAllMessages(): string[] {
    return [...this.messageQueue];
  }

  simulateConnectionFailure() {
    this.shouldFailConnection = true;
  }

  simulateSendFailure() {
    this.shouldFailSend = true;
  }

  simulateDisconnection() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: 1006, reason: 'Connection lost' }));
  }
}

// Global mock WebSocket reference
let mockWebSocketInstance: MockWebSocket | null = null;

// Mock WebSocket constructor
const MockWebSocketConstructor = vi.fn((url: string) => {
  mockWebSocketInstance = new MockWebSocket(url);
  return mockWebSocketInstance;
});

// Setup WebSocket mock
Object.assign(MockWebSocketConstructor, {
  CONNECTING: MockWebSocket.CONNECTING,
  OPEN: MockWebSocket.OPEN,
  CLOSING: MockWebSocket.CLOSING,
  CLOSED: MockWebSocket.CLOSED
});

(global as any).WebSocket = MockWebSocketConstructor;

describe('WebSocket Service Connection Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWebSocketInstance = null;
    // Reset WebSocket service state
    wsService.disconnect();
  });

  afterEach(() => {
    wsService.disconnect();
  });

  describe('Connection establishment', () => {
    it('should establish connection successfully', async () => {
      const connectPromise = wsService.connect('ws://localhost:8000/ws');

      // Wait for connection to complete
      await new Promise(resolve => setTimeout(resolve, 20));

      expect(MockWebSocketConstructor).toHaveBeenCalledWith('ws://localhost:8000/ws');
      expect(wsService.isConnected()).toBe(true);
    });

    it('should handle connection failure', async () => {
      // Setup failure before connection attempt
      const originalConstructor = MockWebSocketConstructor;
      (global as any).WebSocket = vi.fn((url: string) => {
        const instance = new MockWebSocket(url);
        instance.simulateConnectionFailure();
        mockWebSocketInstance = instance;
        return instance;
      });

      const connectPromise = wsService.connect('ws://localhost:8000/ws');

      // Wait for connection attempt to complete
      await new Promise(resolve => setTimeout(resolve, 20));

      expect(wsService.isConnected()).toBe(false);

      // Restore original constructor
      (global as any).WebSocket = originalConstructor;
    });

    it('should handle multiple connection attempts', async () => {
      // First connection
      await wsService.connect('ws://localhost:8000/ws');
      const firstInstance = mockWebSocketInstance;

      // Second connection attempt should disconnect first
      await wsService.connect('ws://localhost:8000/ws');
      const secondInstance = mockWebSocketInstance;

      expect(firstInstance).not.toBe(secondInstance);
      expect(wsService.isConnected()).toBe(true);
    });
  });

  describe('Message handling', () => {
    beforeEach(async () => {
      await wsService.connect('ws://localhost:8000/ws');
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    it('should send messages when connected', () => {
      const message = { type: 'ping', data: {} };

      wsService.sendMessage(message);

      expect(mockWebSocketInstance?.getLastMessage()).toBe(JSON.stringify(message));
    });

    it('should queue messages when disconnected', async () => {
      // Disconnect
      wsService.disconnect();

      const message = { type: 'queued_message', data: {} };
      wsService.sendMessage(message);

      // Reconnect
      await wsService.connect('ws://localhost:8000/ws');
      await new Promise(resolve => setTimeout(resolve, 20));

      // Queued message should be sent
      expect(mockWebSocketInstance?.getLastMessage()).toBe(JSON.stringify(message));
    });

    it('should handle incoming messages', () => {
      const messageHandler = vi.fn();
      wsService.onMessage(messageHandler);

      const message = { type: 'game_update', data: { game_id: 'test' } };
      mockWebSocketInstance?.simulateMessage(JSON.stringify(message));

      expect(messageHandler).toHaveBeenCalledWith(message);
    });

    it('should handle malformed incoming messages', () => {
      const messageHandler = vi.fn();
      const errorHandler = vi.fn();
      wsService.onMessage(messageHandler);
      wsService.onError(errorHandler);

      // Send malformed JSON
      mockWebSocketInstance?.simulateMessage('invalid json {');

      expect(messageHandler).not.toHaveBeenCalled();
      expect(errorHandler).toHaveBeenCalled();
    });
  });

  describe('Reconnection logic', () => {
    it('should attempt reconnection after disconnect', async () => {
      await wsService.connect('ws://localhost:8000/ws');
      await new Promise(resolve => setTimeout(resolve, 20));

      // Simulate unexpected disconnection
      mockWebSocketInstance?.simulateDisconnection();

      // Wait for reconnection attempt
      await new Promise(resolve => setTimeout(resolve, 100));

      // Should have attempted to reconnect
      expect(MockWebSocketConstructor).toHaveBeenCalledTimes(2);
    });

    it('should back off exponentially on repeated failures', async () => {
      let connectionAttempts = 0;
      (global as any).WebSocket = vi.fn((url: string) => {
        connectionAttempts++;
        const instance = new MockWebSocket(url);
        if (connectionAttempts <= 3) {
          instance.simulateConnectionFailure();
        }
        mockWebSocketInstance = instance;
        return instance;
      });

      await wsService.connect('ws://localhost:8000/ws');

      // Wait for multiple reconnection attempts
      await new Promise(resolve => setTimeout(resolve, 500));

      // Should have made multiple attempts with backoff
      expect(connectionAttempts).toBeGreaterThan(1);
    });

    it('should stop reconnecting after max attempts', async () => {
      (global as any).WebSocket = vi.fn((url: string) => {
        const instance = new MockWebSocket(url);
        instance.simulateConnectionFailure();
        mockWebSocketInstance = instance;
        return instance;
      });

      await wsService.connect('ws://localhost:8000/ws');

      // Wait for all reconnection attempts
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Should eventually stop trying
      expect(wsService.isConnected()).toBe(false);
    });
  });

  describe('Game operation methods', () => {
    beforeEach(async () => {
      await wsService.connect('ws://localhost:8000/ws');
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    it('should create game with correct message format', () => {
      const settings = {
        mode: 'human_vs_human',
        board_size: 9
      };

      wsService.createGame(settings);

      const sentMessage = JSON.parse(mockWebSocketInstance?.getLastMessage() || '{}');
      expect(sentMessage.type).toBe('create_game');
      expect(sentMessage.data).toEqual(settings);
      expect(sentMessage.request_id).toBeDefined();
    });

    it('should make move with correct message format', () => {
      const gameId = 'test-game-123';
      const action = 'move up';

      wsService.makeMove(gameId, action);

      const sentMessage = JSON.parse(mockWebSocketInstance?.getLastMessage() || '{}');
      expect(sentMessage.type).toBe('make_move');
      expect(sentMessage.data).toEqual({
        game_id: gameId,
        action: action
      });
    });

    it('should join game with correct message format', () => {
      const gameId = 'test-game-456';

      wsService.joinGame(gameId);

      const sentMessage = JSON.parse(mockWebSocketInstance?.getLastMessage() || '{}');
      expect(sentMessage.type).toBe('join_game');
      expect(sentMessage.data).toEqual({
        game_id: gameId
      });
    });

    it('should leave game with correct message format', () => {
      const gameId = 'test-game-789';

      wsService.leaveGame(gameId);

      const sentMessage = JSON.parse(mockWebSocketInstance?.getLastMessage() || '{}');
      expect(sentMessage.type).toBe('leave_game');
      expect(sentMessage.data).toEqual({
        game_id: gameId
      });
    });
  });

  describe('Connection state events', () => {
    it('should emit connection events', async () => {
      const connectHandler = vi.fn();
      const disconnectHandler = vi.fn();

      wsService.onConnect(connectHandler);
      wsService.onDisconnect(disconnectHandler);

      await wsService.connect('ws://localhost:8000/ws');
      await new Promise(resolve => setTimeout(resolve, 20));

      expect(connectHandler).toHaveBeenCalled();

      wsService.disconnect();
      expect(disconnectHandler).toHaveBeenCalled();
    });

    it('should provide connection state information', async () => {
      expect(wsService.getConnectionState()).toEqual({
        connected: false,
        connecting: false,
        url: null,
        reconnectAttempts: 0
      });

      await wsService.connect('ws://localhost:8000/ws');
      await new Promise(resolve => setTimeout(resolve, 20));

      const connectedState = wsService.getConnectionState();
      expect(connectedState.connected).toBe(true);
      expect(connectedState.url).toBe('ws://localhost:8000/ws');
    });
  });

  describe('Error handling', () => {
    it('should handle WebSocket send errors', async () => {
      await wsService.connect('ws://localhost:8000/ws');
      await new Promise(resolve => setTimeout(resolve, 20));

      // Setup send failure
      mockWebSocketInstance?.simulateSendFailure();

      const errorHandler = vi.fn();
      wsService.onError(errorHandler);

      wsService.sendMessage({ type: 'test', data: {} });

      expect(errorHandler).toHaveBeenCalled();
    });

    it('should handle connection errors gracefully', async () => {
      const errorHandler = vi.fn();
      wsService.onError(errorHandler);

      // Setup connection failure
      (global as any).WebSocket = vi.fn((url: string) => {
        const instance = new MockWebSocket(url);
        setTimeout(() => {
          instance.onerror?.(new Event('error'));
        }, 10);
        mockWebSocketInstance = instance;
        return instance;
      });

      await wsService.connect('ws://localhost:8000/ws');
      await new Promise(resolve => setTimeout(resolve, 20));

      expect(errorHandler).toHaveBeenCalled();
    });
  });

  describe('Message correlation', () => {
    beforeEach(async () => {
      await wsService.connect('ws://localhost:8000/ws');
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    it('should correlate responses with requests', () => {
      const responseHandler = vi.fn();

      wsService.createGame({ mode: 'human_vs_human' }, responseHandler);

      // Get the request ID from sent message
      const sentMessage = JSON.parse(mockWebSocketInstance?.getLastMessage() || '{}');
      const requestId = sentMessage.request_id;

      // Simulate correlated response
      const response = {
        type: 'game_created',
        request_id: requestId,
        data: { game_id: 'new-game-123', success: true }
      };

      mockWebSocketInstance?.simulateMessage(JSON.stringify(response));

      expect(responseHandler).toHaveBeenCalledWith(response);
    });

    it('should handle timeout for uncorrelated requests', async () => {
      const timeoutHandler = vi.fn();

      wsService.createGame({ mode: 'human_vs_human' }, null, timeoutHandler, 100); // 100ms timeout

      // Wait for timeout
      await new Promise(resolve => setTimeout(resolve, 150));

      expect(timeoutHandler).toHaveBeenCalled();
    });

    it('should ignore responses without correlation', () => {
      const responseHandler = vi.fn();
      const messageHandler = vi.fn();

      wsService.onMessage(messageHandler);
      wsService.createGame({ mode: 'human_vs_human' }, responseHandler);

      // Send response with wrong request ID
      const response = {
        type: 'game_created',
        request_id: 'wrong-id',
        data: { game_id: 'new-game-123', success: true }
      };

      mockWebSocketInstance?.simulateMessage(JSON.stringify(response));

      expect(responseHandler).not.toHaveBeenCalled();
      expect(messageHandler).toHaveBeenCalledWith(response); // Should still go to general handler
    });
  });

  describe('Cleanup and resource management', () => {
    it('should clean up event handlers on disconnect', async () => {
      await wsService.connect('ws://localhost:8000/ws');
      await new Promise(resolve => setTimeout(resolve, 20));

      const handler = vi.fn();
      wsService.onMessage(handler);

      wsService.disconnect();

      // Try to simulate message after disconnect
      mockWebSocketInstance?.simulateMessage('{"type": "test"}');

      expect(handler).not.toHaveBeenCalled();
    });

    it('should clear message queue on explicit disconnect', () => {
      // Queue messages while disconnected
      wsService.sendMessage({ type: 'queued1', data: {} });
      wsService.sendMessage({ type: 'queued2', data: {} });

      // Clear queue by disconnecting
      wsService.disconnect();

      // Reconnect - no queued messages should be sent
      wsService.connect('ws://localhost:8000/ws');

      expect(mockWebSocketInstance?.getAllMessages()).toHaveLength(0);
    });
  });
});