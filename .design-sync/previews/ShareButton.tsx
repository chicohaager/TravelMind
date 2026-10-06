import { ShareButton } from 'travelmind-frontend'

/**
 * Der Knopf ist absichtlich nur ein Symbol — allein auf einer Karte lehrt er
 * aber niemanden, wozu er da ist. Deshalb hier im Zusammenhang, so wie er in
 * der Kopfzeile einer Reise steht. Das Menü klappt erst beim Klick auf und
 * ist statisch nicht darstellbar.
 */
export const InDerKopfzeile = () => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '1rem',
      padding: '0.75rem 1rem',
      border: '1px solid #D2E9E9',
      borderRadius: '0.625rem',
      background: '#fff',
      maxWidth: 520,
    }}
  >
    <div>
      <div style={{ fontFamily: '"Newsreader Variable", Georgia, serif', fontSize: '1.25rem', fontWeight: 600 }}>
        Herbst in Porto
      </div>
      <div style={{ fontSize: '0.875rem', color: '#5b6b6b' }}>01.–08. Oktober 2026 · Porto</div>
    </div>
    <ShareButton url="https://travelmind.example/share/abc123" title="Herbst in Porto" />
  </div>
)

/** Der Knopf allein — so, wie er in eine bestehende Werkzeugleiste passt. */
export const Alleinstehend = () => (
  <ShareButton url="https://travelmind.example/share/abc123" title="Herbst in Porto" />
)
