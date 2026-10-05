import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default [
  {
    ignores: ['dist', 'node_modules', 'build', '.vite']
  },
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      // 'latest' so class fields (ErrorBoundary) parse; esbuild/Vite transpile them
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.es2020
      },
      parserOptions: {
        ecmaFeatures: {
          jsx: true
        }
      }
    },
    settings: {
      react: {
        version: 'detect'
      }
    },
    plugins: {
      react,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh
    },
    rules: {
      ...react.configs.recommended.rules,
      ...react.configs['jsx-runtime'].rules,
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true }
      ],
      'react/prop-types': 'off',
      'react/react-in-jsx-scope': 'off'
    }
  },
  {
    // Build/tool configs are executed by Node, not in the browser
    files: ['*.config.js'],
    languageOptions: {
      globals: {
        ...globals.node
      }
    }
  },
  {
    // Test helpers and specs are never hot-reloaded, so the Fast Refresh
    // export rule does not apply to them
    files: ['src/test/**/*.{js,jsx}', '**/*.test.{js,jsx}'],
    rules: {
      'react-refresh/only-export-components': 'off'
    }
  }
]
