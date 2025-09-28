// Use ES modules with dynamic imports to handle module resolution
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

// Use absolute paths to resolve modules from the build directory
const vitestPath = '/opt/mcts/frontend-build/node_modules/vitest/dist/config.js';
const reactPluginPath = '/opt/mcts/frontend-build/node_modules/@vitejs/plugin-react/dist/index.js';

let defineConfig, react;

try {
  const vitestModule = await import(vitestPath);
  defineConfig = vitestModule.defineConfig;
} catch (error) {
  console.error('Failed to import vitest config:', error);
  process.exit(1);
}

try {
  const reactModule = await import(reactPluginPath);
  react = reactModule.default;
} catch (error) {
  console.warn('Failed to import react plugin:', error);
  react = () => ({});
}

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
    globals: true,
    environment: 'jsdom',
    setupFiles: ['/app/frontend/setupTests.ts'],
    include: [
      '/app/frontend/tests/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/build/**',
      '**/coverage/**',
      '**/cypress/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build,eslint,prettier}.config.*'
    ],
    testTimeout: 15000,
    hookTimeout: 10000,
    teardownTimeout: 5000,

    // Improved test isolation settings
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: false, // Enable proper process isolation
        execArgv: ['--max-old-space-size=4096', '--expose-gc'],
        maxWorkers: 2, // Allow limited parallelization
        minWorkers: 1,
      }
    },

    // Mock and state management
    restoreMocks: true, // Automatically restore mocks between tests
    clearMocks: true,   // Clear mock state between tests
    resetMocks: false,  // Don't reset implementation, just state
    mockReset: false,   // Keep manual control over mock resets

    retry: 0,
    bail: 0,
    logHeapUsage: true,
    isolate: true, // Keep test isolation enabled
    watch: false,

    // Test execution settings
    sequence: {
      concurrent: false, // Disable concurrent execution for now
      shuffle: false,    // Keep deterministic order
      hooks: 'stack',    // Run hooks in stack order
    },

    // Module resolution
    deps: {
      moduleDirectories: [
        'node_modules',
        '/opt/mcts/frontend-build/node_modules'
      ],
      optimizer: {
        web: {
          // External dependencies that should not be bundled
          exclude: [
            'react',
            'react-dom',
            '@testing-library/react',
            '@testing-library/dom'
          ]
        }
      }
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      include: ['/app/frontend/src/**/*.{ts,tsx}'],
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
    reporters: ['default']
  },
  resolve: {
    alias: {
      '@': '/app/frontend/src',
      '@/components': '/app/frontend/src/components',
      '@/services': '/app/frontend/src/services',
      '@/store': '/app/frontend/src/store',
      '@/types': '/app/frontend/src/types',
      '@/utils': '/app/frontend/src/utils',
      // Map common dependencies to the build directory
      'react': '/opt/mcts/frontend-build/node_modules/react',
      'react-dom': '/opt/mcts/frontend-build/node_modules/react-dom',
      // Map testing library modules to the build directory
      '@testing-library/react': '/opt/mcts/frontend-build/node_modules/@testing-library/react',
      '@testing-library/dom': '/opt/mcts/frontend-build/node_modules/@testing-library/dom',
      '@testing-library/user-event': '/opt/mcts/frontend-build/node_modules/@testing-library/user-event',
      // Map other dependencies to the build directory
      'react-hot-toast': '/opt/mcts/frontend-build/node_modules/react-hot-toast',
      'zustand': '/opt/mcts/frontend-build/node_modules/zustand',
      'axios': '/opt/mcts/frontend-build/node_modules/axios',
      'socket.io-client': '/opt/mcts/frontend-build/node_modules/socket.io-client',
      // Map test dependencies
      '@vitest/coverage-v8': '/opt/mcts/frontend-build/node_modules/@vitest/coverage-v8'
    },
    extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json'],
    // Tell Vite where to find node_modules
    preserveSymlinks: false
  },

  // Vite config to specify module directories
  optimizeDeps: {
    include: ['react', 'react-dom']
  },

  // Specify custom node_modules location
  cacheDir: '/opt/mcts/frontend-build/.vite',
  define: {
    'process.env.NODE_ENV': '"test"',
    global: 'globalThis',
  }
});