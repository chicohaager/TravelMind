# TravelMind

Selbst gehostete Webanwendung zum Planen, Organisieren und Dokumentieren von
Reisen — mit Reisetagebuch, Fotogalerie, Karte, Budget und KI-Unterstützung
über vier Anbieter (Groq, Anthropic, OpenAI, Google).

Oberflächensprachen: Deutsch, English, Español, Français.

---

## Was drin ist

| | |
| --- | --- |
| **Backend** | FastAPI, PostgreSQL 16, SQLAlchemy 2 (async), Alembic — 127 Endpunkte in 21 Modulen |
| **Frontend** | React 18, Vite 5, TailwindCSS, React Query, Leaflet, PWA |
| **Betrieb** | Strukturiertes JSON-Logging (structlog), Sentry, Request-IDs, Metriken, Security-Header, Rate-Limiting auf 72 Endpunkten |
| **Sprachen** | de · en · es · fr, je 955 Schlüssel, deckungsgleich (durch einen Test erzwungen) |

Funktionen: Reisen mit Zielen, Terminen und Budget · Orte sammeln, kategorisieren
und auf einer Karte anzeigen · Routen bauen · Reisetagebuch mit Markdown und
Fotos · Fotogalerie und Zeitleiste · Ausgaben erfassen und aufteilen ·
Mitreisende einladen · Sprachaufnahmen transkribieren · Tagebuch öffentlich
teilen · Offline-Betrieb als PWA.

---

## Schnellstart (Entwicklung)

Voraussetzungen: Docker mit Compose v2, oder Node ≥ 18 und Python 3.11.

```bash
git clone https://github.com/chicohaager/TravelMind.git
cd TravelMind
cp .env.example .env
```

`.env` bearbeiten — **zwei Werte müssen gesetzt sein**, sonst bricht das Backend
beim Start ab (mit genau dieser Meldung):

```bash
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

Datenbank-Volume anlegen — die Entwicklungs-Compose bindet es **extern** ein,
damit ein `docker compose down -v` bestehende Reisedaten nicht mitnimmt:

```bash
docker volume create travelmind_postgres_data
```

Starten:

```bash
docker compose up -d
```

Oberfläche: <http://localhost:5173> · API-Doku: <http://localhost:8003/docs>
(gemessen: liefert die FastAPI-Oberfläche; in der Produktion **nicht**
erreichbar, weil nginx nur `/api/` und `/uploads/` weiterreicht).

Erstes Konto anlegen — es gibt kein Standardkonto, die Anwendung legt beim
Start keinen Benutzer an:

```bash
docker compose exec backend python create_admin.py
```

### Ohne Docker

```bash
# Backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --reload --port 8003

# Frontend (zweites Terminal)
cd frontend && npm ci && npm run dev
```

Die Oberfläche spricht die API in der Entwicklung über den Vite-Proxy an —
`VITE_API_URL` bleibt dabei **leer**. Gesetzt wird sie nur, wenn API und
Oberfläche getrennt betrieben werden.

---

## Tests und Prüfungen

Alle vier laufen auch in CI, und **jede kann rot werden**:

```bash
# Backend: Formatierung, Linting, Tests mit Abdeckungsschwelle
flake8 backend/
black --line-length=120 --check backend/
isort --profile=black --line-length=120 --check-only backend/
cd backend && pytest tests -q --cov=. --cov-fail-under=50

# Frontend
cd frontend && npx eslint . && npx vitest run && npm run build

# End-to-End (Playwright, benötigt eine laufende Instanz)
cd frontend && npx playwright test
```

Stand 2026-08-25: **53 Backend-Tests**, **46 Frontend-Tests**, Backend-Abdeckung
**53 %**, 0 Lint-Fehler auf beiden Seiten.

Einige Tests sind Wächter gegen Fehlerklassen, die schon einmal in der
Produktion standen — sie prüfen nicht nur, dass etwas funktioniert, sondern dass
eine bestimmte Art von Fehler nicht zurückkommen kann:

- `frontend/src/test/i18n-integrity.test.js` — Namensräume mit Doppelpunkt,
  deckungsgleiche Sprachdateien, `<html lang>`, keine fest verdrahteten Locales.
- `frontend/src/utils/format.test.js` — Datums-, Zahl- und Währungsformate in
  allen vier Sprachen, auch in der Form **mit** Region (`de-DE`).

---

## Produktivbetrieb

Gebaut wird **außerhalb** des Zielsystems; ausgeliefert werden getaggte Images.
Der Tag ist der Commit-SHA — dadurch gibt es einen Rückweg.

```bash
SHA=$(git rev-parse --short HEAD)

docker build -f backend/Dockerfile.prod  -t travelmind-backend:$SHA  backend/
docker build -f frontend/Dockerfile.prod -t travelmind-frontend:$SHA frontend/

# Auf den Zielrechner übertragen
docker save travelmind-backend:$SHA travelmind-frontend:$SHA | gzip -1 \
  | ssh <benutzer>@<host> 'gunzip | docker load'
```

Auf dem Zielrechner liegen neben `docker-compose.prod.yml` zwei Dateien:

| Datei | Inhalt |
| --- | --- |
| `.env` | **Nur Geheimnisse**: `POSTGRES_PASSWORD`, `JWT_SECRET`, `SECRET_KEY` |
| `deploy-params.conf` | Alles andere: `TRAVELMIND_TAG`, `TRAVELMIND_DATA`, `TRAVELMIND_PORT`, `CORS_ORIGINS`, `TZ` |

```bash
docker compose -f docker-compose.prod.yml \
  --env-file .env --env-file deploy-params.conf up -d
```

**Rollback** ist eine Zeile: `TRAVELMIND_TAG` in `deploy-params.conf` auf den
vorherigen Commit-SHA setzen und `up -d` wiederholen. Die alten Images bleiben
unter ihrem Tag liegen.

Die Bind-Mounts `uploads/` und `backups/` müssen **uid/gid 1001** gehören — das
ist die im Image festgenagelte Kennung, unter der die Container laufen:

```bash
chown -R 1001:1001 <datenverzeichnis>/uploads <datenverzeichnis>/backups
```

Alle drei Container laufen non-root, mit `cap_drop: ALL` und
`no-new-privileges`; das Frontend zusätzlich mit schreibgeschütztem
Dateisystem.

---

## Konfiguration

`.env.example` listet alle Variablen mit Erläuterung. Die wichtigsten:

| Variable | Bedeutung |
| --- | --- |
| `JWT_SECRET`, `SECRET_KEY` | **Pflicht.** Ohne sichere Werte startet das Backend nicht. |
| `DATABASE_URL` | `postgresql+asyncpg://…` für PostgreSQL |
| `CORS_ORIGINS` | Komma-getrennte Liste erlaubter Herkünfte — **mit Port** |
| `ENABLE_DEMO_MODE` | Steuert Demo-Reisen in `routes/trips.py`. In der Produktion `false`. |
| `VITE_API_URL` | Nur setzen, wenn API und Oberfläche getrennt laufen. Sonst leer lassen — die Oberfläche spricht dann den relativen Pfad `/api` an. |

KI-Anbieter werden **pro Benutzer** in den Einstellungen der Oberfläche
hinterlegt, nicht über Umgebungsvariablen.

---

## Dokumentation

| Datei | Inhalt |
| --- | --- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Aufbau von Backend und Frontend |
| [`docs/BACKUP.md`](docs/BACKUP.md) | Sicherung und Wiederherstellung |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Gemessener Zustand und Umbauplan |
| [`docs/CLAUDE_API_EXAMPLES.md`](docs/CLAUDE_API_EXAMPLES.md) | Beispiele zur KI-Anbindung |
| `/docs` (nur Entwicklung) | OpenAPI-Oberfläche der API unter `http://localhost:8003/docs`. Hinter dem Produktions-nginx **nicht** erreichbar — dort beantwortet der SPA-Fallback den Pfad. |

---

## Mitarbeit

Vor einem Pull Request müssen die Prüfungen oben lokal grün sein. Die
`pre-commit`-Hooks nehmen einem den größten Teil davon ab:

```bash
pip install pre-commit && pre-commit install
pre-commit run --all-files
```

---

## Lizenz

MIT — siehe [LICENSE](LICENSE).
