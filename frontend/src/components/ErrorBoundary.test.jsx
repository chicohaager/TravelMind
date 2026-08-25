/**
 * ErrorBoundary Component Tests
 */

import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { render, screen } from '@/test/utils'
import i18n from '@/i18n'
import ErrorBoundary from './ErrorBoundary'

// Component that throws an error
function ThrowError({ shouldThrow }) {
  if (shouldThrow) {
    throw new Error('Test error')
  }
  return <div>No error</div>
}

describe('ErrorBoundary', () => {
  // i18next ausdruecklich auf eine bekannte Sprache setzen, damit dieser Test
  // nicht davon abhaengt, ob eine andere Datei die Instanz vorher geladen hat.
  beforeAll(async () => {
    await i18n.changeLanguage('de')
  })

  // Suppress console.error for these tests
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    )

    expect(screen.getByText('Child content')).toBeInTheDocument()
  })

  it('renders error fallback when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    // Erwartet wird die UEBERSETZUNG, nicht der hartkodierte Fallback.
    //
    // Vorher stand hier /schiefgelaufen/i — der zweite Parameter von
    // t('errors:generic', 'Etwas ist schiefgelaufen'). Der Test bestand nur,
    // solange i18next in dieser Datei gar nicht initialisiert war; sobald eine
    // andere Testdatei die Instanz laedt, greift die echte Uebersetzung und der
    // Text lautet anders. Ein Test, der vom Ladezustand einer anderen Datei
    // abhaengt, prueft nicht das Verhalten der Anwendung.
    expect(screen.getByText(i18n.t('errors:generic'))).toBeInTheDocument()
  })

  it('renders retry button in error state', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText(/erneut versuchen/i)).toBeInTheDocument()
  })

  it('renders home button in error state', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText(/startseite/i)).toBeInTheDocument()
  })
})
