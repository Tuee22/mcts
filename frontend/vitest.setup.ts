// Import React first to ensure it's available globally
import React from 'react'
import { expect, afterEach, vi, beforeAll, afterAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

// Make React available globally to prevent hook errors
;(globalThis as any).React = React

// Extend Vitest's expect with Testing Library matchers
expect.extend(matchers)

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