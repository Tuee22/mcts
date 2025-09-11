// Import React first to ensure it's available globally
import React, { act } from 'react'
import { expect, afterEach, vi, beforeAll, afterAll } from 'vitest'
import { cleanup, configure } from '@testing-library/react'

// Define custom DOM matchers for Vitest testing
const customMatchers = {
  toBeInTheDocument(received: any) {
    const pass = received && document.body.contains(received);
    return {
      message: () => `expected element ${pass ? 'not ' : ''}to be in the document`,
      pass,
    };
  },
  toHaveTextContent(received: any, expected: string | RegExp) {
    const textContent = received?.textContent || '';
    const pass = typeof expected === 'string' 
      ? textContent.includes(expected)
      : expected.test(textContent);
    return {
      message: () => `expected element to have text content "${expected}", but got "${textContent}"`,
      pass,
    };
  },
  toHaveAttribute(received: any, attribute: string, expectedValue?: any) {
    if (!received) return { message: () => 'expected element to exist', pass: false };
    const hasAttribute = received.hasAttribute(attribute);
    if (expectedValue === undefined) {
      return {
        message: () => `expected element ${hasAttribute ? 'not ' : ''}to have attribute "${attribute}"`,
        pass: hasAttribute,
      };
    }
    const actualValue = received.getAttribute(attribute);
    const pass = hasAttribute && actualValue === expectedValue;
    return {
      message: () => `expected element to have attribute "${attribute}" with value "${expectedValue}", but got "${actualValue}"`,
      pass,
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
  },
  toBeDisabled(received: any) {
    if (!received) return { message: () => 'expected element to exist', pass: false };
    const pass = received.disabled === true || received.hasAttribute('disabled');
    return {
      message: () => `expected element ${pass ? 'not ' : ''}to be disabled`,
      pass,
    };
  }
};

// Make React available globally to prevent hook errors
;(globalThis as any).React = React

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

// Extend Vitest's expect with our custom DOM matchers
expect.extend(customMatchers)

// Global setup before all tests
beforeAll(() => {
  // Ensure React is properly initialized
  console.log('React version in test environment:', React.version)
})

// Cleanup after each test case (e.g. clearing jsdom)
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  vi.clearAllTimers()
})

// Final cleanup after all tests
afterAll(() => {
  vi.restoreAllMocks()
})

// Mock global APIs that might not be available in jsdom
Object.defineProperty(global, 'ResizeObserver', {
  value: vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  })),
  writable: true,
})

Object.defineProperty(global, 'IntersectionObserver', {
  value: vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  })),
  writable: true,
})

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
})

// Mock requestAnimationFrame
global.requestAnimationFrame = vi.fn((cb) => {
  return setTimeout(cb, 16)
})

global.cancelAnimationFrame = vi.fn((id) => {
  clearTimeout(id)
})

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
})

// Mock navigator.clipboard - handle existing property
if (!navigator.clipboard) {
  Object.defineProperty(navigator, 'clipboard', {
    value: {
      writeText: vi.fn(() => Promise.resolve()),
      readText: vi.fn(() => Promise.resolve('mock clipboard text')),
    },
    writable: true,
    configurable: true,
  });
} else {
  // If clipboard already exists, just replace the methods
  navigator.clipboard.writeText = vi.fn(() => Promise.resolve());
  navigator.clipboard.readText = vi.fn(() => Promise.resolve('mock clipboard text'));
}