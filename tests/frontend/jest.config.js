/** @type {import('jest').Config} */
module.exports = {
  // Test environment
  testEnvironment: 'jsdom',
  
  // Setup files (commented out for smoke test)
  // setupFilesAfterEnv: [
  //   '<rootDir>/setupTests.ts'
  // ],
  
  // Module name mapping for assets and CSS
  moduleNameMapper: {
    '^../../../frontend/src/(.*)$': '<rootDir>/../../frontend/src/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(gif|ttf|eot|svg|png|jpg|jpeg)$': '<rootDir>/mocks/fileMock.js'
  },
  
  // Test match patterns
  testMatch: [
    '<rootDir>/**/*.test.{js,jsx,ts,tsx}',
    '<rootDir>/**/__tests__/**/*.{js,jsx,ts,tsx}'
  ],
  
  // Coverage configuration
  collectCoverageFrom: [
    '../../frontend/src/**/*.{js,jsx,ts,tsx}',
    '!../../frontend/src/**/*.d.ts',
    '!../../frontend/src/index.tsx',
    '!../../frontend/src/reportWebVitals.ts'
  ],
  
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  
  // Transform configuration
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': [
      'babel-jest',
      {
        presets: [
          ['@babel/preset-env', { targets: { node: 'current' } }],
          ['@babel/preset-react', { runtime: 'automatic' }],
          '@babel/preset-typescript'
        ]
      }
    ]
  },
  
  // Module file extensions
  moduleFileExtensions: [
    'js',
    'jsx',
    'ts',
    'tsx',
    'json',
    'node'
  ],
  
  // Test timeout
  testTimeout: 10000,
  
  // Ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/build/',
    '/dist/'
  ],
  
  // Clear mocks between tests
  clearMocks: true,
  
  // Collect coverage on all runs
  collectCoverage: true,
  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  
  // Verbose output
  verbose: true,
  
  // Watch plugins for development (commented out until installed)
  // watchPlugins: [
  //   'jest-watch-typeahead/filename',
  //   'jest-watch-typeahead/testname'
  // ],
  
  // ESM support
  extensionsToTreatAsEsm: ['.ts', '.tsx'],
  
  // Module resolution
  moduleDirectories: ['node_modules', '<rootDir>/../../frontend/src'],
  
  // Global variables
  globals: {
    'ts-jest': {
      useESM: true
    }
  }
};