import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default [
  {
    // Erzeugtes wird NICHT geprueft.
    //
    // Bis 2026-08-25 fehlten hier html/ und dev-dist/. `npx eslint .` meldete
    // deshalb 440 Fehler, von denen 377 in gebauten Buendeln standen — 320
    // allein in html/assets/index-*.js. Ein Gate, das immer rot ist, wird
    // weggeklickt; danach schuetzt es auch dort nicht mehr, wo es recht haette.
    ignores: [
      'dist',
      'dev-dist',
      'html',
      'build',
      'node_modules',
      '.vite',
      'coverage',
      'playwright-report',
      'test-results',
      'public/**/*.js',
    ],
  },
  js.configs.recommended,
  {
    // Werkzeug-Konfiguration laeuft in Node, nicht im Browser: __dirname und
    // process sind dort definiert. Ohne diesen Block meldete eslint 16 Fehler
    // fuer korrekten Code.
    files: ['*.config.js', 'vite.config.js', 'vitest.config.js', 'playwright.config.ts'],
    languageOptions: {
      globals: { ...globals.node },
    },
  },
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      // 'latest' statt 2020: ErrorBoundary.jsx nutzt Klassenfelder
      // (`state = { … }`), die ecmaVersion 2020 nicht kennt. eslint konnte die
      // Datei deshalb nicht parsen und hat sie ohne weiteren Hinweis
      // uebersprungen — eine Datei, die nie geprueft wurde, waehrend das Gate
      // gruen meldete.
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
      'react/react-in-jsx-scope': 'off',
      // Absichtlich ungenutztes wird mit _ markiert — sichtbar im Code, statt
      // die Regel abzuschalten. Die Ausnahme ist damit enger als die Regel:
      // sie deckt nur, was jemand ausdruecklich so benannt hat.
      'no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ]
    }
  }
]
