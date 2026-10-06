# Änderungen

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [SemVer](https://semver.org/lang/de/).

Die Version steht an **drei** Stellen und muss zusammen wandern:
`frontend/package.json`, `backend/main.py` (`version=`) und die Fußzeile in
`frontend/src/components/layout/Sidebar.jsx`. Ein Test hält das fest —
auseinandergelaufene Versionsangaben sind der Grund, warum eine
Fehlermeldung aus dem Betrieb sich nicht zuordnen lässt.

---

## [Unveröffentlicht]

### Geändert

- **Node 24 LTS** statt Node 20 (Supportende 30.04.2026) in `Dockerfile`,
  `Dockerfile.prod` und CI; `engines.node` jetzt `>=24.0.0`. Aus `main`
  (PR #3) übernommen.
- **`docker-compose.hub.yml` zurück**, passend zu diesem Stand: Backend auf
  8137 ohne veröffentlichten Port (nginx leitet weiter), Gesundheitsprüfung
  `/api/health/live`, benannte Volumes statt Bind-Mounts (aus PR #6),
  `JWT_SECRET`/`SECRET_KEY` scheitern laut, wenn sie fehlen.
- **Workflow „Production Images“** (`deploy.yml`, aus PR #4): baut die
  Produktions-Images, schiebt sie auf `main` und bei `v*`-Tags nach GHCR.
  Kein Server-Deploy — das bleibt `deploy/ausrollen.sh`.
- **tailwindcss 4.3.3** statt 3.4.19 (`@tailwindcss/postcss` statt
  `tailwindcss` + `autoprefixer`). Grund: `npm audit` meldete 7 Befunde, die
  nur an tailwind 3 hingen — `braces` hat keine gepatchte Version
  (GHSA-vfj7-8cjw-p6xm). Jetzt 0 Befunde.
  **Neue Browser-Mindestversionen:** Chrome 111, Safari 16.4, Firefox 128
  (laut tailwindcss.com/docs/compatibility). Ältere Browser bekommen die
  Oberfläche nicht mehr vollständig gestaltet.
  Das Aussehen ist unverändert: 52 Screenshot-Paare (13 Ansichten × hell/dunkel
  × Desktop/Handy) vorher/nachher verglichen, 47 pixelgleich, die übrigen nur
  mit Rundungsabweichungen oder dem Kartenrauschen, das auch zwei Läufe
  desselben Stands zeigen. Dafür nötig waren:
  - `tailwind.compat-v3.js`: Standardpalette und Schriftgrößen von v3 (v4 hat
    die Farben auf oklch umgestellt und Zeilenhöhen relativ gemacht),
  - Kompatibilitätsregeln in `styles/index.css` (Rahmenfarbe, Platzhalter,
    Knopf-Zeiger, Ziffernform und Hintergrund in Formularfeldern, Datumsfelder,
    `space-x/y` mit v3-Semantik, Dunkelmodus per `@custom-variant` mit
    v3-Selektor, eigene Regeln und `mobile.css` in `@layer utilities`),
  - Verläufe mit `/srgb` (v4 interpoliert sonst in oklab),
  - Schrift-Imports in `main.jsx` statt `@import` in `index.css` — sonst
    fehlten alle Schriftdateien im Build,
  - `safelist` als `@source inline(…)` — v4 liest `safelist` nicht mehr.

## [1.1.0] — 2026-08-25

Ein Tag Instandsetzung vor einer Reise. Die Anwendung war seit dem 26. Juni
abgeschaltet, ohne dass es jemandem aufgefallen wäre; danach wurde jede
Behauptung über sie nachgemessen. Der Ertrag sind nicht die Tests — es sind
die Fehler, die dabei herausfielen.

### Behoben — Datenverlust und tote Funktionen

- **Das Löschen einer Ortsliste löschte alle Orte darin.** Der
  Bestätigungsdialog versprach wörtlich das Gegenteil. Die Datenbankregel
  sagte `SET NULL`, die ORM-Kaskade kam ihr zuvor.
- **Die drei DSGVO-Endpunkte haben nie funktioniert** — Datenmitnahme
  (Art. 20) und Löschantrag (Art. 17) antworteten auf jeden Aufruf mit 422.
  Ein Parameter ohne Typangabe wurde zum Pflicht-Query-Parameter.
- **Kein Foto über 1 MB war hochladbar.** `client_max_body_size` fehlte in
  nginx, es galt der Standard von 1 MB — ein Handyfoto hat 2–5 MB.
- **Jede Claude-Anfrage scheiterte** seit dem Initial-Commit: der
  anthropic-SDK nimmt `temperature` nicht mehr an. Dazu ein Folgefehler —
  die aktuellen Modelle denken adaptiv, `content[0].text` gibt es dann nicht.
- **Alle vier KI-Modell-IDs waren veraltet**, die von Groq (dem kostenlosen
  Standardanbieter) stand nicht mehr im Angebot.
- **`IconSelector` war nicht darstellbar** — importierte ein lucide-Symbol,
  das es in der installierten Version nicht gibt.
- **Die tägliche Sicherung war stillgelegt** — das Deploy-Skript löschte das
  bind-gemountete Skriptverzeichnis; die laufenden Container sahen ein leeres
  `/skripte`.
- **`/api/health` stürzte auf 500 ab**, wenn eine Teilprüfung warf — der
  Ausfall nahm die Auskunft mit, die sagen soll, was ausgefallen ist.

### Behoben — Sicherheit und Datenschutz

- **Der API-Schlüssel des Nutzers stand in KI-Fehlermeldungen** (zehn
  Stellen in `routes/ai.py`, dazu die Schlüsselprüfung). Anbieter schreiben
  ihn in ihre Meldung; er landete damit in der HTTP-Antwort, in den
  Entwicklerwerkzeugen und im Proxy-Protokoll.
- **Ein Kontowechsel ohne Neuladen zeigte die Daten des vorigen Kontos.**
  Auf geteilten Rechnern ein Leseloch ohne Token.
- **Hinter einem Reverse Proxy zählten alle Besucher als einer** — die
  Ratenbegrenzung hätte den getroffen, der nichts falsch gemacht hat.

### Behoben — Oberfläche

- **18 rohe i18n-Schlüssel** waren sichtbar (`diary.moodHappy` statt
  „Glücklich"), dazu 25 Beschriftungen, die nie durch `t()` liefen —
  darunter drei fest **deutsche**, die ein englischer Nutzer zu sehen bekam.
- **Sprachwahl, Dunkelmodus und Abmelden lagen auf dem Handy außerhalb des
  Bildschirms** und waren damit nicht erreichbar.
- **„Route speichern" wirkte tot** — Orte kamen nur per Ziehen hinein.

### Geändert

- **Gestaltung „Adria"**: Tiefsee-Teal statt Indigo, Signalorange statt
  Amber, Newsreader + Public Sans statt Poppins + Inter. Die Kontraste sind
  gerechnet, nicht geschätzt. Schriften werden selbst ausgeliefert — vorher
  kamen sie von Google und hätten offline gefehlt.
- **Übersetzungen werden nachgeladen**: index-Chunk 227 → 103 kB, beim
  Erstaufruf 2 Anfragen statt 57.
- Der Inhalt darf auf breiten Schirmen atmen (bis 1800 px, vierte Spalte).

### Betrieb

- Sicherung mit **Restore-Probe** nach jedem Lauf, Wächter mit Alarm,
  Deploy-Skript mit Rückweg.
- Coverage 53 % → **75,3 %**, 71 → 492 Tests; CI-Schranke von 50 auf 75.
- Frontend: 90 Tests, darunter Wächter gegen ganze Fehlerklassen (i18n,
  Gestaltungs-Token, Symbol-Importe, Barrierefreiheit, SDK-Signaturen).

### Bekannt und offen

- Die Sicherung liegt auf **derselben Platte** wie die Daten (3-2-1 nicht
  erfüllt).
- `google.generativeai` ist abgekündigt; die Umstellung auf `google.genai`
  steht aus.
- Die Auflösung der Client-IP hinter Pangolin ist konfiguriert, aber erst
  LAN-seitig gemessen.

---

## [1.0.0] — 2025-11-01

Erste Fassung.
