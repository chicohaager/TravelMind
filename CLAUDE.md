# CLAUDE.md — Arbeitsregeln für dieses Projekt

Wiederhergestellt am 2026-08-25. Commit `f82d006` hatte die Datei entfernt.
Das ist **nicht** die alte Fassung: sie beschreibt, was am 2026-08-25 gemessen
gilt, und enthält die Fallen, die beim Wiederaufbau der Produktion aufgefallen
sind.

---

## Vor der ersten Änderung

```bash
# Backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt flake8 black isort pytest-cov

# Frontend
cd frontend && npm ci

# Hooks — sie sind die günstigste Stelle, an der etwas auffällt
pip install pre-commit && pre-commit install
```

## Vor jedem „fertig"

Alles hiervon muss grün sein. In CI läuft dasselbe, und **jede Zeile davon kann
rot werden** — der alte Workflow trug `continue-on-error: true` auf neun
Schritten, deshalb liefen 169 flake8-Verstöße und 98 CVEs unter einem grünen
Haken auf.

```bash
flake8 backend/                                        # muss 0 melden
black --line-length=120 --check backend/
isort --profile=black --line-length=120 --check-only backend/
cd backend && pytest tests -q --cov=. --cov-fail-under=50

cd frontend && npx eslint .                            # muss 0 Fehler melden
cd frontend && npx vitest run
cd frontend && npm run build
```

Bei UI-Änderungen zusätzlich: **im Browser durchklicken, in DE.** Ein HTTP 200
sagt hier nichts — der SPA-Fallback beantwortet jeden unbekannten Pfad mit 200,
und am 2026-08-25 lieferte `curl` auf `/api/auth/login` sauber 200, während im
Browser jeder Login mit 503 scheiterte.

---

## Fallen, die dieses Projekt schon einmal gestellt hat

Jede davon hat Stunden gekostet. Alle haben dieselbe Form: **ein Fallback zeigte
etwas Plausibles, statt laut zu scheitern.**

### Frontend

| Falle | Woran man sie erkennt |
|---|---|
| **`t('namensraum.schlüssel')` mit Punkt** | i18next sucht dann im Standard-Namensraum `common`, findet nichts und zeigt den Fallback. Auf dem Bildschirm stand `+ culture` statt `+ Kultur`. Namensräume brauchen einen **Doppelpunkt**. Der Test `i18n-integrity.test.js` verbietet es. |
| **Fest verdrahtete Locale** | `toLocaleDateString('de-DE')` — spanische Nutzer bekamen deutsche Formate. Immer `aktuelleLocale()` aus `utils/format`. Auch das erzwingt ein Test. |
| **`i18n.language` trägt die Region** | Nach der Spracherkennung steht dort `de-DE`, nicht `de`. Jeder Vergleich muss auf dem Sprachteil arbeiten (`.split('-')[0]`) oder `resolvedLanguage` nehmen. |
| **`lng:` in `i18n.init`** | Setzt man es, wird der LanguageDetector vollständig übergangen — er ist dann konfiguriert und wirkungslos. Nicht setzen. |
| **Keine `.env` im Build-Kontext** | Vite backt `VITE_*` ins Bundle. `frontend/.dockerignore` hält die lokale Datei draußen; CI prüft, dass keine Entwicklungs-Adresse im Bundle steht. |
| **`VITE_API_URL` leer lassen** | Die Oberfläche spricht `/api` relativ an. Eine absolute Adresse im Bundle funktioniert nur unter genau einem Hostnamen. |

### Backend

| Falle | Woran man sie erkennt |
|---|---|
| **Nebenwirkungs-Importe** | `models/database.py` und `tests/conftest.py` importieren Modelle, die nirgends benutzt werden — sie registrieren Tabellen an `Base.metadata`. Ohne sie legt `create_all()` sie nicht an. Sie tragen `# noqa: F401` **und** eine Begründung. Nicht entfernen, auch nicht durch autoflake. |
| **`login` erwartet Formulardaten** | `OAuth2PasswordRequestForm`, nicht JSON. `curl -d 'username=…&password=…'`, kein `-H 'Content-Type: application/json'`. |
| **Datumsfelder brauchen volle Zeitangabe** | `2026-09-01` wird abgewiesen, `2026-09-01T00:00:00` nicht. |
| **`/health` gibt es zweimal** | Einmal ohne Präfix und einmal als `/api/health*`. Beide antworten. |

### Betrieb

| Falle | Woran man sie erkennt |
|---|---|
| **nginx läuft non-root auf 8080** | Port 80 kann ein unprivilegierter Prozess nicht binden. Veröffentlicht wird über das Port-Mapping. Wer das ändert, braucht wieder `user: "0:0"` — und hebt damit die Härtung des Images auf. |
| **uid 1001 ist ein Vertrag** | Backend- und Frontend-Image laufen unter 1001. Die Bind-Mounts `uploads/` und `backups/` müssen ihr gehören, sonst startet gunicorn nicht (`PermissionError: 'uploads/trips'`). |
| **`localhost` in Healthchecks** | Kann in schlanken Images auf `::1` auflösen, während der Dienst nur IPv4 bindet — der Container meldet dann fälschlich `unhealthy`. Immer `127.0.0.1`. |
| **`docker compose` auf .143** | Das Plugin wird nicht gefunden. Direkt aufrufen: `/usr/lib/docker/cli-plugins/docker-compose`. |
| **Kein `build:` in der Produktion** | Gebaut wird außerhalb, ausgeliefert werden Images mit dem Commit-SHA als Tag. Nur so gibt es einen Rückweg. |

---

## Wie in diesem Projekt geprüft wird

Diese drei Regeln haben am 2026-08-25 mehr gefunden als jedes Nachdenken:

1. **Von der Seite messen, über die die Aussage gilt.** `docker exec … id`
   zeigt den Exec-Benutzer, nicht den laufenden Prozess — dafür `docker top`.
   `curl` schickt keinen `Origin`-Header, ein Browser immer.

2. **Ein negativer Befund braucht eine Positivkontrolle.** „Kein Treffer" ist
   wertlos, solange nicht feststeht, dass die Suche überhaupt anschlagen kann.
   Der i18n-Scanner hat vier Fundstellen mehr gefunden als `grep`, weil er eine
   hatte.

3. **Ein Wächter, der nie rot war, ist eine Zusicherung ohne Prüfung.** Jeder
   Test in `i18n-integrity.test.js` und `format.test.js` wurde durch Sabotage
   rot gesehen, bevor er eingecheckt wurde. Neue Wächter genauso.

Und die Umkehrung davon: **eine Ausnahme muss enger sein als die Regel.**
`# noqa`, `# nosec`, `eslint-disable` stehen hier je Zeile mit Begründung — nie
je Datei und nie global. Wo doch etwas projektweit ausgenommen ist (`pyproject.toml`,
`setup.cfg`, `.markdownlint.json`), steht der Grund daneben.

---

## Wo was liegt

```text
backend/
  main.py            App, Middleware, Fehlerbehandlung, Start-Prüfungen
  routes/            21 Module, 127 Endpunkte
  models/            SQLAlchemy-Modelle; database.py enthält init_db
  services/          KI-Anbindung, Geocoding, Audit, Benachrichtigungen
  middleware/        Security-Header, Request-IDs, Metriken
  alembic/versions/  Migrationen (erzeugt — von den Lint-Regeln ausgenommen)

frontend/src/
  pages/             18 Seiten
  components/        Wiederverwendbares
  locales/<lang>/    4 Sprachen × 28 Namensräume, je 955 Schlüssel
  utils/format.js    EINZIGE Stelle, an der eine konkrete Locale stehen darf
  test/              Wächter gegen ganze Fehlerklassen
```

Weiteres: [`README.md`](README.md) · [`docs/ROADMAP.md`](docs/ROADMAP.md) ·
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
