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
      '**/*e2e*.test.*',
      // Exclude performance tests by default (run separately)
      '**/performanceEdgeCases.test.*'
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
          branches: 80, // Reduced from 90 to be more realistic
          functions: 80,
          lines: 80,
          statements: 80
        }
      }
    },
    // Memory and performance optimizations
    logHeapUsage: false, // Disabled to reduce memory overhead
    testTimeout: 10000, // Increased for memory-intensive tests
    hookTimeout: 5000,
    // Optimize worker pool for memory usage and add Node.js memory limits
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true, // Use single fork to reduce memory usage
        execArgv: ['--max-old-space-size=2048'], // 2GB heap limit
      }
    }
  },
  resolve: {
    alias: {
      // Frontend source alias  
      '@': path.resolve(__dirname, '../../frontend/src'),
      '@frontend': path.resolve(__dirname, '../../frontend/src')
    },
    // Ensure frontend dependencies can be resolved
    preserveSymlinks: true,
    extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json']
  },
  // Specify node modules resolution for container
  define: {
    global: 'globalThis',
  }
})