/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  // Sicherungsliste für die Palette.
  //
  // Tailwind liefert nur aus, was im Quelltext VORKOMMT. Am 2026-08-26
  // gemessen: `bg-secondary-500` stand in keiner ausgelieferten CSS, weil die
  // Anwendung die Signalfarbe kaum als Fläche benutzt. Für die Anwendung ist
  // das richtig — für das Design-System nach claude.ai/design ist es eine
  // Falle: der Agent baut damit neue Oberflächen und schreibt Klassen, die
  // ins Leere laufen; das Ergebnis ist stillschweigend ungestylt.
  //
  // Deshalb steht die volle Palette hier fest drin. Kosten gemessen: siehe
  // .design-sync/NOTES.md.
  safelist: [
    { pattern: /^(bg|text|border|ring|from|to|via)-(primary|secondary)-(50|100|200|300|400|500|600|700|800|900|950)$/ },
    // Die Schrift-Utilities kommen in der Anwendung nicht vor (sie setzt die
    // Familien ueber h1..h6 im Basis-CSS). Der Design-Agent braucht sie aber,
    // um eigene Ueberschriften zu bauen — ohne Sicherungsliste laeuft
    // `font-display` ins Leere. Am 2026-08-26 genau so gemessen.
    'font-display', 'font-sans', 'font-mono', 'tabular-nums',
    // Zustandsvarianten brauchen `variants`, nicht das Präfix im Muster —
    // mit `hover:` im Muster erzeugt Tailwind nichts (am 2026-08-26 gemessen).
    {
      pattern: /^(bg|text|border)-(primary|secondary)-(100|200|300|400|500|600|700|800)$/,
      variants: ['hover', 'focus', 'active', 'dark'],
    },
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // ── Palette „Adria", 2026-08-25 ───────────────────────────────
        //
        // Vorher: Indigo #6366F1 + Amber #F59E0B — die Vorgabefarben, die
        // jede zweite Anwendung traegt. Sie sind hier zusaetzlich falsch:
        // der eigentliche Inhalt dieser App sind FOTOS und KARTEN, und ein
        // lautes Indigo kaempft mit beidem — mit jedem Bild und mit den
        // beige-gruenen OSM-Kacheln.
        //
        // primary: Tiefsee-Teal. Tritt neben Fotos und Kartenkacheln zurueck,
        // statt mit ihnen zu konkurrieren.
        primary: {
          50: '#ECF6F6',
          100: '#D2E9E9',
          200: '#A6D3D4',
          300: '#71B6B8',
          400: '#429799',
          500: '#1F7A7D',
          600: '#146264',
          700: '#124F51',
          800: '#123F41',
          900: '#123436',
          950: '#071F20',
        },
        // secondary: Signalorange — die Farbe, die auf einer Karte eine
        // ROUTE hat. Sparsam einsetzen; sie ist der einzige laute Ton.
        //
        // 🔴 Gemessen (WCAG): weisse Schrift auf secondary-500 ergibt nur
        // 3,82:1 — das reicht nur fuer grosse Schrift. Wo Weiss darauf
        // steht, gehoert 600 (#B34C22, 5,28:1) hin, nicht 500.
        secondary: {
          50: '#FDF3EE',
          100: '#FAE3D7',
          200: '#F4C4AC',
          300: '#EC9E78',
          400: '#E27B4B',
          500: '#D2612F',
          600: '#B34C22',
          700: '#8F3C1D',
          800: '#71321C',
          900: '#5C2B1A',
          950: '#31140B',
        }
      },
      // Schriften werden SELBST AUSGELIEFERT (siehe styles/index.css).
      // Vorher kamen Inter und Poppins von fonts.googleapis.com — in einer
      // App, die offline funktionieren soll, ist das die falsche Abhaengigkeit:
      // beim ersten Aufruf ohne Netz gibt es keine Schrift.
      //
      // Public Sans: neutrale Grotesk fuer die Oberflaeche, mit
      //   Tabellenziffern fuer das Budget. Bewusst NICHT Inter.
      // Newsreader: redaktionelle Serifenschrift mit optischen Groessen —
      //   ein Reisetagebuch ist ein Lesetext, keine Systemsteuerung.
      fontFamily: {
        sans: ['"Public Sans Variable"', 'system-ui', 'sans-serif'],
        display: ['"Newsreader Variable"', 'Georgia', 'serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'bounce-slow': 'bounce 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      boxShadow: {
        'soft': '0 2px 15px rgba(0, 0, 0, 0.05)',
        'soft-lg': '0 4px 25px rgba(0, 0, 0, 0.08)',
      },
      // Engere Radien: eine Reise-App ist ein Werkzeug, kein Spielzeug.
      // 1rem an einer Karte laesst sie wie eine Kachel aussehen; 0,625rem
      // laesst das Foto darin die Form bestimmen.
      borderRadius: {
        'xl': '0.625rem',
        '2xl': '0.875rem',
        '3xl': '1.25rem',
      },
    },
  },
  plugins: [],
}
