// Comprehensive Vitest setup file for frontend tests
import React from 'react';
import { cleanup, configure } from '@testing-library/react';
import { afterEach, beforeAll, afterAll, vi, expect } from 'vitest';

// Import React's act (not ReactDOM's) for modern act usage  
import { act } from 'react';

// Make React and act available globally to prevent hook errors
(globalThis as any).React = React;
(globalThis as any).act = act;

// Configure testing library to use React.act
configure({
  // Use React.act instead of the deprecated ReactDOMTestUtils.act
  asyncWrapper: async (cb) => {
    let result: any
    await act(async () => {
      result = await cb()
    })
    return result
  },
  // Reduce timeout for faster tests
  asyncUtilTimeout: 5000,
})

// Custom DOM matchers - Vitest native approach
expect.extend({
  toBeInTheDocument(received: Element) {
    const pass = document.body.contains(received);
    return {
      message: () => 
        pass 
          ? `Expected element not to be in the document`
          : `Expected element to be in the document`,
      pass,
    };
  },
  
  toHaveClass(received: Element, expectedClass: string) {
    const pass = received.classList.contains(expectedClass);
    return {
      message: () =>
        pass
          ? `Expected element not to have class "${expectedClass}"`
          : `Expected element to have class "${expectedClass}"`,
      pass,
    };
  },
  
  toHaveTextContent(received: Element, expectedText: string | RegExp) {
    const actualText = received.textContent || '';
    const pass = typeof expectedText === 'string' 
      ? actualText.includes(expectedText)
      : expectedText.test(actualText);
    return {
      message: () =>
        pass
          ? `Expected element not to have text content "${expectedText}"`
          : `Expected element to have text content "${expectedText}", but got "${actualText}"`,
      pass,
    };
  },
  
  toBeDisabled(received: HTMLElement) {
    const pass = received.hasAttribute('disabled') || 
                 (received as HTMLInputElement).disabled === true;
    return {
      message: () =>
        pass
          ? `Expected element not to be disabled`
          : `Expected element to be disabled`,
      pass,
    };
  },
  
  toHaveAttribute(received: Element, expectedAttribute: string, expectedValue?: string) {
    const hasAttribute = received.hasAttribute(expectedAttribute);
    if (!hasAttribute) {
      return {
        message: () => `Expected element to have attribute "${expectedAttribute}"`,
        pass: false,
      };
    }
    
    if (expectedValue !== undefined) {
      const actualValue = received.getAttribute(expectedAttribute);
      const pass = actualValue === expectedValue;
      return {
        message: () =>
          pass
            ? `Expected element not to have attribute "${expectedAttribute}" with value "${expectedValue}"`
            : `Expected element to have attribute "${expectedAttribute}" with value "${expectedValue}", but got "${actualValue}"`,
        pass,
      };
    }
    
    return {
      message: () => `Expected element not to have attribute "${expectedAttribute}"`,
      pass: true,
    };
  },

  toBeVisible(received: any) {
    if (!received) return { message: () => 'expected element to exist', pass: false };
    const style = window.getComputedStyle(received);
    const pass = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    return {
      message: () => `expected element ${pass ? 'not ' : ''}to be visible`,
      pass,
    };
  }
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
  // Ensure React is properly initialized
  console.log('React version in test environment:', React.version);
  
  // Mock browser APIs that don't exist in jsdom
  setupBrowserAPIs();
  
  // Mock performance APIs
  setupPerformanceAPIs();
  
  // Setup console error filtering for cleaner test output
  setupConsoleFiltering();
});

// Cleanup after each test automatically
afterEach(() => {
  cleanup();
  // Clear all mocks after each test
  vi.clearAllMocks();
  // Clear timers
  vi.clearAllTimers();
  // Reset clipboard mock if it exists
  if (navigator.clipboard && 'mockReset' in navigator.clipboard) {
    (navigator.clipboard as any).mockReset();
  }
});

afterAll(() => {
  // Restore original console methods
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
  
  // Restore all mocks
  vi.restoreAllMocks();
});

// Browser API Mocks
function setupBrowserAPIs() {
  // Mock navigator.clipboard with configurable property - delete first if exists
  if ('clipboard' in navigator) {
    delete (navigator as any).clipboard;
  }
  
  // Create a more comprehensive clipboard mock
  const clipboardMock = {
    writeText: vi.fn(() => Promise.resolve()),
    readText: vi.fn(() => Promise.resolve('')),
    write: vi.fn(() => Promise.resolve()),
    read: vi.fn(() => Promise.resolve([])),
    // Reset method for tests
    mockReset: () => {
      clipboardMock.writeText.mockReset();
      clipboardMock.readText.mockReset();
      clipboardMock.write.mockReset();
      clipboardMock.read.mockReset();
    }
  };
  
  Object.defineProperty(navigator, 'clipboard', {
    value: clipboardMock,
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

  // Mock window.location
  Object.defineProperty(window, 'location', {
    value: {
      href: 'http://localhost:3000',
      protocol: 'http:',
      host: 'localhost:3000',
      hostname: 'localhost',
      port: '3000',
      pathname: '/',
      search: '',
      hash: '',
      origin: 'http://localhost:3000',
    },
    writable: true,
  });
}

// Performance API Mocks
function setupPerformanceAPIs() {
  // Mock performance.now with consistent timing
  Object.defineProperty(window.performance, 'now', {
    value: vi.fn(() => Date.now()),
    configurable: true,
    writable: true
  });

  // Mock requestAnimationFrame
  global.requestAnimationFrame = vi.fn(cb => setTimeout(cb, 16));
  global.cancelAnimationFrame = vi.fn(clearTimeout);

  // Mock requestIdleCallback
  global.requestIdleCallback = vi.fn(cb => setTimeout(cb, 1));
  global.cancelIdleCallback = vi.fn(clearTimeout);

  // Mock performance API
  Object.defineProperty(global, 'performance', {
    value: {
      now: vi.fn(() => Date.now()),
      mark: vi.fn(),
      measure: vi.fn(),
      memory: {
        usedJSHeapSize: 1000000,
        totalJSHeapSize: 2000000,
        jsHeapSizeLimit: 4000000,
      },
    },
    writable: true,
  });
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
        message.includes('Warning: An update to') ||
        message.includes('Warning: useLayoutEffect does nothing on the server') ||
        message.includes('Warning: `ReactDOMTestUtils.act` is deprecated')
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