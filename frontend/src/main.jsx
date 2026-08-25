import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import App from './App.jsx'
import { initSentry } from './utils/sentry'
import { uebersetzungenBereit } from './i18n'
import './styles/index.css'
import './styles/mobile.css'

// Initialize Sentry error tracking (before app renders)
initSentry()

// Create a React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

// Die Uebersetzungen werden nachgeladen (siehe i18n.js). Ohne dieses Warten
// rendert React, bevor sie da sind, und `t('trips:title')` liefert so lange den
// SCHLUESSEL zurueck — auf dem Bildschirm stuende kurz `trips:title`. Genau die
// Klasse von stillem Fehler, gegen die `i18n-integrity.test.js` sonst waecht.
// `i18n.init()` gibt ein Promise zurueck, das erst aufloest, wenn die
// Namensraeume der erkannten Sprache geladen sind.
const wurzel = ReactDOM.createRoot(document.getElementById('root'))

const anwendungStarten = () =>
  wurzel.render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
          <Toaster
            position="top-center"
            toastOptions={{
              duration: 3000,
              style: {
                background: '#363636',
                color: '#fff',
                fontSize: '14px',
                padding: '12px 16px',
              },
              success: {
                iconTheme: {
                  primary: '#10B981',
                  secondary: '#fff',
                },
              },
              error: {
                iconTheme: {
                  primary: '#EF4444',
                  secondary: '#fff',
                },
              },
            }}
            containerStyle={{
              top: 70, // Below navbar
            }}
          />
        </BrowserRouter>
      </QueryClientProvider>
    </React.StrictMode>
  )

// Rendern, sobald die Uebersetzungen da sind. Faellt das Laden aus (kein Netz,
// kaputter Chunk), wird TROTZDEM gerendert — i18next liefert dann den
// englischen Fallback bzw. den Schluessel. Eine weisse Seite waere das
// schlechtere Ergebnis, und `catch` ist hier deshalb kein Verschlucken:
// der Fehler wird protokolliert und die Anwendung startet.
uebersetzungenBereit
  .catch((fehler) => {
    // Ein stiller Ausfall der Uebersetzungen ist genau der Fehler, der
    // monatelang niemandem auffaellt — deshalb laut ins Protokoll.
    console.error('Uebersetzungen konnten nicht geladen werden:', fehler)
  })
  .finally(anwendungStarten)
