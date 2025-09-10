// Standardized mocks for frontend testing
import { vi } from 'vitest';

// WebSocket service mock
export const mockWebSocketService = {
  connect: vi.fn(() => Promise.resolve()),
  disconnect: vi.fn(),
  isConnected: vi.fn(() => true),
  createGame: vi.fn(() => Promise.resolve({ gameId: 'test-game-123' })),
  makeMove: vi.fn(() => Promise.resolve()),
  getAIMove: vi.fn(() => Promise.resolve()),
  
  // Test helpers
  simulateConnection: () => {
    mockWebSocketService.isConnected.mockReturnValue(true);
  },
  simulateDisconnection: () => {
    mockWebSocketService.isConnected.mockReturnValue(false);
  },
  simulateError: (error: string) => {
    mockWebSocketService.connect.mockRejectedValue(new Error(error));
  }
};

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
  ...overrides
});

// React Hot Toast mock
export const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
  loading: vi.fn(),
  dismiss: vi.fn()
};

// Zustand store mock helper
export const createZustandMock = <T>(initialState: T, actions: any = {}) => {
  let state = { ...initialState };
  
  const setState = (updater: Partial<T> | ((state: T) => Partial<T>)) => {
    if (typeof updater === 'function') {
      state = { ...state, ...updater(state) };
    } else {
      state = { ...state, ...updater };
    }
  };
  
  const getState = () => state;
  
  return vi.fn(() => ({
    ...state,
    ...actions,
    setState,
    getState
  }));
};

// Performance observer mock
export const mockPerformanceObserver = {
  observe: vi.fn(),
  disconnect: vi.fn(),
  takeRecords: vi.fn(() => [])
};

// Intersection observer mock
export const mockIntersectionObserver = {
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
};

// Resize observer mock  
export const mockResizeObserver = {
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
};

// Socket.io client mock
export const mockSocketIO = {
  connect: vi.fn(() => mockSocketIOInstance),
  disconnect: vi.fn(),
  connected: true,
  on: vi.fn(),
  off: vi.fn(),
  emit: vi.fn()
};

export const mockSocketIOInstance = {
  connected: true,
  connect: vi.fn(),
  disconnect: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  emit: vi.fn(),
  
  // Test helpers
  simulateConnect: () => {
    mockSocketIOInstance.connected = true;
    const onHandlers = mockSocketIOInstance.on.mock.calls
      .filter(call => call[0] === 'connect')
      .map(call => call[1]);
    onHandlers.forEach(handler => handler());
  },
  simulateDisconnect: () => {
    mockSocketIOInstance.connected = false;
    const onHandlers = mockSocketIOInstance.on.mock.calls
      .filter(call => call[0] === 'disconnect')
      .map(call => call[1]);
    onHandlers.forEach(handler => handler());
  },
  simulateMessage: (event: string, data: any) => {
    const onHandlers = mockSocketIOInstance.on.mock.calls
      .filter(call => call[0] === event)
      .map(call => call[1]);
    onHandlers.forEach(handler => handler(data));
  }
};

// Clipboard API mock
export const mockClipboard = {
  writeText: vi.fn(() => Promise.resolve()),
  readText: vi.fn(() => Promise.resolve('')),
  write: vi.fn(() => Promise.resolve()),
  read: vi.fn(() => Promise.resolve([]))
};

// File system access mock (for potential save/load features)
export const mockFileSystemAccess = {
  showOpenFilePicker: vi.fn(() => Promise.resolve([])),
  showSaveFilePicker: vi.fn(() => Promise.resolve(null))
};

// Notification API mock
export const mockNotification = {
  requestPermission: vi.fn(() => Promise.resolve('granted')),
  permission: 'granted'
};

// Media query mock
export const mockMatchMedia = (matches = false) => ({
  matches,
  media: '',
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn()
});

// CSS animation mock
export const mockAnimation = {
  play: vi.fn(),
  pause: vi.fn(),
  finish: vi.fn(),
  cancel: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn()
};

// RequestAnimationFrame mock queue
export const mockRAFQueue: Array<(time: number) => void> = [];

export const mockRequestAnimationFrame = (callback: (time: number) => void) => {
  mockRAFQueue.push(callback);
  return mockRAFQueue.length;
};

export const mockCancelAnimationFrame = (id: number) => {
  delete mockRAFQueue[id - 1];
};

export const flushRAFQueue = () => {
  const currentTime = performance.now();
  mockRAFQueue.forEach(callback => callback && callback(currentTime));
  mockRAFQueue.length = 0;
};