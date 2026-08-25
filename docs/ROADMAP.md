# TravelMind — Stand und Weg zur professionellen App

**Erhoben am:** 2026-08-25 · **Branch:** `feat/photo-media` @ `d62d47b`
**Alle Zahlen in diesem Dokument sind an diesem Tag gemessen.** Das Kommando steht jeweils dabei.

---

## 1. Stand

### 1.1 Was steht

| Bereich | Messwert | Kommando |
|---|---|---|
| Backend | 15.404 Zeilen Python, 77 Dateien | `find backend -name '*.py' … \| wc -l` |
| API | 127 Endpunkte in 21 Route-Modulen, 136 Routen registriert | `grep -rhE '^@router\.(get\|post\|put\|patch\|delete)' backend/routes/*.py \| wc -l` |
| Frontend | 16.419 Zeilen, 58 JSX-Komponenten, 18 Seiten | `find frontend/src -type f … \| wc -l` |
| Backend-Tests | **53 grün** in 19,5 s | `venv/bin/python -m pytest backend/tests -q` |
| Backend-Coverage | **53 %** (5689 Statements, 2650 ungedeckt) | `pytest --cov=backend` |
| Frontend-Tests | 11 Unit-Tests in 2 Dateien, 16 E2E-Tests | `npx vitest run`, `grep -c 'test(' e2e/*.spec.ts` |
| Build | grün in 2,86 s, Code-Splitting aktiv, PWA 39 Precache-Einträge | `npm run build` |

Die Backend-Infrastruktur ist bereits auf professionellem Niveau — das ist kein Prototyp:
strukturiertes JSON-Logging (structlog), Sentry, Request-IDs, Metrics-Middleware,
Security-Header, zentrale Error-Handler, Alembic mit 5 Migrationen, Rate-Limiting auf
**72 von 127** Endpunkten, `Dockerfile.prod` als Multi-Stage-Build mit `USER travelmind`
und `HEALTHCHECK`.

### 1.2 Was nicht stimmt

#### 🔴 P0 — Die Produktion ist weg

Auf `<host>` existiert **kein einziger** TravelMind-Container. Nicht gestoppt — nicht vorhanden.

```
docker ps -a --format '{{.Names}}' | wc -l   → 36 Container
docker ps -a | grep -i travel                → (leer)
docker ps -a --filter status=exited          → nur zimaos-mcp-deployer
Port 8190                                    → nimmt keine Verbindung an
ping <host>                           → 0 % Verlust, 0,35 ms (Host lebt)
Ports 22 und 80                              → offen
```

Es ist mehr als „Container gestoppt". Die App ist vollständig deinstalliert:

```
ls /var/lib/casaos/apps/travelmind/     → No such file or directory  (CasaOS-Eintrag weg)
docker images | grep -i travel          → (leer)                     (Images weg)
ls -d /DATA/zfw                         → existiert, rules.json darin nicht mehr
```

Von 22 CasaOS-Apps auf dem Host ist TravelMind nicht mehr dabei. Zum Firewall-Eintrag sage ich
nichts — die Datei `/DATA/zfw/rules.json`, die meine Notiz vom Juni nennt, existiert nicht mehr;
ein „nicht gefunden" an einem Ort, an dem nichts mehr liegt, ist kein Befund.

**Die Daten sind unversehrt:** `/DATA/AppData/travelmind/{postgres,uploads,backups}`,
Uploads **104 MB**. Verloren sind Container, Images und die Registrierung — nicht die Reisen.

Das Muster (App-Eintrag weg + Images weg + Datenverzeichnis unangetastet) passt zu einer
Deinstallation über die ZimaOS-Oberfläche. **Gemessen ist der Zustand, nicht die Ursache** —
ich behaupte nicht, dass es so war.

Gemerkt hat es niemand: Es gibt keine Überwachung, die einen Ausfall meldet.

#### 🔴 P0 — Der Branch hat die Release-Infrastruktur gelöscht

Commit `f82d006` *„chore: remove obsolete docs, CI/CD configs, Docker and helper scripts"*
entfernt **38 Dateien** gegenüber `origin/main`:

```
git diff --name-status origin/main HEAD | grep '^D' | wc -l   → 38
```

Darunter tragende Teile: alle drei GitHub-Workflows (`ci.yml` 290 Zeilen, `deploy.yml` 129,
`pr-checks.yml` 122), `README.md` (409 Zeilen), `CHANGELOG.md`, `CONTRIBUTING.md`,
`DEPLOYMENT.md`, `docker-compose.prod.yml`, `deploy.sh`, `CLAUDE.md`.

Ein Teil war echter Ballast — `QUICKSTART.md` **und** `QUICK_START.md` **und**
`EINFACHER_START.md` **und** `MANUAL_START.md`, dazu `FINAL_SUMMARY.md` und `FIXES_APPLIED.md`.
Das Aufräumen war richtig; README und CI sind mit rausgefallen.

**Heutiger Zustand: kein README, kein CI, keine LICENSE.**

#### 🔴 P0 — 39 Commits liegen nur auf dieser Platte

```
git branch -vv   → feat/photo-media [origin/feat/photo-media: 39 voraus]
git rev-list --left-right --count origin/main...HEAD   → 1  45
```

Fünf Wochen Arbeit (Security-Hardening, AI-Fixes, Offline-Cache, Sentry-Maskierung) sind
nirgends gespiegelt.

#### 🔴 P1 — 98 bekannte Schwachstellen in den Abhängigkeiten

```
pip-audit -r backend/requirements.txt   → 96 Pakete geprüft, 14 betroffen, 98 Findings
```

| Paket | Version | Findings |
|---|---|---|
| aiohttp | 3.9.1 | 41 |
| pillow | 10.2.0 | 22 |
| starlette | 0.35.1 | 9 |
| python-multipart | 0.0.6 | 9 |
| python-jose | 3.3.0 | 5 |
| requests, gunicorn, fastapi, protobuf, sentry-sdk, ecdsa, pytest, python-dotenv, pillow-heif | | 12 zusammen |

Dazu `npm audit`: **7 Findings, davon 5 hoch** (u. a. `form-data` CRLF-Injection,
`follow-redirects`). Alle über `npm audit fix` behebbar.

Die Versionen sind sauber gepinnt — das ist richtig. Sie wurden nur seit Januar 2024 nicht angefasst.

#### 🟠 P1 — Ein einziges Backup, zwei Monate alt

```
ls -la /DATA/AppData/travelmind/backups/
→ prod_pre_import_20260624.sql   43.506 Bytes   24. Juni
```

Das ist die einzige Datei. Seit dem 24. Juni nichts. Die **104 MB Uploads** (Fotos!) haben
überhaupt kein Backup — der SQL-Dump enthält sie nicht.

#### 🟠 P1 — Der Prod-Container lief als root

`backend/Dockerfile.prod:71` setzt `USER travelmind`. Die Compose auf `.143` überschreibt das
mit `user: "0:0"`. Die Härtung im Image war damit wirkungslos.

Zweitens baut die Compose per `build:` direkt auf dem Host statt ein getaggtes Image zu ziehen —
damit gibt es **keinen Rückweg**: kein Image-Tag, kein Rollback, kein reproduzierbarer Stand.

#### 🟠 P2 — Das Lint-Gate ist unbrauchbar

```
npx eslint .   → 460 Probleme (440 Fehler)
```

Davon sind **377 in Build-Artefakten**: `html/assets/index-*.js` 320, `dev-dist/` 41,
`vite.config.js`/`vitest.config.js` 16. Im echten Quelltext stehen **63 Fehler in 25 Dateien**
(54 × `no-unused-vars`, 8 × `no-case-declarations`).

Es fehlt schlicht eine `ignores`-Angabe. Ein Gate, das immer rot meldet, wird weggeklickt —
danach schützt es auch dort nicht mehr, wo es recht hätte.

#### 🟠 P2 — Die vier Sprachen sind auseinandergelaufen

```
de: 955 Keys   en: 955 Keys (deckungsgleich)
es: 963 Keys   → 7 fehlen, 15 zusätzlich
fr: 963 Keys   → 7 fehlen, 15 zusätzlich
```

Es fehlen `common:clear`, `common:noResults`, `common:searchPlaceholder`, `diary:caption`,
`diary:captionPlaceholder`, `diary:captionSaved`, `map:showPhotos`. **Vier davon werden im Code
benutzt** — spanische und französische Nutzer bekommen dort englischen Fallback-Text mitten in
der Oberfläche.

#### 🟠 P2 — 40 % des Hauptbundles sind Übersetzungen

Alle vier Sprachen werden in `src/i18n.js` statisch importiert und landen im `index`-Chunk.
Belegt mit einer Positivkontrolle je Sprache — `Speichern`, `Save`, `Guardar`, `Enregistrer`
stehen alle vier im gebauten Chunk:

```
144,1 KiB kompaktes Locale-JSON von 362,9 KiB index-Chunk = 40 %
```

Nachladen pro Sprache spart dem Nutzer rund drei Viertel davon.

#### 🟡 P2 — Die Testabdeckung ist schief verteilt

Backend 53 % gesamt, aber die größten Module sind die dünnsten:
`routes/diary.py` 30 % (368 Statements), `routes/timeline.py` 32 %, `routes/admin.py` 36 %,
`services/ai_service.py` 25 %, `services/guide_parser.py` 20 %.

Frontend: 11 Tests für 58 Komponenten. Getestet sind `ErrorBoundary` und `services/api.js` — sonst nichts.

#### 🟡 P2 — Barrierefreiheit ist ungeprüft

7 `aria-*`-Attribute in 58 Komponenten. Immerhin: 25 `<img>` mit 25 `alt=`. Es gibt keinen
Tastatur-Test, keine Kontrastprüfung, kein `axe` in der Suite.

#### 🟡 P3 — Modell-IDs und Auth-Härtung

`ai_service.py` nutzt `claude-sonnet-4-6` — eine Generation hinter dem aktuellen
`claude-sonnet-5`. Die IDs `gpt-5.4`, `gemini-3.5-flash` und `meta-llama/llama-4-maverick-…`
habe ich **nicht** gegen die Provider-Dokumentation geprüft: unverifiziert.

Passwörter: mindestens 8 Zeichen, keine Komplexitäts- oder Leak-Prüfung, kein 2FA.
**55 von 127** Endpunkten haben kein Rate-Limit.

---

## 2. Plan

Sechs Phasen. Jede Zeile nennt die Prüfung, die sie abschließt — „gemacht" gilt erst mit ihr.

### Phase 0 — Sichern · ~1 Stunde · vor allem anderen

| # | Schritt | Prüfung |
|---|---|---|
| 0.1 | 39 Commits nach `origin/feat/photo-media` pushen | `git rev-list --count origin/feat/photo-media..HEAD` → 0 |
| 0.2 | Postgres-Volume und 104 MB Uploads von `.143` herunterziehen | `sha256sum` beidseitig gleich, Dateizahl gleich |
| 0.3 | Klären, wodurch die Container verschwanden (Docker-Events, ZimaOS-Update) | Ursache benannt, nicht vermutet |

### Phase 1 — Wieder online · ~1 Tag

| # | Schritt | Prüfung |
|---|---|---|
| 1.1 | Compose reparieren: `user: "0:0"` raus, `build:` durch getaggtes Image ersetzen (Tag = Commit-SHA) | `docker inspect` zeigt non-root; Tag ist ein SHA |
| 1.2 | Stack hochfahren | `/api/health` liefert 200 mit Payload, alle Container `healthy` |
| 1.3 | Im Browser in **DE** durchklicken: Login, Trip anlegen, Diary mit Foto, Budget, Karte | Screenshot je Flow, Konsole leer, keine rohen i18n-Keys |

### Phase 2 — Fundament zurückholen · 2–3 Tage

| # | Schritt | Prüfung |
|---|---|---|
| 2.1 | `README.md` neu — Basis aus `origin/main`, aber auf den heutigen Stand korrigiert | Jeder Befehl darin einmal ausgeführt |
| 2.2 | CI zurück: `ci.yml` + `pr-checks.yml` aus `origin/main` holen und an den heutigen Baum anpassen | Ein PR läuft grün durch; ein absichtlich kaputter wird rot |
| 2.3 | `LICENSE` wählen und setzen | Datei liegt, SPDX-Kennung im README |
| 2.4 | `eslint.config.js` um `ignores` für `dist/ html/ dev-dist/` erweitern, dann die 63 echten Fehler beheben | `npx eslint .` → 0 Fehler |
| 2.5 | `CLAUDE.md` wieder anlegen (Projektregeln, Startbefehle, Fallen) | — |

**Der wichtigste Schritt der Phase ist 2.2.** Ohne CI ist jede spätere Aussage über „grün"
wieder von Hand gemessen und damit vom Zufall abhängig.

### Phase 3 — Sicherheit · 2–3 Tage

| # | Schritt | Prüfung |
|---|---|---|
| 3.1 | Python-Updates in zwei Wellen: erst `pillow aiohttp starlette fastapi python-multipart python-jose requests gunicorn`, dann der Rest | `pytest` nach **jeder** Welle grün; `pip-audit` → 0 |
| 3.2 | `npm audit fix`, danach Build und E2E | `npm audit` → 0 hoch/kritisch |
| 3.3 | `pip-audit` und `npm audit` als CI-Gate, das den Build **bricht** | Ein absichtlich verwundbares Pin macht CI rot |
| 3.4 | Container non-root, `read_only: true` wo möglich, `cap_drop: ALL` | `docker inspect` je Dienst |
| 3.5 | Rate-Limits auf die 55 offenen Endpunkte | Skript zählt Endpunkte ohne `@limiter.limit` → 0 |
| 3.6 | Passwort-Policy (Länge + HIBP-Range-Check), 2FA optional | Test: bekanntes geleaktes Passwort wird abgelehnt |

### Phase 4 — Betrieb · ~2 Tage

| # | Schritt | Prüfung |
|---|---|---|
| 4.1 | Tägliches Backup: `pg_dump` **plus Uploads**, Retention 14/8/6 | **Restore-Probe** auf einen leeren Stack — ein Backup ist erst nach erfolgreichem Restore eines |
| 4.2 | Überwachung: `/api/health` und `/metrics` an ein Dashboard, Alarm bei Ausfall | Container absichtlich stoppen → Alarm kommt an |
| 4.3 | Deploy-Skript mit Image-Tag und Rollback-Pfad | Rollback auf die Vorversion einmal durchgeführt |

**4.1 und 4.2 sind die Antwort auf genau den heutigen Befund**: Die Produktion war weg und
104 MB Fotos hatten kein Backup — beides ist niemandem aufgefallen.

### Phase 5 — Qualität · 1–2 Wochen, parallel möglich

| # | Schritt | Prüfung |
|---|---|---|
| 5.1 | Backend-Coverage 53 % → 75 %, zuerst `diary`, `timeline`, `admin`, `ai_service`, `guide_parser` | `pytest --cov` ≥ 75 %, CI bricht darunter |
| 5.2 | Frontend: die acht wichtigsten Flows als Component-Tests, E2E in **DE-Locale** gegen Postgres | Suite grün; ein eingebauter Fehler wird rot |
| 5.3 | i18n-Gate: Skript vergleicht die Key-Sets aller Sprachen, die 7 fehlenden es/fr-Keys ergänzen | Skript → Exit 0; ein entfernter Key macht CI rot |
| 5.4 | Locales nachladen statt statisch importieren | index-Chunk misst < 250 kB |
| 5.5 | `axe-core` in die E2E-Suite, aria-Lücken schließen | 0 kritische axe-Verstöße auf den 8 Hauptseiten |

### Phase 6 — Produktreife · danach

| # | Schritt |
|---|---|
| 6.1 | Modell-IDs gegen die Provider-Dokumentation prüfen und aktualisieren (nie aus dem Gedächtnis) |
| 6.2 | Onboarding, leere Zustände, Fehlermeldungen in der Nutzersprache |
| 6.3 | Semantische Versionierung, `CHANGELOG.md` wieder pflegen, Release-Tags |
| 6.4 | OpenAPI-Doku veröffentlichen (die Tags stehen schon in `main.py`) |

---

## 3. Reihenfolge in einem Satz

**Erst sichern (0), dann wieder laufen lassen (1), dann das Netz einziehen, das den nächsten
Ausfall meldet (2 + 4), dann die Angriffsfläche schließen (3), dann die Qualität (5).**

Die Phasen 0–2 sind der Unterschied zwischen „läuft bei mir" und „ist ein Produkt".
Alles danach ist Ausbau.

---

## 4. Was ich heute NICHT geprüft habe

Ehrlich benannt, damit niemand es für geprüft hält:

- **Keine Browser-Verifikation.** Die App läuft nirgends — alle UI-Aussagen in diesem Dokument
  stammen aus dem Quelltext und dem Build, nicht aus einer laufenden Oberfläche.
- **Die offenen Bugs aus dem Juni** (rohe i18n-Keys, leere AI-Suggestions) konnte ich deshalb
  weder bestätigen noch entkräften.
- **Die Modell-IDs** `gpt-5.4`, `gemini-3.5-flash`, `meta-llama/llama-4-maverick-17b-128e-instruct`
  sind ungeprüft — dafür braucht es die Provider-Dokumentation.
- **Die Ursache des Produktionsausfalls** ist nicht gemessen, nur der Zustand.
