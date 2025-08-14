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
      // Map React dependencies to main frontend
      'react': path.resolve('../../frontend/node_modules/react'),
      'react-dom': path.resolve('../../frontend/node_modules/react-dom'),
      '@testing-library/react': path.resolve('../../frontend/node_modules/@testing-library/react'),
      'zustand': path.resolve('../../frontend/node_modules/zustand'),
      'react-hot-toast': path.resolve('../../frontend/node_modules/react-hot-toast'),
      'socket.io-client': path.resolve('../../frontend/node_modules/socket.io-client'),
      // Frontend source alias
      '@frontend': path.resolve('../../frontend/src'),
      // CSS modules
      '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
    }
  }
})