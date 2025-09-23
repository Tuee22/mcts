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
    setupFiles: ['./setupTests.ts'],
    include: [
      'tests/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/build/**',
      '**/coverage/**',
      '**/cypress/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build,eslint,prettier}.config.*',
      ...(process.env.INCLUDE_PERFORMANCE_TESTS !== 'true' ? ['**/performanceEdgeCases.test.*'] : [])
    ],
    testTimeout: 20000,
    hookTimeout: 15000,
    teardownTimeout: 5000,
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true,
        execArgv: ['--max-old-space-size=8192', '--expose-gc'],
        maxWorkers: 1,
      }
    },
    retry: 0,
    bail: 0,
    logHeapUsage: true,
    isolate: true,
    watch: false,
    deps: {
      moduleDirectories: [
        'node_modules',
        '/opt/mcts/frontend-build/node_modules'
      ]
    },
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
      'socket.io-client': '/opt/mcts/frontend-build/node_modules/socket.io-client'
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