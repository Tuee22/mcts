/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  esbuild: {
    jsx: 'automatic',
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./setup/setupTests.ts'],
    globals: true,
    css: true,
    // Fix deprecated 'basic' reporter
    reporters: [
      ['default', { summary: false }]
    ],
    // Frontend tests should be fast and isolated
    include: ['**/*.test.{ts,tsx}'],
    exclude: [
      '**/node_modules/**',
      '**/build/**',
      '**/dist/**',
      // Exclude integration and E2E tests - they belong elsewhere
      '**/*integration*.test.*',
      '**/*e2e*.test.*'
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      include: ['../../frontend/src/**/*.{ts,tsx}'],
      exclude: [
        'node_modules/',
        'setup/',
        'fixtures/',
        '**/*.d.ts',
        'coverage/',
        'build/',
        'dist/'
      ],
      thresholds: {
        global: {
          branches: 90,
          functions: 90,
          lines: 90,
          statements: 90
        }
      }
    },
    // Performance and memory monitoring
    logHeapUsage: true,
    testTimeout: 5000, // Fast tests only
    hookTimeout: 2000
  },
  resolve: {
    alias: {
      // Frontend source alias  
      '@': path.resolve(__dirname, '../../frontend/src'),
      '@frontend': path.resolve(__dirname, '../../frontend/src')
    }
  },
  // Specify node modules resolution for container
  define: {
    global: 'globalThis',
  }
})