/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./setupTests.ts'],
    globals: true,
    css: true,
    // NO exclude array - run ALL tests
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      exclude: [
        'node_modules/',
        'setupTests.ts',
        '**/*.d.ts',
        'mocks/',
        'coverage/',
        'build/',
        'dist/'
      ]
    }
  },
  resolve: {
    alias: {
      // Frontend source alias  
      '@frontend': path.resolve('../../frontend/src'),
      // CSS modules
      '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
    }
  }
})