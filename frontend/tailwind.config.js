/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
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
