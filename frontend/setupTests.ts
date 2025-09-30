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
  
  toBeEnabled(received: HTMLElement) {
    const pass = !received.hasAttribute('disabled') && 
                 (received as HTMLInputElement).disabled !== true;
    return {
      message: () =>
        pass
          ? `Expected element not to be enabled`
          : `Expected element to be enabled`,
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
  // Mock browser APIs that don't exist in jsdom
  setupBrowserAPIs();

  // Mock performance APIs
  setupPerformanceAPIs();

  // Setup console error filtering for cleaner test output
  setupConsoleFiltering();
});

// Additional cleanup before each test to ensure fresh state
beforeEach(() => {
  // Ensure clean DOM before each test
  cleanup();

  // Clear document body
  if (document.body) {
    document.body.innerHTML = '';
  }
});

// Cleanup after each test automatically
afterEach(() => {
  // Clean up React Testing Library DOM
  cleanup();

  // Clear all mock calls and instances
  vi.clearAllMocks();

  // Selectively reset modules that cause state leakage
  // Only reset modules that don't break test isolation
  // NOTE: Commented out as it interferes with mock application
  // try {
  //   // Reset React-related modules that might hold state
  //   vi.resetModules(['@/store/gameStore', '@/services/websocket']);
  // } catch {
  //   // Module reset failed, continue
  // }

  // Clear timers and intervals if they are mocked
  try {
    vi.clearAllTimers();
    vi.runOnlyPendingTimers();
  } catch {
    // Timers are not mocked, skip
  }

  // Reset clipboard mock if it exists
  if (navigator.clipboard && 'mockReset' in navigator.clipboard) {
    (navigator.clipboard as any).mockReset();
  }

  // Clear any pending timeouts/intervals
  if (typeof window !== 'undefined') {
    // Clear any lingering timeouts
    for (let i = 1; i < 9999; i++) {
      clearTimeout(i);
      clearInterval(i);
    }
  }

  // Clean up DOM state more thoroughly
  if (document.body) {
    document.body.innerHTML = '';
  }

  // Reset global React state if available
  if ((globalThis as any).React) {
    // Clear any cached React instances
    try {
      (globalThis as any).React.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = undefined;
    } catch {
      // React internals not available
    }
  }

  // Force garbage collection if available
  if (global.gc) {
    global.gc();
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
      close: vi.fn(function(this: any) {
        this.readyState = WebSocket.CLOSED;
        if (this.onclose) {
          this.onclose(new CloseEvent('close'));
        }
      }),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onopen: null,
      onclose: null,
      onmessage: null,
      onerror: null
    };

    // Bind close method to ws instance for proper 'this' context
    ws.close = ws.close.bind(ws);

    // Ensure the close method is always available and bound
    Object.defineProperty(ws, 'close', {
      value: ws.close,
      writable: false,
      enumerable: true,
      configurable: false
    });

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
  global.ResizeObserver = class ResizeObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();

    constructor(callback?: ResizeObserverCallback) {
      // Store callback if needed for testing
    }
  } as any;

  // Mock IntersectionObserver
  global.IntersectionObserver = class IntersectionObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
    root = null;
    rootMargin = '';
    thresholds: number[] = [];

    constructor(callback?: IntersectionObserverCallback, options?: IntersectionObserverInit) {
      // Store callback and options if needed for testing
    }
  } as any;

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

  // Mock Canvas API with comprehensive implementation
  const mockCanvasContext = {
    // Drawing rectangles
    fillRect: vi.fn(),
    clearRect: vi.fn(),
    strokeRect: vi.fn(),

    // Drawing paths
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    closePath: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    clip: vi.fn(),
    arc: vi.fn(),
    arcTo: vi.fn(),
    bezierCurveTo: vi.fn(),
    quadraticCurveTo: vi.fn(),
    rect: vi.fn(),
    ellipse: vi.fn(),

    // Text
    fillText: vi.fn(),
    strokeText: vi.fn(),
    measureText: vi.fn(() => ({
      width: 100,
      actualBoundingBoxLeft: 0,
      actualBoundingBoxRight: 100,
      actualBoundingBoxAscent: 10,
      actualBoundingBoxDescent: 2,
      fontBoundingBoxAscent: 12,
      fontBoundingBoxDescent: 3,
      emHeightAscent: 10,
      emHeightDescent: 2,
      hangingBaseline: 8,
      alphabeticBaseline: 0,
      ideographicBaseline: -2
    })),

    // Transformations
    translate: vi.fn(),
    scale: vi.fn(),
    rotate: vi.fn(),
    transform: vi.fn(),
    setTransform: vi.fn(),
    resetTransform: vi.fn(),

    // Image drawing
    drawImage: vi.fn(),

    // Pixel manipulation
    getImageData: vi.fn(() => ({
      data: new Uint8ClampedArray(4),
      width: 1,
      height: 1,
      colorSpace: 'srgb'
    })),
    putImageData: vi.fn(),
    createImageData: vi.fn((width: number = 1, height: number = 1) => ({
      data: new Uint8ClampedArray(width * height * 4),
      width,
      height,
      colorSpace: 'srgb'
    })),

    // State
    save: vi.fn(),
    restore: vi.fn(),

    // Gradients and patterns
    createLinearGradient: vi.fn(() => ({
      addColorStop: vi.fn()
    })),
    createRadialGradient: vi.fn(() => ({
      addColorStop: vi.fn()
    })),
    createPattern: vi.fn(() => null),

    // Line styles
    setLineDash: vi.fn(),
    getLineDash: vi.fn(() => []),

    // Filters and compositing
    filter: 'none',
    globalAlpha: 1,
    globalCompositeOperation: 'source-over',

    // Fill and stroke styles
    fillStyle: '#000000',
    strokeStyle: '#000000',
    lineWidth: 1,
    lineCap: 'butt',
    lineJoin: 'miter',
    miterLimit: 10,
    lineDashOffset: 0,

    // Shadow styles
    shadowBlur: 0,
    shadowColor: 'rgba(0, 0, 0, 0)',
    shadowOffsetX: 0,
    shadowOffsetY: 0,

    // Text styles
    font: '10px sans-serif',
    textAlign: 'start',
    textBaseline: 'alphabetic',
    direction: 'inherit',
    fontKerning: 'auto',

    // Path2D support
    isPointInPath: vi.fn(() => false),
    isPointInStroke: vi.fn(() => false)
  };

  // Enhanced HTMLCanvasElement mock - always returns a context
  HTMLCanvasElement.prototype.getContext = vi.fn().mockImplementation((contextType: string, options?: any) => {
    if (contextType === '2d') {
      return mockCanvasContext;
    } else if (contextType === 'webgl' || contextType === 'webgl2') {
      // Basic WebGL mock
      return {
        canvas: {},
        drawingBufferWidth: 300,
        drawingBufferHeight: 150,
        getParameter: vi.fn(),
        getExtension: vi.fn(() => null),
        getSupportedExtensions: vi.fn(() => []),
        createShader: vi.fn(),
        createProgram: vi.fn(),
        attachShader: vi.fn(),
        linkProgram: vi.fn(),
        useProgram: vi.fn(),
        createBuffer: vi.fn(),
        bindBuffer: vi.fn(),
        bufferData: vi.fn(),
        vertexAttribPointer: vi.fn(),
        enableVertexAttribArray: vi.fn(),
        drawArrays: vi.fn(),
        viewport: vi.fn(),
        clearColor: vi.fn(),
        clear: vi.fn()
      };
    }
    // Always return a basic context even for unknown types to prevent undefined
    return mockCanvasContext;
  });

  // Mock canvas dimensions and properties
  Object.defineProperty(HTMLCanvasElement.prototype, 'width', {
    get: vi.fn(() => 300),
    set: vi.fn(),
    configurable: true
  });

  Object.defineProperty(HTMLCanvasElement.prototype, 'height', {
    get: vi.fn(() => 150),
    set: vi.fn(),
    configurable: true
  });

  // Mock toDataURL and other canvas methods
  HTMLCanvasElement.prototype.toDataURL = vi.fn(() => 'data:image/png;base64,mock');
  HTMLCanvasElement.prototype.toBlob = vi.fn((callback) => {
    if (callback) {
      callback(new Blob(['mock'], { type: 'image/png' }));
    }
  });
  HTMLCanvasElement.prototype.getImageData = vi.fn(() => mockCanvasContext.getImageData());
  HTMLCanvasElement.prototype.transferControlToOffscreen = vi.fn(() => ({
    getContext: vi.fn(() => mockCanvasContext)
  }));

  // Enhance canvas elements created in tests without breaking JSX rendering
  const originalCreateElement = document.createElement.bind(document);
  document.createElement = function(tagName: string, options?: any) {
    const element = originalCreateElement.call(this, tagName, options);
    if (tagName.toLowerCase() === 'canvas') {
      // Enhance canvas elements with better getContext mock
      element.getContext = vi.fn().mockImplementation((contextType: string) => {
        if (contextType === '2d' || contextType === 'webgl' || contextType === 'webgl2') {
          return mockCanvasContext;
        }
        return mockCanvasContext; // Always return context to prevent undefined
      });
      Object.defineProperty(element, 'width', {
        get: () => 300,
        set: vi.fn(),
        configurable: true
      });
      Object.defineProperty(element, 'height', {
        get: () => 150,
        set: vi.fn(),
        configurable: true
      });
    }
    return element;
  };


  // Mock URL.createObjectURL and URL.revokeObjectURL
  global.URL.createObjectURL = vi.fn(() => 'mock-url');
  global.URL.revokeObjectURL = vi.fn();

  // Mock window.location
  Object.defineProperty(window, 'location', {
    value: {
      href: 'http://localhost:8000',
      protocol: 'http:',
      host: 'localhost:8000',
      hostname: 'localhost',
      port: '8000',
      pathname: '/',
      search: '',
      hash: '',
      origin: 'http://localhost:8000',
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
        message.includes('Warning: `ReactDOMTestUtils.act` is deprecated') ||
        // Suppress expected test error messages
        message.includes('Failed to create game:') ||
        message.includes('Failed to create new game:') ||
        message.includes('Connection lost') ||
        message.includes('WebSocket connection failed') ||
        message.includes('Error creating game:') ||
        message.includes('Game creation failed')
      )
    ) {
      return; // Suppress known React warnings and expected test errors
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
  waitFor: async (fn: () => boolean | Promise<boolean>, timeout = 5000): Promise<void> => {
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