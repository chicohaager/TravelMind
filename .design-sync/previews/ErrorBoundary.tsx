import { ErrorBoundary } from 'travelmind-frontend'

/** Im Normalfall unsichtbar: er reicht die Kinder einfach durch. */
export const Standard = () => (
  <ErrorBoundary>
    <p style={{ margin: 0 }}>Alles in Ordnung — dieser Inhalt kommt unverändert durch.</p>
  </ErrorBoundary>
)

/**
 * Der eigentliche Zweck: eine Komponente wirft, und statt einer weißen Seite
 * steht eine Meldung da. `Kaputt` wirft beim ersten Rendern.
 */
const Kaputt = () => {
  throw new Error('Beispiel: diese Komponente ist abgestürzt')
}

export const NachEinemFehler = () => (
  <ErrorBoundary>
    <Kaputt />
  </ErrorBoundary>
)
