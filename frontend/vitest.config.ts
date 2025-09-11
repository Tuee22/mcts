/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import { resolve } from 'path'

export default defineConfig({
  test: {
    // Enable globals for vi, describe, it, expect
    globals: true,
    
    // Use jsdom environment for DOM testing
    environment: 'jsdom',
    
    // Setup file for test configuration
    setupFiles: ['./vitest.setup.ts'],
    
    // Include patterns for test discovery - supports tests in both frontend/ and tests/frontend/
    include: [
      '**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}',
      '../tests/frontend/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],
    
    // Exclude patterns - be more specific to avoid node_modules tests
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/cypress/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build,eslint,prettier}.config.*',
      '../tests/frontend/node_modules/**'
    ],
    
    // Test timeout settings
    testTimeout: 10000,
    hookTimeout: 10000,
    
    // Pool options for better performance
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true
      }
    },
    
    // Retry failed tests
    retry: 0,
    
    // Bail after first failure for faster feedback during development
    bail: 0
  },
  
  // Module resolution
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@/components': resolve(__dirname, './src/components'),
      '@/services': resolve(__dirname, './src/services'),
      '@/store': resolve(__dirname, './src/store'),
      '@/types': resolve(__dirname, './src/types'),
      '@/utils': resolve(__dirname, './src/utils')
    }
  },

  // Define global types
  define: {
    // Ensure we're in test mode
    'process.env.NODE_ENV': '"test"'
  }
})