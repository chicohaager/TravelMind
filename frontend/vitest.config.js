import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    // Use jsdom for DOM testing
    environment: 'jsdom',

    // Setup files run before each test file
    setupFiles: ['./src/test/setup.js'],

    // Include test files
    include: ['src/**/*.{test,spec}.{js,jsx}'],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{js,jsx}'],
      exclude: [
        'src/test/**',
        'src/**/*.test.{js,jsx}',
        'src/**/*.spec.{js,jsx}',
        'src/main.jsx',
        'src/vite-env.d.ts'
      ],
      // Coverage thresholds (enable after initial tests are written)
      // thresholds: {
      //   lines: 60,
      //   functions: 60,
      //   branches: 60,
      //   statements: 60
      // }
    },

    // Global test settings
    globals: true,

    // CSS handling
    css: true,

    // Reporter configuration
    reporters: ['default', 'html'],

    // Watch mode exclusions
    watchExclude: ['node_modules', 'dist'],

    // Pool configuration for parallel tests
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@services': path.resolve(__dirname, './src/services'),
      '@contexts': path.resolve(__dirname, './src/contexts'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@utils': path.resolve(__dirname, './src/utils')
    }
  }
})
