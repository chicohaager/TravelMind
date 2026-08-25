# TravelMind — Stand und Weg zur professionellen App

**Erhoben am:** 2026-08-25 · **Branch:** `feat/photo-media` @ `d62d47b`
**Alle Zahlen in diesem Dokument sind an diesem Tag gemessen.** Das Kommando steht jeweils dabei.

---

## 1. Stand

### 1.1 Was steht

| Bereich | Messwert | Kommando |
| --- | --- | --- |
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

```text
docker ps -a --format '{{.Names}}' | wc -l   → 36 Container
docker ps -a | grep -i travel                → (leer)
docker ps -a --filter status=exited          → nur zimaos-mcp-deployer
Port 8190                                    → nimmt keine Verbindung an
ping <host>                           → 0 % Verlust, 0,35 ms (Host lebt)
Ports 22 und 80                              → offen
```

Es ist mehr als „Container gestoppt". Die App ist vollständig deinstalliert:

```text
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

```text
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

```text
git branch -vv   → feat/photo-media [origin/feat/photo-media: 39 voraus]
git rev-list --left-right --count origin/main...HEAD   → 1  45
```

Fünf Wochen Arbeit (Security-Hardening, AI-Fixes, Offline-Cache, Sentry-Maskierung) sind
nirgends gespiegelt.

#### 🔴 P1 — 98 bekannte Schwachstellen in den Abhängigkeiten

```text
pip-audit -r backend/requirements.txt   → 96 Pakete geprüft, 14 betroffen, 98 Findings
```

| Paket | Version | Findings |
| --- | --- | --- |
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

```text
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

```text
npx eslint .   → 460 Probleme (440 Fehler)
```

Davon sind **377 in Build-Artefakten**: `html/assets/index-*.js` 320, `dev-dist/` 41,
`vite.config.js`/`vitest.config.js` 16. Im echten Quelltext stehen **63 Fehler in 25 Dateien**
(54 × `no-unused-vars`, 8 × `no-case-declarations`).

Es fehlt schlicht eine `ignores`-Angabe. Ein Gate, das immer rot meldet, wird weggeklickt —
danach schützt es auch dort nicht mehr, wo es recht hätte.

#### 🟠 P2 — Die vier Sprachen sind auseinandergelaufen

```text
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

```text
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

## 1.3 Fortschritt (laufend aktualisiert)

**Stand 2026-08-25, 14:30.** Phase 0 und Phase 1 sind abgeschlossen und belegt.

| Phase | Schritt | Zustand | Beleg |
| --- | --- | --- | --- |
| 0.1 | 39 Commits pushen | ✅ | `git rev-list --count origin/feat/photo-media..HEAD` → 0 |
| 0.2 | Daten sichern | ✅ | 1429 Dateien, **1429/1429 sha256 OK, 0 FAILED**, Archiv unter `~/backups/travelmind-20260825/` (116 MB) |
| 0.3 | Ursache klären | ⚠️ teilweise | Abschaltung auf **2026-06-26 16:35** datiert (`pg_stat/pgstat.stat` geschrieben, sauberer Shutdown, kein `postmaster.pid`). Die Ursache ist **nicht mehr messbar**: alle Lebenszyklus-Logs beginnen später — `mod-management.log` ab 16.07., darin 103 Einträge für eine andere App als Positivkontrolle und 0 für travelmind. ZimaOS ging von v1.6.1 auf v1.7.1-beta1; der Zeitpunkt ist aus den erhaltenen Logs nicht datierbar. |
| 1.1 | Compose reparieren | ✅ | Alle drei Container non-root, am **Host-Prozess** gemessen: db uid 70, backend 1001, frontend 1001. `cap_drop: ALL`, `no-new-privileges`, Frontend zusätzlich `read_only`. Getaggte Images statt `build:` — mehrere Versionen liegen auf dem Host, Rollback ist eine Zeile in `deploy-params.conf`. |
| 1.2 | Stack hochfahren | ✅ | `/api/health` liefert 200 **mit Payload** (`database: healthy`), alle Container `healthy`. Echte Daten unversehrt: 2 Nutzer, 4 Reisen (Hamburg, La Palma, Toskana + Testreise), 16 Orte, 2 Tagebucheinträge, 7 Medien. Fotos laden wieder (1,4 MB PNG, 351 KB JPEG), Gegenkontrolle liefert 404. |
| 1.3 | Browser-Durchgang in DE | ✅ | 7 Seiten auf Deutsch, 0 rohe i18n-Keys (Scanner mit bestandener Positivkontrolle), Reise über die Oberfläche angelegt, alle vier Sprachen geprüft, keine Konsolenfehler. |

| 2.1 | README neu | ✅ | Jeder Befehl darin ausgeführt. Zwei Behauptungen dabei widerlegt und korrigiert: `/docs` ist hinter dem Produktions-nginx **nicht** erreichbar (der SPA-Fallback liefert 200 für jeden Pfad), und `ENABLE_DEMO_MODE` steuert Demo-Reisen, nicht ein Standardkonto. |
| 2.2 | CI zurück | ✅ | Neu geschrieben statt zurückgeholt: die alte Fassung trug `continue-on-error: true` auf **neun** Schritten — Lint, Frontend-Tests, Trivy, Safety und E2E konnten gar nicht rot werden. Der neue Workflow hat davon 0 in 142 Inhaltszeilen. Alle Befehle vorher lokal gefahren. |
| 2.3 | LICENSE | ✅ | MIT — war in `backend/package.json` und im alten README bereits deklariert, die Datei fehlte nur. |
| 2.4 | Lint-Gate | ✅ | eslint **440 → 0** Fehler; flake8 **169 → 0**; bandit 0. `ErrorBoundary.jsx` konnte eslint gar nicht parsen und wurde stillschweigend übersprungen (ecmaVersion 2020 kennt keine Klassenfelder). Sabotage-Gegenprobe auf beiden Seiten rot. |
| 2.5 | CLAUDE.md | ✅ | Neu geschrieben mit den Fallen, die der Wiederaufbau aufgedeckt hat. |
| 2.6 | pre-commit | ✅ | Die Konfiguration lag seit jeher da und **konnte nie laufen**: Hook nicht installiert, zwei referenzierte Dateien fehlten, black auf ein nicht vorhandenes Python gepinnt. Alle 17 Hooks grün, Sabotage-Gegenprobe rot. |

### Phase 3 — Sicherheit (abgeschlossen)

| Schritt | Zustand | Beleg |
|---|---|---|
| 3.1 Python-Updates | ✅ | **98 → 0** Findings. Gemessen an den **104 Paketen im gebauten Image**, nicht nur an der Anforderungsdatei: `No known vulnerabilities found`. Zwei Wellen; Pillow sprang über zwei Hauptversionen und wurde an zwölf echten Fotos geprüft (Validierung, EXIF mit Zeit und GPS, Verkleinerung, HEIC). |
| 3.2 npm | ✅ | **7 → 0**. `npm audit`: `found 0 vulnerabilities`. Dafür vite 5→8, vitest 1→4 und react-router-dom 6→7. |
| 3.3 Audits als CI-Tor | ✅ | Neuer Job „Bekannte Schwachstellen", beide Prüfungen hart. Erst **nachdem** sie grün sind — ein Tor, das bei 98 Findings eingebaut wird, ist nach dem dritten roten Lauf abgeschaltet. |
| 3.4 Container-Härtung | ✅ | Beide Anwendungscontainer jetzt `read_only`, `cap_drop: ALL`, `no-new-privileges`, non-root. Am laufenden Container gemessen. |
| 3.5 Rate-Limits | ✅ | **0 von 123** Endpunkten ohne Grenze (vorher 51). Dabei ein echter Fund, siehe unten. |
| 3.6 Passwortregeln | ✅ | Länge plus Abgleich mit bekannten Leaks an **allen drei** Stellen, an denen ein Passwort gesetzt wird. In der Produktion belegt: `testpass123` wird mit der exakten Trefferzahl abgewiesen. |

#### python-jose → PyJWT: kein Geschmacksurteil

`python-jose` hält `pyasn1` unter 0.5 fest — sechs Findings — und zieht `ecdsa`
mit, für das es **überhaupt keine** behebende Version gibt. Beide ließen sich
nur durch den Wechsel schließen. Die benutzte Schnittstelle war identisch:
sieben Aufrufe in zwei Dateien.

Belegt statt angenommen: ein **echtes Token aus der laufenden Produktion**,
signiert von python-jose, wird von PyJWT gelesen — bestehende Anmeldungen
laufen weiter. Im Browser nachgeprüft: nach dem Ausrollen war die alte Sitzung
noch gültig.

#### Der Fund bei den Rate-Limits: die Grenzen zählten pro Worker

Nach dem Anbringen wollte ich sie belegen. 140 Anfragen an einen Endpunkt mit
Grenze 120/Minute gingen alle durch. Drei Messungen bis zur Ursache:

1. **Über nginx:** 115 von 140 kamen als HTTP **503** — nginx' eigene Grenze
   (10 r/s) greift *vor* der Anwendung. Ich hatte von der falschen Seite gemessen.
2. **Direkt gegen den Container:** 140 × 200, kein einziger 429.
3. **Im laufenden Prozess:** Konfiguration korrekt — aber **4 gunicorn-Worker
   und `MemoryStorage`**. Jeder Worker zählt für sich.

Die effektive Grenze war damit bis zu **viermal so hoch** wie die konfigurierte.
`AUTH_LOGIN = 10/minute` erlaubte real bis zu 40 Versuche.

Behoben ohne neue Infrastruktur zu erzwingen: `RATE_LIMIT_STORAGE_URI` macht
einen gemeinsamen Speicher möglich; das Verhalten ohne ihn steht jetzt samt
Messwert im Code. nginx bekam eine **eigene, strengere Zone für `/api/auth/`**
(1 r/s statt 10) und antwortet auf Überschreitung mit **429 statt 503** — der
Unterschied ist nicht kosmetisch, 503 liest sich in jeder Überwachung als
„Dienst ausgefallen".

Belegt nach dem Ausrollen: `/api/` 24×200 / 16×429, `/api/auth/` nur 6 von 15
durchgelassen, einzelne Anfrage weiterhin 200.

#### Passwortregeln nach NIST SP 800-63B

Ausdrücklich **keine** Komplexitätsregeln — die erzeugen „Passwort1!". Wirksam
sind Länge und der Abgleich mit bekannten Leaks über k-Anonymität: es verlassen
fünf Zeichen des SHA-1-Hashes den Server, nie das Passwort. Ein eigener Test
prüft genau das.

Die interessante Frage war, was bei nicht erreichbarem Dienst passiert. Drei
Betriebsarten (`best-effort` / `required` / `off`), und `leak_treffer` ist dabei
`None`, nicht `0` — „nicht feststellbar" ist nicht „nachweislich nicht
betroffen". Genau diese Verwechslung macht ein Fallback unsichtbar.

Gegen den echten Dienst gemessen: die bisherigen Testpasswörter `securepass123`
und `testpass123` stehen **547** bzw. **8.513** Mal in bekannten Leaks. Die
Regel funktioniert — und deshalb brachen drei alte Tests.

**Backend-Tests: 53 → 71.**

### Phase 4 — Betrieb (abgeschlossen)

| Schritt | Zustand | Beleg |
|---|---|---|
| 4.1 Tägliche Sicherung mit Restore-Probe | ✅ | Erste vollständige Sicherung inklusive der **104 MB Fotos**, danach in eine Wegwerf-Datenbank zurückgespielt: alle Zeilen stimmen, alle 45 Fotos entpackt. **PROBE BESTANDEN.** |
| 4.2 Überwachung mit Alarm | ✅ | Backend absichtlich gestoppt → nach drei Fehlversuchen Alarm, Pushover-Meldung verschickt. Backend gestartet → Entwarnung verschickt. **Beide Richtungen belegt.** |
| 4.3 Deploy-Skript mit Rückweg | ✅ | Vollständiges Ausrollen, dann `--zurueck` auf den vorigen Stand, dann wieder vor. Jedes Mal von außen geprüft. |

#### Das vorhandene Backup-Skript konnte nie funktionieren

`backend/scripts/backup_database.py` liegt seit jeher im Repository und war in
`docs/BACKUP.md` dokumentiert. Es ruft `pg_dump` im Backend-Container auf —
**dort gibt es keins**:

```text
docker exec travelmind-backend python /app/scripts/backup_database.py …
ERROR - pg_dump not found. Please install PostgreSQL client tools.
```

Nachinstallieren wäre die naheliegende und die falsche Antwort: Debian
bookworm liefert `pg_dump` 15, der Server läuft auf 16, und `pg_dump`
verweigert den Dienst gegen eine neuere Serverversion.

Die neue Lösung läuft in einem `postgres:16-alpine`-Container im Compose-Netz
und benutzt damit den `pg_dump` **desselben Image-Stands** wie der Server — die
Versionen können per Konstruktion nicht auseinanderlaufen. Ohne Docker-Socket
(die erste Fassung brauchte ihn, und das ist faktisch Root auf dem Host) und
ohne systemd.

#### Die Probe hat sofort zwei echte Fehler gefunden

Beide in busybox' `sha256sum`, beide hätten eine Sicherung stillschweigend als
„geprüft" durchgehen lassen:

1. `--quiet` kennt es nicht — die Prüfung brach mit einer Nutzungsmeldung ab.
2. Es überspringt **Kommentarzeilen nicht**, sondern hält sie für Dateinamen:
   zwei erfundene `FAILED` neben zwei echten `OK`, Exit 1.

Genau dafür ist eine Probe da. Beide behoben, das Manifest ist jetzt rein
maschinenlesbar.

#### Ein Wächter, der den Inhalt prüft

Sichern allein hätte den Fall vom Juni nicht verhindert. `travelmind-waechter`
fragt Oberfläche **und** API im Minutentakt, durch dieselbe Kette wie ein
Nutzer — und prüft den **Inhalt**, nicht den Statuscode. Das ist wesentlich:
Der SPA-Rückfall beantwortet jeden Pfad mit 200, und die API kann 200 liefern,
während die Datenbank weg ist. Alarm über Pushover mit Priorität 1, also an
Ruhezeiten vorbei — ein Ausfall, der bis zum Morgen wartet, ist genau der Fall
vom 26. Juni.

#### Nebenbei repariert

Beim Absichern von `.env` (0600 root) hatte ich mir selbst den Deploy-Weg
verbaut — des Betreibers Konto konnte die Compose nicht mehr starten. Jetzt `640
root:samba`: strenger als vorher (644), und der Betrieb läuft.

### Was der Wiederaufbau ans Licht gebracht hat

Sieben Fehler, alle mit derselben Form: **ein Fallback zeigte etwas Plausibles
an, statt laut zu scheitern.** Keiner war auf API-Ebene oder in den Tests
sichtbar; jeder wurde erst durch einen Klick im echten Browser gefunden.

1. **Das Frontend baute mit der Konfigurationsdatei des Entwicklerrechners.**
   Es gab kein `.dockerignore`; `COPY . .` nahm sie mit, Vite backte
   `http://localhost:8003` ins Bundle. Im Browser scheiterte **jeder** Login
   mit 503 — derselbe Login per `curl` gegen `/api` lieferte 200. Behoben durch
   `.dockerignore` plus relativen API-Pfad als Standard.
2. **nginx konnte nicht non-root laufen** (Port 80 ist einem unprivilegierten
   Prozess verwehrt). Deshalb hatte die alte Compose `user: "0:0"` gesetzt und
   damit die Härtung des Images aufgehoben. Behoben an der Ursache: Port 8080.
3. **Die uid des Backends war Zufall.** `useradd -r` ohne `-u` vergab 999; die
   Bind-Mounts müssen ihr aber gehören. Auf 1001 festgenagelt.
4. **`lng: 'en'` machte den LanguageDetector zu totem Code.** Jeder Nutzer sah
   Englisch, auch mit deutschem Browser.
5. **Namensräume mit Punkt statt Doppelpunkt** an sieben Stellen — im
   Reise-Dialog stand `+ culture`, `+ cityTrip` mitten in der deutschen
   Oberfläche, während die Übersetzung danebenlag und nur unerreichbar war.
   Vier der sieben fand der neue Wächter, nicht mein grep.
6. **Die Formatierung kannte nur `de` gegen alles andere.** `i18n.language`
   trägt die Region ('de-DE'), der Vergleich schlug fehl: **€1,200.00** statt
   **1.200,00 €**. Spanisch und Französisch bekamen ohnehin US-Formate.
7. **`<html lang>` stand fest auf `de`** — auch bei spanischer Oberfläche.
   Vorlesesoftware hätte spanischen Text deutsch ausgesprochen.

**Wächter statt Vorsatz:** `i18n-integrity.test.js` (Namensraum-Schreibweise,
deckungsgleiche Schlüsselmengen, `<html lang>`) und `format.test.js` (alle vier
Sprachen **und** die Form mit Region — genau der Fall, an dem es zerbrochen
ist). Beide Hälften des i18n-Wächters wurden durch Sabotage rot gesehen, bevor
sie eingecheckt wurden.

**Frontend-Tests: 11 → 43.** Sprachdateien: alle vier auf exakt 955 Schlüssel.

---

## 2. Plan

Sechs Phasen. Jede Zeile nennt die Prüfung, die sie abschließt — „gemacht" gilt erst mit ihr.

### Phase 0 — Sichern · ~1 Stunde · vor allem anderen

| # | Schritt | Prüfung |
| --- | --- | --- |
| 0.1 | 39 Commits nach `origin/feat/photo-media` pushen | `git rev-list --count origin/feat/photo-media..HEAD` → 0 |
| 0.2 | Postgres-Volume und 104 MB Uploads von `.143` herunterziehen | `sha256sum` beidseitig gleich, Dateizahl gleich |
| 0.3 | Klären, wodurch die Container verschwanden (Docker-Events, ZimaOS-Update) | Ursache benannt, nicht vermutet |

### Phase 1 — Wieder online · ~1 Tag

| # | Schritt | Prüfung |
| --- | --- | --- |
| 1.1 | Compose reparieren: `user: "0:0"` raus, `build:` durch getaggtes Image ersetzen (Tag = Commit-SHA) | `docker inspect` zeigt non-root; Tag ist ein SHA |
| 1.2 | Stack hochfahren | `/api/health` liefert 200 mit Payload, alle Container `healthy` |
| 1.3 | Im Browser in **DE** durchklicken: Login, Trip anlegen, Diary mit Foto, Budget, Karte | Screenshot je Flow, Konsole leer, keine rohen i18n-Keys |

### Phase 2 — Fundament zurückholen · 2–3 Tage

| # | Schritt | Prüfung |
| --- | --- | --- |
| 2.1 | `README.md` neu — Basis aus `origin/main`, aber auf den heutigen Stand korrigiert | Jeder Befehl darin einmal ausgeführt |
| 2.2 | CI zurück: `ci.yml` + `pr-checks.yml` aus `origin/main` holen und an den heutigen Baum anpassen | Ein PR läuft grün durch; ein absichtlich kaputter wird rot |
| 2.3 | `LICENSE` wählen und setzen | Datei liegt, SPDX-Kennung im README |
| 2.4 | `eslint.config.js` um `ignores` für `dist/ html/ dev-dist/` erweitern, dann die 63 echten Fehler beheben | `npx eslint .` → 0 Fehler |
| 2.5 | `CLAUDE.md` wieder anlegen (Projektregeln, Startbefehle, Fallen) | — |

**Der wichtigste Schritt der Phase ist 2.2.** Ohne CI ist jede spätere Aussage über „grün"
wieder von Hand gemessen und damit vom Zufall abhängig.

### Phase 3 — Sicherheit · 2–3 Tage

| # | Schritt | Prüfung |
| --- | --- | --- |
| 3.1 | Python-Updates in zwei Wellen: erst `pillow aiohttp starlette fastapi python-multipart python-jose requests gunicorn`, dann der Rest | `pytest` nach **jeder** Welle grün; `pip-audit` → 0 |
| 3.2 | `npm audit fix`, danach Build und E2E | `npm audit` → 0 hoch/kritisch |
| 3.3 | `pip-audit` und `npm audit` als CI-Gate, das den Build **bricht** | Ein absichtlich verwundbares Pin macht CI rot |
| 3.4 | Container non-root, `read_only: true` wo möglich, `cap_drop: ALL` | `docker inspect` je Dienst |
| 3.5 | Rate-Limits auf die 55 offenen Endpunkte | Skript zählt Endpunkte ohne `@limiter.limit` → 0 |
| 3.6 | Passwort-Policy (Länge + HIBP-Range-Check), 2FA optional | Test: bekanntes geleaktes Passwort wird abgelehnt |

### Phase 4 — Betrieb · ~2 Tage

| # | Schritt | Prüfung |
| --- | --- | --- |
| 4.1 | Tägliches Backup: `pg_dump` **plus Uploads**, Retention 14/8/6 | **Restore-Probe** auf einen leeren Stack — ein Backup ist erst nach erfolgreichem Restore eines |
| 4.2 | Überwachung: `/api/health` und `/metrics` an ein Dashboard, Alarm bei Ausfall | Container absichtlich stoppen → Alarm kommt an |
| 4.3 | Deploy-Skript mit Image-Tag und Rollback-Pfad | Rollback auf die Vorversion einmal durchgeführt |

**4.1 und 4.2 sind die Antwort auf genau den heutigen Befund**: Die Produktion war weg und
104 MB Fotos hatten kein Backup — beides ist niemandem aufgefallen.

### Phase 5 — Qualität · 1–2 Wochen, parallel möglich

| # | Schritt | Prüfung |
| --- | --- | --- |
| 5.1 | ✅ Backend-Coverage 53 % → **75,18 %**, 71 → 483 Tests; CI-Schranke von 50 auf 75 angehoben | `pytest --cov` ≥ 75 %, Gegenkontrolle mit 76 gefahren |
| 5.2 | Frontend: die acht wichtigsten Flows als Component-Tests, E2E in **DE-Locale** gegen Postgres | Suite grün; ein eingebauter Fehler wird rot |
| 5.3 | ✅ i18n-Gate: Skript vergleicht die Key-Sets aller Sprachen, die 7 fehlenden es/fr-Keys ergänzen | Skript → Exit 0; ein entfernter Key macht CI rot |
| 5.4 | ✅ Locales nachladen statt statisch importieren | index-Chunk 227,0 → 103,1 kB; im Browser 2 Anfragen statt 57 |
| 5.5 | `axe-core` in die E2E-Suite, aria-Lücken schließen | 0 kritische axe-Verstöße auf den 8 Hauptseiten |

#### 5.4 — was gemessen wurde

Vorher lagen **112 Übersetzungsdateien** (4 Sprachen × 28 Namensräume) als
statische Importe im Hauptbündel: 143,9 KiB von 227,0 KiB, also **63 %** von
dem, was jeder Besucher lädt, bevor er überhaupt weiß, welche Sprache er
spricht. Drei Viertel davon konnte er nie brauchen.

| | vorher | nachher |
| --- | --- | --- |
| index-Chunk | 227,0 kB | 103,1 kB |
| JS-Anfragen beim Erstaufruf | 69 | 15 |
| Übersetzungen übertragen | im Bündel | 39,3 kB in 2 Dateien |

Der Zwischenschritt ist der lehrreiche Teil: `import()` allein erzeugte **eine
Datei je Namensraum**, und ein deutscher Erstbesuch holte davon **57** — 28 für
`de` und 28 für `en`, weil i18next die Rückfallsprache mitlädt. Das stand in
keinem Build-Log; gefunden hat es erst die Messung im Browser
(`performance.getEntriesByType('resource')`). `manualChunks` fasst jetzt je
Sprache zusammen.

`main.jsx` wartet auf das Init-Promise, bevor gerendert wird. Ohne das Warten
liefert `t('trips:title')` so lange den **Schlüssel** zurück — auf dem
Bildschirm stünde kurz `trips:title`. Schlägt das Laden fehl, wird trotzdem
gerendert (englischer Rückfall statt weißer Seite) und der Fehler landet laut
im Protokoll.

Im Browser geprüft: alle vier Sprachen umgeschaltet, `<html lang>` folgt, kein
roher Schlüssel sichtbar, je Sprache genau eine nachgeladene Datei.

#### Nebenbefund: 25 Beschriftungen liefen nie durch `t()`

Aufgefallen an *einem* Eintrag der Seitenleiste (`name: 'Transcription'`), der
in **allen vier Sprachen** englisch war, während `transcribe:title` in allen
vier danebenlag. Der Scan über alle `.jsx` fand 25 weitere Stellen derselben
Form — darunter drei fest **deutsche** (`label: 'Glücklich'`), die ein
englischer Nutzer zu sehen bekommen hätte.

Behoben und mit einem vierten Wächter in `i18n-integrity.test.js` abgesichert,
der die **Form** sucht statt einzelner Wörter. Durch Sabotage am echten
Repository rot gesehen. Ausnahmen sind enger als die Regel: Markennamen als
Werte, Testfixtures, und `pages/Home.jsx` — Letzteres hängt an einer eigenen
Zusicherung, dass `/` weiterhin auf `/trips` umleitet.

#### Nebenbefund: die PWA ist im Betrieb nicht aktiv

Der Build erzeugt einen Service Worker und precacht 157 Dateien (1367 KiB).
Im Browser gemessen: `window.isSecureContext === false` und
`'serviceWorker' in navigator === false`. Über einfaches HTTP auf einer
LAN-Adresse ist der Kontext nicht sicher, also läuft **kein** Service Worker —
Offline-Betrieb und Installierbarkeit gibt es derzeit nicht. Das ist keine
Fehlfunktion des Codes, sondern eine Folge des Transports; es braucht TLS.
Gehört nach Phase 6.

### Phase 6 — Produktreife · danach

| # | Schritt |
| --- | --- |
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

---

## Was die Testarbeit an ECHTEN Fehlern gefunden hat

Nicht der Nebeneffekt — der eigentliche Ertrag. Jeder Punkt ist durch
Sabotage in beide Richtungen belegt.

| Fund | Wirkung | Wie er sich versteckt hat |
|---|---|---|
| **Ortsliste löschen löschte alle Orte darin** | Datenverlust bei einem Klick | Der Bestätigungsdialog versprach wörtlich „Orte werden nicht gelöscht". Die Datenbankregel sagte `SET NULL`, die ORM-Kaskade kam ihr zuvor. |
| **Die drei DSGVO-Endpunkte haben nie funktioniert** | Datenmitnahme (Art. 20) und Löschantrag (Art. 17) antworteten immer 422 | `request` ohne Typangabe wurde zum Pflicht-Query-Parameter. Code lädt, App startet, `/docs` zeigt sie an. |
| **Der API-Schlüssel stand in KI-Fehlermeldungen** | Der Wert, den die App verschlüsselt ablegt, stand im Klartext in der HTTP-Antwort | `detail=f"…{str(e)}"` an zehn Stellen — Anbieter schreiben den Schlüssel in ihre Meldung. |
| **Alle vier Modell-IDs veraltet, die von Groq gelöscht** | Jede KI-Anfrage ohne eigene Konfiguration schlug fehl | Groq ist der kostenlose Standardanbieter; die ID stand nicht mehr in der Herstellerliste. |
| **Kein Foto über 1 MB hochladbar** | Handyfotos (2–5 MB) wurden mit 413 abgewiesen | `client_max_body_size` fehlte in nginx, Standard 1 MB — das Backend erlaubt 10 MB. |
| **Kontowechsel zeigte die Daten des vorigen Kontos** | Auf geteilten Rechnern ein Leseloch ohne Token | React-Query-Schlüssel ohne Konto, `staleTime` 5 min, kein `clear()` beim An- oder Abmelden. |
| **18 rohe i18n-Schlüssel im Bildschirm** | `diary.moodHappy` statt „Glücklich" | Der Schlüssel lag in einer Eigenschaft; der Wächter prüfte nur `t('…')`-Aufrufe. |
| **Die tägliche Sicherung war stillgelegt** | Der Lauf um 03:00 wäre abgebrochen | Mein eigenes Deploy-Skript löschte das bind-gemountete Skriptverzeichnis; laufende Container sahen ein leeres `/skripte`. |
| **`/api/health` stürzte auf 500 ab**, wenn eine Teilprüfung warf | Der Ausfall nahm die Auskunft mit, die sagen soll, was ausgefallen ist | `asyncio.gather` ohne `return_exceptions`. |

Korrigiert wurde außerdem eine **falsche Behauptung in `CLAUDE.md`**: ein Datum
ohne Uhrzeit werde abgewiesen. An allen fünf Modellen mit Datumsfeld gemessen
— es wird angenommen, Pydantic ergänzt Mitternacht.

---

## Kern-Flows vor der Kroatien-Reise — durchgeklickt, nicht behauptet

Am 2026-08-25 gegen die laufende Produktion, angemeldet als echter Nutzer.
Alle Prüfdaten anschließend wieder entfernt und die Entfernung gegengeprüft.

| Flow | Beleg |
|---|---|
| **Foto hochladen** | echtes JPEG, 4,18 MB (Signatur `ff d8 ff e0`) → HTTP 200 in 2,1 s, nach WebP gewandelt; Datei mit gültiger RIFF/WEBP-Signatur auf der Platte. **Vorher unmöglich** — nginx wies alles über 1 MB mit 413 ab |
| **Route bauen** | Name + zwei Orte per ➕ → gespeichert, „Routen (1)", **eine Polylinie auf der Karte** in der gewählten Farbe |
| **Tagebucheintrag** | angelegt (201) mit Stimmung und Bewertung, in der Liste, **auf dem Bildschirm sichtbar** samt Ort |
| **Ausgabe erfassen** | 47,80 € angelegt (201), schlägt in der Zusammenfassung durch (`by_category.food = 47.8`), im Bildschirm sichtbar |
| **Tagesplan füllen** | zwei Orte aufgenommen (201), als Tag gelesen, Optimierung meldet „2 Einträge optimiert" |
| **Sprachwechsel** | alle vier Sprachen, `<html lang>` folgt, kein roher Schlüssel |
| **Offline** | Server unerreichbar (`fetch` wirft) → **die App rendert vollständig auf Deutsch** aus dem Precache |
| **Handy (411 px)** | nichts abgeschnitten, Benutzermenü erreichbar (Profil · Einstellungen · **Abmelden**) |

### Was diese Runde an Fehlern gefunden hat

* **Kein Foto über 1 MB hochladbar** — `client_max_body_size` fehlte
* **Sprachwahl, Dunkelmodus und Abmelden lagen bei 411 px außerhalb des Bildschirms**
* **„Route speichern" wirkte tot** — Orte kamen nur per Ziehen hinein
* **18 rohe i18n-Schlüssel**, die der Wächter nicht sah
* **Alle vier KI-Modell-IDs veraltet**, die von Groq gelöscht
* **Die tägliche Sicherung war stillgelegt** — durch das Deploy-Skript selbst

### Noch offen

* **KI mit echtem Schlüssel** — die IDs sind gegen die Herstellerdoku geprüft, nicht gegen den Dienst
* **Pangolin durch den Tunnel** — die Auflösung der Client-IP ist konfiguriert, aber erst LAN-seitig gemessen
