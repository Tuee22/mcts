// Vitest setup file for frontend tests - pure frontend focus
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, afterAll, vi } from 'vitest';

// Cleanup after each test automatically
afterEach(() => {
  cleanup();
  // Clear all mocks after each test
  vi.clearAllMocks();
  // Clear timers
  vi.clearAllTimers();
});

// Mock react-hot-toast globally to avoid rendering issues - must be at module level
vi.mock('react-hot-toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn()
  },
  Toaster: () => null
}));

// Global test setup
beforeAll(() => {

  // Mock browser APIs that don't exist in jsdom
  setupBrowserAPIs();
  
  // Mock performance APIs
  setupPerformanceAPIs();
  
  // Setup console error filtering for cleaner test output
  setupConsoleFiltering();
});

afterAll(() => {
  // Restore original console methods
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
});

// Browser API Mocks
function setupBrowserAPIs() {
  // Mock navigator.clipboard with configurable property
  Object.defineProperty(navigator, 'clipboard', {
    value: {
      writeText: vi.fn(() => Promise.resolve()),
      readText: vi.fn(() => Promise.resolve('')),
      write: vi.fn(() => Promise.resolve()),
      read: vi.fn(() => Promise.resolve([]))
    },
    writable: true,
    configurable: true
  });

  // Mock localStorage
  const createStorageMock = () => {
    let store: { [key: string]: string } = {};
    return {
      getItem: vi.fn((key: string) => store[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        store[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete store[key];
      }),
      clear: vi.fn(() => {
        store = {};
      }),
      key: vi.fn((index: number) => Object.keys(store)[index] || null),
      get length() { return Object.keys(store).length; }
    };
  };

  Object.defineProperty(window, 'localStorage', {
    value: createStorageMock(),
    configurable: true,
    writable: true
  });

  Object.defineProperty(window, 'sessionStorage', {
    value: createStorageMock(),
    configurable: true,
    writable: true
  });

  // Mock WebSocket with proper state management
  global.WebSocket = vi.fn().mockImplementation((url: string) => {
    const ws = {
      url,
      readyState: WebSocket.CONNECTING,
      send: vi.fn(),
      close: vi.fn(() => {
        ws.readyState = WebSocket.CLOSED;
      }),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onopen: null,
      onclose: null,
      onmessage: null,
      onerror: null
    };
    
    // Simulate connection opening after a tick
    setTimeout(() => {
      ws.readyState = WebSocket.OPEN;
      if (ws.onopen) ws.onopen(new Event('open'));
    }, 0);
    
    return ws;
  }) as any;

  // Define WebSocket constants
  Object.defineProperty(WebSocket, 'CONNECTING', { value: 0 });
  Object.defineProperty(WebSocket, 'OPEN', { value: 1 });
  Object.defineProperty(WebSocket, 'CLOSING', { value: 2 });
  Object.defineProperty(WebSocket, 'CLOSED', { value: 3 });

  // Mock ResizeObserver
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn()
  }));

  // Mock IntersectionObserver
  global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
    root: null,
    rootMargin: '',
    thresholds: []
  }));

  // Mock matchMedia
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn()
    }))
  });

  // Mock Canvas API
  HTMLCanvasElement.prototype.getContext = vi.fn().mockImplementation(() => ({
    fillRect: vi.fn(),
    clearRect: vi.fn(),
    getImageData: vi.fn(() => ({ data: new Array(4) })),
    putImageData: vi.fn(),
    createImageData: vi.fn(() => ({ data: new Array(4) })),
    setTransform: vi.fn(),
    drawImage: vi.fn(),
    save: vi.fn(),
    fillText: vi.fn(),
    restore: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    closePath: vi.fn(),
    stroke: vi.fn(),
    translate: vi.fn(),
    scale: vi.fn(),
    rotate: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    measureText: vi.fn(() => ({ width: 0 })),
    transform: vi.fn(),
    rect: vi.fn(),
    clip: vi.fn()
  }));

  // Mock URL.createObjectURL and URL.revokeObjectURL
  global.URL.createObjectURL = vi.fn(() => 'mock-url');
  global.URL.revokeObjectURL = vi.fn();
}

// Performance API Mocks
function setupPerformanceAPIs() {
  // Mock performance.now with consistent timing - only if not already defined
  if (!window.performance.now || Object.getOwnPropertyDescriptor(window.performance, 'now')?.configurable !== false) {
    Object.defineProperty(window.performance, 'now', {
      value: vi.fn(() => Date.now()),
      configurable: true,
      writable: true
    });
  }

  // Mock requestAnimationFrame
  global.requestAnimationFrame = vi.fn(cb => setTimeout(cb, 16));
  global.cancelAnimationFrame = vi.fn(clearTimeout);

  // Mock requestIdleCallback
  global.requestIdleCallback = vi.fn(cb => setTimeout(cb, 1));
  global.cancelIdleCallback = vi.fn(clearTimeout);
}

// Console filtering for cleaner test output
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

function setupConsoleFiltering() {
  console.error = (...args: any[]) => {
    const message = args[0];
    if (
      typeof message === 'string' && (
        message.includes('Warning: ReactDOM.render is no longer supported') ||
        message.includes('Warning: An invalid form control') ||
        message.includes('Warning: componentWillReceiveProps') ||
        message.includes('Warning: componentWillMount') ||
        message.includes('act(...)') ||
        message.includes('Warning: useLayoutEffect does nothing on the server')
      )
    ) {
      return; // Suppress known React warnings in tests
    }
    originalConsoleError.call(console, ...args);
  };

  console.warn = (...args: any[]) => {
    const message = args[0];
    if (
      typeof message === 'string' && (
        message.includes('Warning: React.createElement') ||
        message.includes('Warning: Each child in a list should have a unique "key" prop')
      )
    ) {
      return; // Suppress known React warnings in tests
    }
    originalConsoleWarn.call(console, ...args);
  };
}

// Export utilities for tests
export const testUtils = {
  // Wait for async operations
  waitFor: async (fn: () => boolean | Promise<boolean>, timeout = 1000): Promise<void> => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const result = await fn();
        if (result) return;
      } catch {
        // Continue waiting
      }
      await new Promise(resolve => setTimeout(resolve, 10));
    }
    throw new Error(`Timeout waiting for condition after ${timeout}ms`);
  },

  // Memory usage tracking
  getMemoryUsage: () => {
    if ('memory' in performance) {
      return (performance as any).memory;
    }
    return null;
  }
};