# design-sync — Notizen zu diesem Repo

## Was hier anders ist als bei einem üblichen Design-System

- **TravelMind ist eine Anwendung, keine Komponentenbibliothek.** `private: true`,
  kein `main`/`module`/`exports`, kein Bibliotheks-Build, kein Storybook.
  Der Einstiegspunkt ist deshalb `frontend/src/design-system.js` — eine
  **von Hand gepflegte Barrel-Datei**, die sagt, was das Design-System nach
  außen anbietet. Die Anwendung selbst importiert sie NICHT (Vite lädt jede
  Komponente einzeln, damit das Code-Splitting erhalten bleibt).
  🔴 **Neue Komponente unter `src/components/` ⇒ auch dort eintragen UND in
  `cfg.componentSrcMap`**, sonst fehlt sie im Sync.

- **Es gibt keine `.d.ts`-Dateien** (reines JavaScript). Der Konverter
  meldete beim ersten Lauf `[ZERO_MATCH]`. Deshalb ist `componentSrcMap`
  hier NICHT sparse, sondern vollständig — es ist die einzige Quelle, aus
  der die Komponentenliste kommt.

- **`jsconfig.json` in `frontend/` ist für den Sync da**, nicht für die
  Anwendung: esbuild löst die Aliase (`@components/…`) nur über
  `compilerOptions.paths` auf. Die Werte müssen mit `resolve.alias` in
  `vite.config.js` übereinstimmen.

- **Die CSS wird aus dem App-Build geholt.** `src/styles/index.css` enthält
  rohe `@tailwind`-Direktiven und taugt nicht als `cssEntry`. `cfg.buildCmd`
  baut die App und kopiert die kompilierte Datei nach
  `frontend/.ds-css/travelmind.css` — der Vite-Name trägt einen Hash und
  ändert sich bei jedem Bau.

- **Die Schriften kommen aus `node_modules/@fontsource-variable/*`**, nicht
  aus den gehashten dist-Assets: stabile Namen, und es sind dieselben
  Dateien, die die App ausliefert.

## Fork von lib/dts.mjs

`isComponentName` streicht im Original alles, was auf `Manager` endet — es
hält solche Namen für Hilfsobjekte. `ParticipantsManager` ist hier aber eine
ganz gewöhnliche React-Komponente. Ohne den Fork blieb sie im Bündel
importierbar, verlor aber Karte UND Typvertrag — und der Typvertrag ist
genau das, wogegen der Design-Agent programmiert.
`Placements` und `Context` bleiben ausgeschlossen.
🔴 Der Fork braucht `ln -sfn ../.ds-sync/node_modules .design-sync/node_modules`
(einmal pro Klon), sonst findet er `ts-morph` nicht.

## Provider

`frontend/src/design-system-provider.jsx` spannt den Kontext auf, den die
Anwendung sonst in `main.jsx`/`App.jsx` aufspannt. Beim ersten Prüflauf
warfen **21 von 35** Vorschauen Fehler; nach dem Provider waren es 5, und die
5 sind fehlende Props, keine Kontextfehler.

Reihenfolge ist nicht beliebig: `AuthProvider` MUSS innerhalb von
`QueryClientProvider` und `MemoryRouter` liegen — er ruft `useQueryClient`
und arbeitet mit der Navigation. `MemoryRouter` statt `BrowserRouter`, weil
eine Vorschaukarte keine Adresszeile hat.

## Known render warns

- `NotificationBell` — `[RENDER_THIN]`. Berechtigt: die Komponente ist ein
  Glockensymbol, mehr gibt es ohne Benachrichtigungen nicht zu zeigen.

## Browser für die Bildprüfung

Kein `~/.cache/ms-playwright` auf dieser Maschine, aber
`/usr/bin/google-chrome` ist da. `playwright` ist in `.ds-sync/` mit
`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` installiert; die Prüfung läuft mit

    DS_CHROMIUM_PATH=/usr/bin/google-chrome node .ds-sync/package-validate.mjs ./ds-bundle

Ohne diese Variable meldet validate `[RENDER_SKIPPED]` — kein Fehler des
Bündels, sondern ein fehlender Browser.

## Was beim Autorieren der Vorschauen gelernt wurde (2026-08-26)

### Typverträge mussten abgeleitet werden

Ohne `.d.ts` liefert der Konverter für jede Komponente
`[key: string]: unknown` — der Design-Agent wüsste nichts über die API.
`cfg.dtsPropsFor` ist deshalb hier **vollständig** gefüllt: die Prop-Namen
stammen aus der Destrukturierung in der Signatur (27 Komponenten haben sie),
die Datenformen (`place`, `entry`, `expense`, `day`, `trip`) aus den
SQLAlchemy-Modellen des Backends. Welche Props PFLICHT sind, steht nicht im
Quelltext — es steht im Render-Check: die Komponenten, die ohne sie mit
`Cannot read properties of undefined (reading 'category')` abstürzen.

🔴 **Neue Prop ⇒ `dtsPropsFor` nachziehen.** Es gibt keinen Mechanismus, der
das erzwingt; die Ableitung war einmalig.

### Vorschauen waren alle weiß — und die erste Diagnose war falsch

Erste Vermutung: framer-motion. `MotionConfig reducedMotion="always"`
eingebaut — der Bogen blieb leer. Gemessen statt vermutet: `r0len=172`
(Inhalt im DOM) bei `opacity: "0"` im berechneten Stil. framer-motion
behandelt Opazität als „sichere" Animation und schaltet sie bei reduzierter
Bewegung NICHT ab. Die Regel in `design-system-provider.jsx`
(`[style*="opacity"] { opacity: 1 !important }`) schlägt den Inline-Stil.
Ohne sie: 3339 Byte weiß statt 23212 Byte Karte.

### Bekannte Grenzen der Vorschaukarten

- **`ExpenseModal` und `AddToTimelineModal` zeigen ihren Kopf nicht.**
  Gemessen: das Modal steht bei `top: -276 px`, **unabhängig von der
  Fensterhöhe** (900/1300/1700 geprüft) — `position: fixed` löst in der
  Vorschau-Umgebung gegen einen transformierten Vorfahren auf, nicht gegen
  das Fenster. Kein Fehler der Komponente; in der Anwendung sitzt sie richtig.
- **`OfflineIndicator` hat bewusst KEINE autorierte Vorschau.** Der Streifen
  ist `position: fixed` am oberen Rand und ragt aus jeder Karte. Ein Versuch
  mit echtem `offline`-Ereignis lieferte nur einen roten Splitter. Die Floor
  Card ist ehrlicher als eine fast leere Karte.
- **`LanguageSwitcher`** zeigt nur den geschlossenen Zustand; die Liste
  braucht einen Klick.

## Known render warns

- `NotificationBell` — `[RENDER_THIN]`. Berechtigt: die Komponente ist ein
  Glockensymbol.
- `ErrorBoundary` — im Render-Check als `bad` geführt. **Fehlalarm meiner
  eigenen Absicht:** die Zelle `NachEinemFehler` lässt eine Beispielkomponente
  absichtlich werfen, damit die Karte den Fehlerbildschirm zeigt. Das PNG ist
  40 KB und korrekt. Wer den Warn entfernen will, müsste die Zelle streichen —
  und damit die aussagekräftigste Karte der Komponente.

## Dabei in der ANWENDUNG gefundene Fehler

Der Sync ist nicht nur Export — er hat drei echte Defekte sichtbar gemacht:

1. **`ColorPicker` zeigte „Choose custom color" und „Selected:" auf Englisch.**
   Der i18n-Wächter sah es nicht: er sucht Beschriftungen in *Props*, das hier
   war JSX-Text.
2. **`TimelineDay` und `BudgetView` trugen `from-blue-500 to-purple-600`** —
   die alte Palette, mitten in einer teal-farbenen Anwendung. Der
   Gestaltungs-Wächter sah es nicht: er suchte `indigo-*` und `#6366F1`.
   Beide behoben, und `design-tokens.test.js` prüft jetzt auch Verläufe.
3. **Die Kategorienskala der Karte** war die Tailwind-Vorgabe (#ef4444,
   #8b5cf6 …) und passte zu nichts. Ersetzt durch eine harmonisierte Familie,
   verankert auf primary-500 und secondary-500; ein Ton (`viewpoint`) wurde
   nachgedunkelt, weil er den Kontrast knapp verfehlte (2,98:1 → 3,44:1).

Nebenbefund, nicht behoben: `TimelineDay` schreibt **„1 Orte"** statt „1 Ort".

## Re-sync-Risiken

- **`frontend/src/design-system.js` ist von Hand gepflegt.** Eine neue
  Komponente erscheint nicht von selbst — sie muss dort UND in
  `cfg.componentSrcMap` stehen.
- **`cfg.dtsPropsFor` veraltet still.** Ändert sich eine Prop-Signatur, bleibt
  der Vertrag stehen und der Design-Agent programmiert gegen die alte API.
- **`frontend/.ds-css/travelmind.css` ist ein Abzug.** Wer die Gestaltung
  ändert und `cfg.buildCmd` nicht laufen lässt, synchronisiert die alte CSS.
- **Der Fork von `lib/dts.mjs`** muss bei einem Skill-Update gegen das Original
  gediffed werden; er hängt nur an einer Zeile (`Manager`-Endung).
- **Nur mit deutschem Gebietsschema geprüft.** Die Karten zeigen, was ein
  deutscher Nutzer sieht; en/fr/es sind im Bündel, aber nicht angesehen.
