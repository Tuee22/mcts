/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  esbuild: {
    jsx: 'automatic',
    target: 'esnext',
  },
  build: {
    target: 'esnext',
  },
  test: {
    // Enable globals for vi, describe, it, expect
    globals: true,
    
    // Use jsdom environment for DOM testing
    environment: 'jsdom',
    
    // Setup file for test configuration
    setupFiles: ['./setupTests.ts'],
    
    // Include patterns for test discovery - look in tests/
    include: [
      'tests/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],
    
    // Exclude patterns - be more specific to avoid node_modules tests
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/build/**',
      '**/coverage/**',
      '**/cypress/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build,eslint,prettier}.config.*',
      // Conditionally exclude performance tests unless env var set
      ...(process.env.INCLUDE_PERFORMANCE_TESTS !== 'true' ? ['**/performanceEdgeCases.test.*'] : [])
    ],
    
    // Test timeout settings - increased for memory-intensive tests
    testTimeout: 20000,
    hookTimeout: 15000,
    teardownTimeout: 5000,
    
    // Pool options for better performance and memory management
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true, // Use single fork to prevent memory issues
        execArgv: ['--max-old-space-size=8192', '--expose-gc'], // 8GB heap limit with garbage collection
        maxWorkers: 1, // Single worker to prevent memory exhaustion
      }
    },
    
    // Retry failed tests
    retry: 0,
    
    // Bail after first failure for faster feedback during development
    bail: 0,
    
    // Memory and performance optimizations
    logHeapUsage: true,
    isolate: true, // Isolate tests better
    watch: false, // Disable watch mode for stability

    // Configure module resolution for Docker environment
    deps: {
      moduleDirectories: [
        'node_modules',
        '/opt/mcts/frontend-build/node_modules'
      ]
    },

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'node_modules/',
        'build/',
        'dist/',
        'coverage/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/fixtures/**',
        '**/mocks/**'
      ],
      thresholds: {
        global: {
          branches: 70,
          functions: 70, 
          lines: 70,
          statements: 70
        }
      }
    },
    
    // Reporter configuration
    reporters: ['default']
  },
  
  // Module resolution - paths relative to frontend directory
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@/components': resolve(__dirname, './src/components'),
      '@/services': resolve(__dirname, './src/services'),
      '@/store': resolve(__dirname, './src/store'),
      '@/types': resolve(__dirname, './src/types'),
      '@/utils': resolve(__dirname, './src/utils'),
    },
    extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json']
  },

  // Define global types
  define: {
    // Ensure we're in test mode
    'process.env.NODE_ENV': '"test"',
    global: 'globalThis',
  }
})