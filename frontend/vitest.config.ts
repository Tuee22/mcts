/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  esbuild: {
    jsx: 'automatic',
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
      // Exclude performance tests by default (run separately)
      '**/performanceEdgeCases.test.*'
    ],
    
    // Test timeout settings - increased for memory-intensive tests
    testTimeout: 15000,
    hookTimeout: 10000,
    
    // Pool options for better performance and memory management
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true, // Use single fork to reduce memory usage
        execArgv: ['--max-old-space-size=2048'], // 2GB heap limit
      }
    },
    
    // Retry failed tests
    retry: 0,
    
    // Bail after first failure for faster feedback during development
    bail: 0,
    
    // Memory and performance optimizations
    logHeapUsage: false,
    
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