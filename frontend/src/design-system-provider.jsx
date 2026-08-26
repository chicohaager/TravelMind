/**
 * Der Kontext, den TravelMind-Komponenten zum Rendern brauchen.
 *
 * Angelegt am 2026-08-25 für den Sync nach claude.ai/design. Beim ersten
 * Prüflauf warfen 21 von 35 Vorschauen genau drei Fehler:
 *
 *   No QueryClient set, use QueryClientProvider to set one
 *   useNavigate() may be used only in the context of a <Router>
 *   (und stillschweigend: kein i18n → rohe Schlüssel statt Wörter)
 *
 * Das ist kein Fehler der Komponenten — es ist der Kontext, den die
 * Anwendung sonst in `main.jsx` und `App.jsx` aufspannt. Hier steht er
 * einmal, damit jede Vorschau ihn bekommt.
 *
 * Bewusst MemoryRouter statt BrowserRouter: eine Vorschaukarte hat keine
 * Adresszeile, und BrowserRouter würde die des umgebenden Fensters lesen.
 *
 * `retry: false` und `staleTime: Infinity`: eine Karte soll nicht dreimal
 * gegen eine API laufen, die es dort nicht gibt — sie soll sofort das
 * rendern, was ohne Daten zu sehen ist.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { MotionConfig } from 'framer-motion'
import { I18nextProvider } from 'react-i18next'
import i18n from './i18n'
import { AuthProvider } from './contexts/AuthContext'

const abfrageklient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, staleTime: Infinity, refetchOnWindowFocus: false, gcTime: Infinity },
    mutations: { retry: false },
  },
})

export default function DesignSystemProvider({ children }) {
  return (
    // `reducedMotion="always"` allein reicht NICHT.
    //
    // Nicht aus Geschmack: 14 Komponenten starten mit `initial={{ opacity: 0 }}`
    // und blenden sich ein. Eine statische Aufnahme trifft sie dann im
    // unsichtbaren Moment — am 2026-08-25 gemessen: die PlaceCard-Karte
    // rendert einwandfrei (58 KB PNG), der Einzelzellen-Bogen war LEER.
    // framer-motion behandelt Opazität als "sichere" Animation und schaltet
    // sie bei reduzierter Bewegung NICHT ab — gemessen am 2026-08-26: die
    // Zelle hatte Inhalt im DOM (`r0len=172`), aber `opacity: "0"` im
    // berechneten Stil, und das Bild kam mit 3339 Byte weiss heraus.
    // Deshalb zusaetzlich die Regel unten: sie schlaegt den Inline-Stil, den
    // framer-motion setzt.
    // Wer die Bewegung sehen will, sieht sie in der laufenden App.
    <MotionConfig reducedMotion="always">
      <style>{`
        /* Nur fuer Vorschaukarten: was framer-motion einblendet, ist hier
           sofort da. Ein statisches Bild kann keine Einblendung abwarten. */
        [style*="opacity"] { opacity: 1 !important; }
        *, *::before, *::after { animation-duration: 0s !important; transition-duration: 0s !important; }
      `}</style>
      <QueryClientProvider client={abfrageklient}>
        <I18nextProvider i18n={i18n}>
          <MemoryRouter initialEntries={['/']}>
            {/* AuthProvider MUSS innerhalb von QueryClientProvider und Router
              liegen: er ruft useQueryClient (zum Leeren beim Kontowechsel)
              und arbeitet mit der Navigation. Ohne Token meldet er sich
              schlicht als abgemeldet — genau der Zustand, den eine
              Vorschaukarte zeigen soll. */}
            <AuthProvider>{children}</AuthProvider>
          </MemoryRouter>
        </I18nextProvider>
      </QueryClientProvider>
    </MotionConfig>
  )
}
