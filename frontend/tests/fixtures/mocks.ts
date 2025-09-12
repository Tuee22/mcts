// Standardized mocks for frontend testing
import { vi } from 'vitest';

// Comprehensive WebSocket mock with proper state management
export const createMockWebSocket = () => {
  const mockSocket = {
    // Core WebSocket properties
    url: 'ws://localhost:8000/ws',
    readyState: WebSocket.CONNECTING,
    protocol: '',
    extensions: '',
    bufferedAmount: 0,
    binaryType: 'blob' as BinaryType,
    
    // Event handlers
    onopen: null as ((event: Event) => void) | null,
    onclose: null as ((event: CloseEvent) => void) | null,
    onmessage: null as ((event: MessageEvent) => void) | null,
    onerror: null as ((event: Event) => void) | null,
    
    // Methods
    send: vi.fn(),
    close: vi.fn().mockImplementation((code?: number, reason?: string) => {
      mockSocket.readyState = WebSocket.CLOSED;
      if (mockSocket.onclose) {
        mockSocket.onclose(new CloseEvent('close', { code: code || 1000, reason: reason || '' }));
      }
    }),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
    
    // Test helpers for simulation
    simulateOpen: () => {
      mockSocket.readyState = WebSocket.OPEN;
      if (mockSocket.onopen) {
        mockSocket.onopen(new Event('open'));
      }
    },
    
    simulateClose: (code = 1000, reason = '') => {
      mockSocket.readyState = WebSocket.CLOSED;
      if (mockSocket.onclose) {
        mockSocket.onclose(new CloseEvent('close', { code, reason }));
      }
    },
    
    simulateMessage: (data: any) => {
      if (mockSocket.onmessage) {
        const messageData = typeof data === 'string' ? data : JSON.stringify(data);
        mockSocket.onmessage(new MessageEvent('message', { data: messageData }));
      }
    },
    
    simulateError: (error?: string) => {
      if (mockSocket.onerror) {
        mockSocket.onerror(new Event('error'));
      }
    },
    
    // Reset mock to initial state
    reset: () => {
      mockSocket.readyState = WebSocket.CONNECTING;
      mockSocket.onopen = null;
      mockSocket.onclose = null;
      mockSocket.onmessage = null;
      mockSocket.onerror = null;
      vi.clearAllMocks();
    }
  };
  
  return mockSocket;
};

// WebSocket service mock factory
export const createMockWebSocketService = () => ({
  connect: vi.fn(() => Promise.resolve()),
  disconnect: vi.fn(),
  isConnected: vi.fn(() => true),
  createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
  makeMove: vi.fn(() => Promise.resolve()),
  getAIMove: vi.fn(() => Promise.resolve()),
  requestGameState: vi.fn(() => Promise.resolve()),
  
  // Test helpers
  simulateConnection: function() {
    this.isConnected.mockReturnValue(true);
  },
  simulateDisconnection: function() {
    this.isConnected.mockReturnValue(false);
  },
  simulateError: function(error: string) {
    this.connect.mockRejectedValue(new Error(error));
  },
  reset: function() {
    Object.values(this).forEach(fn => {
      if (typeof fn === 'function' && 'mockReset' in fn) {
        fn.mockReset();
      }
    });
    this.isConnected.mockReturnValue(true);
  }
});

// Game store mock factory
export const createMockGameStore = (overrides = {}) => ({
  // State
  gameId: null,
  gameState: null,
  gameSettings: {
    mode: 'human_vs_ai' as const,
    ai_difficulty: 'medium' as const,
    ai_time_limit: 5000,
    board_size: 9
  },
  isConnected: true,
  isLoading: false,
  error: null,
  selectedHistoryIndex: null,
  
  // Actions
  setGameId: vi.fn(),
  setGameState: vi.fn(),
  setGameSettings: vi.fn(),
  setIsConnected: vi.fn(),
  setIsLoading: vi.fn(),
  setError: vi.fn(),
  setSelectedHistoryIndex: vi.fn(),
  addMoveToHistory: vi.fn(),
  reset: vi.fn(),
  
  // Apply overrides
  ...overrides,
  
  // Test helpers
  simulateConnected: function() {
    this.isConnected = true;
    this.setIsConnected.mockReturnValue(true);
  },
  simulateDisconnected: function() {
    this.isConnected = false;
    this.setIsConnected.mockReturnValue(false);
  },
  simulateLoading: function() {
    this.isLoading = true;
    this.setIsLoading.mockReturnValue(true);
  },
  resetMocks: function() {
    Object.values(this).forEach(value => {
      if (typeof value === 'function' && 'mockReset' in value) {
        value.mockReset();
      }
    });
  }
});

// Fetch API mock
export const createMockFetch = () => {
  const mockFetch = vi.fn();
  
  // Default successful responses
  mockFetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: vi.fn().mockResolvedValue({ success: true }),
    text: vi.fn().mockResolvedValue(''),
    blob: vi.fn().mockResolvedValue(new Blob()),
    headers: new Headers(),
    redirected: false,
    statusText: 'OK',
    type: 'basic' as ResponseType,
    url: 'http://localhost:8000/api/test',
    clone: vi.fn(),
    body: null,
    bodyUsed: false,
    arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(0)),
    formData: vi.fn().mockResolvedValue(new FormData())
  });
  
  return mockFetch;
};

// Global mock setup for consistent behavior across tests
export const setupGlobalMocks = () => {
  // Mock WebSocket constructor
  const mockSocket = createMockWebSocket();
  global.WebSocket = vi.fn().mockImplementation(() => {
    // Auto-simulate connection opening
    setTimeout(() => {
      if (mockSocket.readyState === WebSocket.CONNECTING) {
        mockSocket.simulateOpen();
      }
    }, 0);
    return mockSocket;
  }) as any;
  
  // Define WebSocket constants
  Object.defineProperty(WebSocket, 'CONNECTING', { value: 0 });
  Object.defineProperty(WebSocket, 'OPEN', { value: 1 });
  Object.defineProperty(WebSocket, 'CLOSING', { value: 2 });
  Object.defineProperty(WebSocket, 'CLOSED', { value: 3 });
  
  // Mock fetch
  global.fetch = createMockFetch();
  
  return {
    mockSocket,
    mockFetch: global.fetch as any
  };
};

// Reset all global mocks
export const resetGlobalMocks = () => {
  vi.clearAllMocks();
  if (global.WebSocket && 'mockReset' in global.WebSocket) {
    (global.WebSocket as any).mockReset();
  }
  if (global.fetch && 'mockReset' in global.fetch) {
    (global.fetch as any).mockReset();
  }
};

// Clipboard API mock
export const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
  readText: vi.fn().mockResolvedValue(''),
  write: vi.fn().mockResolvedValue(undefined),
  read: vi.fn().mockResolvedValue([])
};

// Export individual mock instances for specific tests
export const mockWebSocket = createMockWebSocket();
export const mockWebSocketService = createMockWebSocketService();
export const mockGameStore = createMockGameStore();
export const mockFetch = createMockFetch();