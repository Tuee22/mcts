// Mock WebSocket implementation for testing
export class MockWebSocket {
  private eventHandlers: { [event: string]: Function[] } = {};
  private isConnected = false;
  public url: string;
  public readyState = WebSocket.CONNECTING;

  constructor(url: string) {
    this.url = url;
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      this.isConnected = true;
      this.emit('connect');
    }, 10);
  }

  on(event: string, handler: Function) {
    if (!this.eventHandlers[event]) {
      this.eventHandlers[event] = [];
    }
    this.eventHandlers[event].push(handler);
  }

  emit(event: string, data?: any) {
    if (this.eventHandlers[event]) {
      this.eventHandlers[event].forEach(handler => handler(data));
    }
  }

  send(data: any) {
    // Mock send - can be used to simulate server responses
    console.log('Mock WebSocket send:', data);
  }

  disconnect() {
    this.isConnected = false;
    this.readyState = WebSocket.CLOSED;
    this.emit('disconnect');
  }

  connected() {
    return this.isConnected;
  }
}

import { vi } from 'vitest';

// Mock socket.io client
export const mockSocketIOClient = {
  connect: vi.fn(() => new MockWebSocket('http://localhost:8000')),
  Socket: MockWebSocket
};

// Mock WebSocket service methods
export const mockWebSocketService = {
  connect: vi.fn(),
  disconnect: vi.fn(),
  createGame: vi.fn(),
  joinGame: vi.fn(),
  makeMove: vi.fn(),
  getAIMove: vi.fn(),
  isConnected: vi.fn(() => true)
};

// WebSocket event data mocks
export const mockWebSocketEvents = {
  gameCreated: {
    game_id: 'test-game-123',
    state: {
      board_size: 9,
      current_player: 0,
      players: [{ x: 4, y: 0 }, { x: 4, y: 8 }],
      walls: [],
      walls_remaining: [10, 10],
      legal_moves: ['a1', 'a2', 'b1'],
      winner: null,
      move_history: []
    }
  },
  gameState: {
    state: {
      board_size: 9,
      current_player: 1,
      players: [{ x: 4, y: 1 }, { x: 4, y: 8 }],
      walls: [],
      walls_remaining: [10, 10],
      legal_moves: ['a1', 'a2', 'b1'],
      winner: null,
      move_history: []
    }
  },
  moveMade: {
    move: {
      notation: 'e2',
      player: 0,
      type: 'move',
      position: { x: 4, y: 7 }
    },
    state: {
      board_size: 9,
      current_player: 1,
      players: [{ x: 4, y: 7 }, { x: 4, y: 8 }],
      walls: [],
      walls_remaining: [10, 10],
      legal_moves: ['a1', 'a2', 'b1'],
      winner: null,
      move_history: [{
        notation: 'e2',
        player: 0,
        type: 'move',
        position: { x: 4, y: 7 }
      }]
    }
  },
  gameOver: {
    winner: 0,
    state: {
      board_size: 9,
      current_player: 0,
      players: [{ x: 4, y: 8 }, { x: 4, y: 1 }],
      walls: [],
      walls_remaining: [10, 10],
      legal_moves: [],
      winner: 0,
      move_history: []
    }
  },
  error: {
    message: 'Invalid move'
  }
};