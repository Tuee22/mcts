/// <reference types="vitest" />
import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  test: {
    // Enable globals for vi, describe, it, expect
    globals: true,
    
    // Use jsdom environment for DOM testing
    environment: 'jsdom',
    
    // Setup file for test configuration
    setupFiles: ['./tests/frontend/setup/vitest.setup.ts'],
    
    // Include patterns for test discovery
    include: ['tests/frontend/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    
    // Exclude patterns
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/cypress/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build,eslint,prettier}.config.*'
    ],
    
    // Test timeout settings
    testTimeout: 10000,
    hookTimeout: 10000,
    
    // Coverage settings
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'coverage/**',
        'dist/**',
        '**/node_modules/**',
        '**/.{idea,git,cache,output,temp}/**',
        '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build,eslint,prettier}.config.*',
        'tests/**'
      ]
    },
    
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
      '@': resolve(__dirname, './frontend/src'),
      '@/components': resolve(__dirname, './frontend/src/components'),
      '@/services': resolve(__dirname, './frontend/src/services'),
      '@/store': resolve(__dirname, './frontend/src/store'),
      '@/types': resolve(__dirname, './frontend/src/types'),
      '@/utils': resolve(__dirname, './frontend/src/utils')
    }
  },

  // Ensure we use the frontend's node_modules for resolution
  server: {
    deps: {
      // Externalize these dependencies during testing
      external: ['react', 'react-dom'],
      
      // Include these for processing
      include: ['@testing-library/*', 'vitest']
    }
  },
  
  // Define global types
  define: {
    // Ensure we're in test mode
    'process.env.NODE_ENV': '"test"'
  }
})