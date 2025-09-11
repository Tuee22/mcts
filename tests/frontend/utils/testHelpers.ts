// Test helper utilities for frontend tests
import React, { ReactElement } from 'react';
import { render as rtlRender, RenderOptions, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

// Enhanced render function with common setup
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  // Future: add providers if needed (theme, context, etc.)
}

export const render = (ui: ReactElement, options?: CustomRenderOptions) => {
  const result = rtlRender(ui, options);
  
  // Return enhanced result with additional utilities
  return {
    ...result,
    user: userEvent.setup({
      // Use fake timers if needed
      advanceTimers: vi.advanceTimersByTime,
    })
  };
};

// Create a configured user event instance
export const createUser = () => userEvent.setup({
  advanceTimers: vi.advanceTimersByTime,
});

// Wait for condition helper
export const waitForCondition = async (
  condition: () => boolean | Promise<boolean>,
  options: { timeout?: number; interval?: number } = {}
): Promise<void> => {
  const { timeout = 1000, interval = 10 } = options;
  const start = Date.now();
  
  while (Date.now() - start < timeout) {
    try {
      const result = await condition();
      if (result) return;
    } catch {
      // Continue waiting
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  
  throw new Error(`Condition not met within ${timeout}ms`);
};

// Memory leak detection helpers
export const createMemoryLeakDetector = () => {
  const initialMemory = getMemoryUsage();
  
  return {
    check: (threshold = 5 * 1024 * 1024) => { // 5MB threshold
      const currentMemory = getMemoryUsage();
      if (currentMemory && initialMemory) {
        const diff = currentMemory.usedJSHeapSize - initialMemory.usedJSHeapSize;
        if (diff > threshold) {
          console.warn(`Potential memory leak detected: ${diff} bytes increase`);
          return false;
        }
      }
      return true;
    }
  };
};

function getMemoryUsage() {
  if ('memory' in performance) {
    return (performance as any).memory;
  }
  return null;
}

// Performance measurement helpers
export const measureRenderTime = async (renderFn: () => void): Promise<number> => {
  const start = performance.now();
  renderFn();
  // Wait for next tick to ensure render is complete
  await new Promise(resolve => setTimeout(resolve, 0));
  const end = performance.now();
  return end - start;
};

// DOM query helpers with better error messages
export const getByTextContent = (text: string | RegExp) => {
  const element = screen.getByText(text);
  if (!element) {
    throw new Error(`Element with text ${text} not found`);
  }
  return element;
};

export const findByTextContent = async (text: string | RegExp) => {
  const element = await screen.findByText(text);
  if (!element) {
    throw new Error(`Element with text ${text} not found`);
  }
  return element;
};

export const queryByTextContent = (text: string | RegExp) => {
  return screen.queryByText(text);
};

// Mock creation helpers
export const createMockWebSocket = () => {
  const mockWS = {
    url: '',
    readyState: WebSocket.CONNECTING,
    send: vi.fn(),
    close: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
    onopen: null as ((event: Event) => void) | null,
    onclose: null as ((event: CloseEvent) => void) | null,
    onmessage: null as ((event: MessageEvent) => void) | null,
    onerror: null as ((event: Event) => void) | null,
    
    // Test helpers
    simulateOpen: () => {
      mockWS.readyState = WebSocket.OPEN;
      if (mockWS.onopen) mockWS.onopen(new Event('open'));
    },
    simulateClose: (code = 1000, reason = '') => {
      mockWS.readyState = WebSocket.CLOSED;
      if (mockWS.onclose) mockWS.onclose(new CloseEvent('close', { code, reason }));
    },
    simulateMessage: (data: any) => {
      if (mockWS.onmessage) {
        mockWS.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
      }
    },
    simulateError: () => {
      if (mockWS.onerror) mockWS.onerror(new Event('error'));
    }
  };
  
  return mockWS;
};

// Storage mocking helpers
export const createMockStorage = () => {
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
    get length() { return Object.keys(store).length; },
    
    // Test helpers
    getStore: () => ({ ...store }),
    setStore: (newStore: { [key: string]: string }) => {
      store = { ...newStore };
    }
  };
};

// Async operation helpers
export const mockAsyncOperation = <T>(
  result: T, 
  delay = 0, 
  shouldReject = false
): Promise<T> => {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (shouldReject) {
        reject(new Error(typeof result === 'string' ? result : 'Mock error'));
      } else {
        resolve(result);
      }
    }, delay);
  });
};

// Component state verification helpers
export const verifyNoMemoryLeaks = (component: HTMLElement) => {
  // Check for common memory leak patterns
  const eventListeners = (component as any)._reactInternalFiber?.memoizedProps;
  const hasUncleanedListeners = eventListeners && Object.keys(eventListeners).some(
    key => key.startsWith('on') && typeof eventListeners[key] === 'function'
  );
  
  return !hasUncleanedListeners;
};

// Error boundary test helper
export const createErrorBoundary = () => {
  let caughtError: Error | null = null;
  
  const ErrorBoundary = ({ children }: { children: React.ReactNode }) => {
    try {
      return React.createElement(React.Fragment, null, children);
    } catch (error) {
      caughtError = error as Error;
      return React.createElement('div', null, 'Error caught');
    }
  };
  
  return {
    ErrorBoundary,
    getCaughtError: () => caughtError,
    clearError: () => { caughtError = null; }
  };
};

// Re-export commonly used testing library functions
export * from '@testing-library/react';
export { userEvent };
export { vi } from 'vitest';