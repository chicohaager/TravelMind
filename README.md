# 🌍 TravelMind

**Deine intelligente Reiseplanungs- und Tagebuch-App mit KI-Unterstützung**

TravelMind ist eine selbst gehostete Webanwendung zur Planung, Organisation und Dokumentation deiner Reisen. Mit Multi-Provider AI-Unterstützung (Claude, OpenAI, Gemini) erhältst du personalisierte Empfehlungen und intelligente Reisevorschläge.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11-blue)
![React](https://img.shields.io/badge/react-18-blue)

---

## ✨ Features

### 🗺️ Reiseplanung
- **Reisen erstellen und verwalten** mit Titel, Beschreibung, Destination
- **Interessen auswählen** für personalisierte Empfehlungen
- **Budgetverwaltung** mit Ausgaben-Tracking
- **Teilnehmerverwaltung** für Gruppenreisen
- **Zeitraum festlegen** mit Start- und Enddatum
- **Cover-Bilder hochladen** für jede Reise

### 🤖 KI-Assistent (Multi-Provider)
- **Wähle deinen AI-Provider**: Claude (Anthropic), OpenAI (GPT-4), oder Google Gemini
- **Eigener API-Key**: Jeder Nutzer verwendet seinen eigenen API-Key
- **Verschlüsselte Speicherung**: API-Keys werden sicher verschlüsselt gespeichert
- **Personalisierte Empfehlungen** basierend auf deinen Interessen
- **Automatische Ortsvorschläge** mit Beschreibungen und Details
- **Intelligente Reise-Tipps** angepasst an Budget und Dauer
- **Destination-Beschreibungen** mit atmosphärischen Texten
- **Best-Time Empfehlungen** für jeden Ort (Vormittag/Nachmittag/Abend)

### 📍 Orte & Sehenswürdigkeiten
- **Orte sammeln** mit Name, Beschreibung, Kategorie
- **GPS-Koordinaten** für Kartenansicht
- **Google Maps Integration** - Direktlink zu jedem Ort
- **Import von Reiseführern** (TripAdvisor, Lonely Planet)
- **Automatische Ortssuche** nach Destination
- **Besuchsstatus markieren** (besucht/nicht besucht)
- **Kosten schätzen** pro Ort

### 📓 Reisetagebuch
- **Tagebucheinträge schreiben** mit Markdown-Support
- **Fotos hochladen** (mehrere pro Eintrag)
- **Stimmung festhalten** (happy, neutral, sad)
- **Bewertungen vergeben** (1-5 Sterne)
- **Tags hinzufügen** zur Organisation
- **Standort speichern** für jeden Eintrag
- **Export als PDF oder Markdown**

### 📅 Timeline-Ansicht
- **Chronologische Übersicht** aller Aktivitäten
- **Tagesplanung** mit Zeitslots
- **Drag & Drop Sortierung**
- **Routenoptimierung** per KI

### 💰 Budget-Tracker
- **Ausgaben erfassen** mit Kategorie und Datum
- **Budget-Übersicht** mit Fortschrittsbalken
- **Mehrere Währungen** unterstützt
- **Kostenteilung** für Gruppenreisen
- **Visualisierung** nach Kategorien

### 👥 Teilnehmerverwaltung
- **Mitreisende hinzufügen** mit Namen und Kontakt
- **Profilfotos** hochladen
- **Kostenaufteilung** berechnen

---

## 🚀 Installation

### Voraussetzungen
- **Docker** und **Docker Compose** installiert
- **AI API Key** für KI-Features (optional, aber empfohlen)
  - Claude: https://console.anthropic.com/
  - OpenAI: https://platform.openai.com/
  - Gemini: https://makersuite.google.com/

### 1. Repository klonen
```bash
git clone https://github.com/dein-username/travelmind.git
cd TravelMind
```

### 2. Umgebungsvariablen konfigurieren
```bash
cp .env.example .env
```

Bearbeite die `.env` Datei:
```env
# Backend
BACKEND_PORT=8000
JWT_SECRET=dein-geheimer-schluessel-hier
SECRET_KEY=dein-verschluesselungs-key-hier

# Database (optional, Standard: SQLite)
DATABASE_URL=sqlite+aiosqlite:///./travelmind.db

# CORS (Frontend URL)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

**Hinweis:** AI-Provider und API-Keys werden nicht mehr global konfiguriert, sondern von jedem Nutzer individuell in den Einstellungen hinterlegt.

### 3. Anwendung starten
```bash
# Entwicklung
docker-compose up -d

# Produktion
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Anwendung öffnen
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Dokumentation**: http://localhost:8000/docs

---

## 📖 Verwendung

### Erste Schritte

#### 1. Account erstellen
- Öffne http://localhost:5173
- Klicke auf "Registrieren"
- Gib Benutzername und Passwort ein

#### 2. Erste Reise anlegen
- Klicke auf "Neue Reise"
- Gib Titel und Destination ein (z.B. "La Palma: Naturparadies")
- Wähle Start- und Enddatum
- Setze dein Budget
- **Wichtig**: Wähle deine Interessen aus (für KI-Empfehlungen)

#### 3. Interessen festlegen
- Gehe zum **Übersicht**-Tab deiner Reise
- Klicke bei "Interessen" auf **Bearbeiten**
- Wähle passende Interessen aus:
  - Natur, Fotografie, Sport, Abenteuer
  - Kultur, Geschichte, Kunst, Architektur
  - Essen, Shopping, Nachtleben
  - Strand, Entspannung, Städtereise

#### 4. KI-Empfehlungen erhalten
- Wechsle zum **Empfehlungen**-Tab
- Die KI analysiert automatisch:
  - Deine Destination
  - Deine Interessen
  - Dein Budget
  - Deine Reisedauer
- Du erhältst 6-8 personalisierte Orte mit:
  - Farbigem Kategorie-Header
  - Beschreibung und Grund der Empfehlung
  - Best-Time (wann am besten besuchen)
  - Geschätzte Kosten und Dauer
  - **Google Maps Link**
  - **Hinzufügen-Button**

#### 5. Orte hinzufügen
**Option A: Aus KI-Empfehlungen**
- Klicke auf "Hinzufügen" bei einer Empfehlung

**Option B: Manuell**
- Gehe zum **Orte**-Tab
- Klicke "Ort hinzufügen"
- Fülle das Formular aus

**Option C: Import aus Reiseführern**
- Gehe zum **Orte**-Tab
- Klicke "Import aus Reiseführer"
- Gib deine Destination ein (z.B. "Paris")
- Wähle gefundene Orte aus
- Klicke "Ausgewählte importieren"

#### 6. Tagebuch führen während der Reise
- Gehe zum **Tagebuch**-Tab
- Klicke "Neuer Eintrag"
- Schreibe deine Erlebnisse (Markdown unterstützt)
- Lade Fotos hoch (mehrere möglich)
- Setze deine Stimmung und Bewertung
- Speichere den Eintrag

#### 7. Budget tracken
- Gehe zum **Budget**-Tab
- Klicke "Ausgabe hinzufügen"
- Wähle Kategorie (Transport, Unterkunft, Essen, etc.)
- Gib Betrag und Beschreibung ein
- Die Übersicht zeigt automatisch:
  - Gesamtausgaben
  - Verbleibendes Budget
  - Prozentuale Auslastung
  - Ausgaben nach Kategorie

---

## 🎨 Features im Detail

### KI-Empfehlungen System

Die KI-Empfehlungen nutzen Claude AI von Anthropic und analysieren:

1. **Deine Interessen**
   - Werden im Übersicht-Tab festgelegt
   - Mindestens 2-3 Interessen empfohlen
   - Beeinflussen Art und Stil der Empfehlungen

2. **Bereits geplante Orte**
   - KI vermeidet Duplikate
   - Schlägt ergänzende Orte vor
   - Sorgt für ausgewogene Mischung

3. **Budget & Dauer**
   - Empfehlungen passen zu deinem Budget
   - Kostenlose und kostenpflichtige Orte
   - Zeitplanung berücksichtigt Reisedauer

4. **Empfehlungs-Karte zeigt:**
   - **Gradient-Header** in Kategorie-Farbe:
     - 🍽️ Restaurant: Orange → Rot → Pink
     - 🎯 Attraction: Lila → Pink → Rot
     - 🏖️ Beach: Blau → Cyan → Türkis
     - 👁️ Viewpoint: Gelb → Orange → Rot
     - 🌳 Park: Grün → Smaragd → Türkis
   - **Großes Icon** (Restaurant 🍽️, Beach 🏖️, etc.)
   - **Name & Beschreibung** des Ortes
   - **Grund-Badge**: "Warum empfohlen?"
   - **Best-Time Badge**: Vormittag/Nachmittag/Abend1
   - **Dauer & Kosten**: Geschätzte Werte
   - **2 Action-Buttons**:
     - "Maps" → Öffnet Google Maps
     - "Hinzufügen" → Speichert in deiner Reise

### Guide Import Funktion

Automatischer Import von Orten aus Online-Reiseführern:

**Unterstützte Quellen:**
- TripAdvisor
- Lonely Planet
- Weitere folgen...

**So funktioniert's:**
1. Gib nur die Destination ein (z.B. "Paris", "La Palma")
2. System durchsucht automatisch mehrere Quellen
3. Extrahiert Namen, Beschreibungen, Kategorien
4. Entfernt Duplikate
5. Zeigt gefilterte Liste zum Auswählen
6. Import mit einem Klick

### Tagebuch-Export

**Markdown-Export:**
- Strukturierte .md Datei
- Alle Einträge chronologisch
- Fotos als Links
- Tags und Bewertungen

**PDF-Export:**
- Professionell formatiert
- Eingebettete Bilder
- Überschriften und Metadaten
- Druckfertig

### Budget-Funktionen

**Kategorien:**
- 🚗 Transport
- 🏨 Unterkunft
- 🍽️ Essen & Trinken
- 🎭 Aktivitäten & Eintritte
- 🛍️ Shopping
- 💊 Gesundheit
- 📱 Sonstiges

**Visualisierung:**
- Fortschrittsbalken (grün/gelb/rot)
- Kreisdiagramm nach Kategorien
- Tabelle aller Ausgaben
- Sortierung nach Datum/Betrag/Kategorie

**Kostenteilung:**
- Für Gruppenreisen
- Automatische Berechnung pro Person
- Übersicht wer was bezahlt hat

---

## 🛠️ Technologie-Stack

### Backend
- **FastAPI** - Modernes Python Web Framework
- **SQLAlchemy 2.0** - Async ORM
- **SQLite/PostgreSQL** - Datenbank
- **Python-Jose** - JWT Authentication
- **Anthropic Claude API** - KI-Integration
- **BeautifulSoup4** - Web Scraping für Guide-Import
- **ReportLab** - PDF-Generierung

### Frontend
- **React 18** - UI Framework
- **Vite** - Build Tool & Dev Server
- **React Router** - Navigation
- **TanStack Query (React Query)** - State & Caching
- **Framer Motion** - Animationen
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **React Hot Toast** - Benachrichtigungen
- **Leaflet** - Karten-Integration

### Infrastructure
- **Docker & Docker Compose** - Containerisierung
- **Nginx** - Reverse Proxy (Production)
- **Uvicorn** - ASGI Server

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────┐
│                 Frontend (React + Vite)              │
│  • TailwindCSS + Framer Motion                      │
│  • React Query für State Management                 │
│  • Responsive Design (Mobile-First)                 │
└─────────────────┬───────────────────────────────────┘
                  │
                  │ REST API (JSON)
                  │
┌─────────────────▼───────────────────────────────────┐
│              Backend (FastAPI + Python)              │
│  • RESTful API Endpoints                            │
│  • JWT Authentication                               │
│  • Claude API Integration                           │
│  • File Upload Management                           │
│  • BeautifulSoup4 Web Scraping                     │
└─────────────────┬───────────────────────────────────┘
                  │
                  │ SQLAlchemy ORM (Async)
                  │
┌─────────────────▼───────────────────────────────────┐
│            Database (SQLite/PostgreSQL)              │
│  • Users, Trips, Places, Diary Entries             │
│  • Budget, Expenses, Participants                   │
│  • Timeline Events                                  │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Konfiguration

### Umgebungsvariablen

#### Backend (`backend/.env`)
```env
# API Keys
CLAUDE_API_KEY=sk-ant-api03-xxxxx
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=2048

# Database
DATABASE_URL=sqlite+aiosqlite:///./travelmind.db
# Oder PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/travelmind

# Security
JWT_SECRET=dein-sehr-langer-zufälliger-geheimer-schlüssel
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200  # 30 Tage

# Server
BACKEND_PORT=8000
BACKEND_RELOAD=true
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Features
ENABLE_AI_FEATURES=true
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE_MB=10
```

#### Frontend (`frontend/.env`)
```env
VITE_API_URL=http://localhost:8000
```

---

## 📱 API Dokumentation

Die interaktive API-Dokumentation ist verfügbar unter:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Wichtige Endpoints

#### Authentication
```
POST /api/auth/register - Registrierung
POST /api/auth/login    - Login
GET  /api/auth/me       - Aktueller User
```

#### Trips
```
GET    /api/trips           - Alle Reisen
GET    /api/trips/{id}      - Einzelne Reise
POST   /api/trips           - Reise erstellen
PUT    /api/trips/{id}      - Reise aktualisieren
DELETE /api/trips/{id}      - Reise löschen
```

#### AI
```
POST /api/ai/personalized-recommendations - Personalisierte Empfehlungen
POST /api/ai/describe                     - Destination beschreiben
POST /api/ai/chat                         - Chat mit KI
```

#### Places
```
GET  /api/places/{trip_id}/places              - Orte einer Reise
POST /api/places/{trip_id}/places              - Ort hinzufügen
POST /api/places/{trip_id}/search-guides       - Guide-Import
POST /api/places/{trip_id}/import-places-bulk  - Bulk-Import
```

---

## 📁 Projektstruktur

```
TravelMind/
├── frontend/
│   ├── src/
│   │   ├── components/          # React-Komponenten
│   │   │   ├── layout/         # Navbar, Sidebar
│   │   │   ├── DiaryEntry.jsx
│   │   │   ├── PlaceCard.jsx
│   │   │   └── RecommendationsView.jsx  # KI-Empfehlungen
│   │   ├── pages/              # Seiten-Komponenten
│   │   │   ├── Home.jsx
│   │   │   ├── Trips.jsx
│   │   │   ├── TripDetail.jsx
│   │   │   ├── AIAssistant.jsx
│   │   │   └── Budget.jsx
│   │   ├── contexts/           # React Contexts
│   │   ├── services/           # API-Services
│   │   │   └── api.js
│   │   ├── utils/              # Helper Functions
│   │   └── App.jsx
│   ├── public/
│   ├── package.json
│   └── vite.config.js
├── backend/
│   ├── routes/                 # API-Endpunkte
│   │   ├── auth.py
│   │   ├── trips.py
│   │   ├── places.py
│   │   ├── diary.py
│   │   ├── budget.py
│   │   ├── timeline.py
│   │   └── ai.py
│   ├── models/                 # Datenbank-Modelle
│   │   ├── database.py
│   │   ├── user.py
│   │   ├── trip.py
│   │   └── ...
│   ├── services/               # Business Logic
│   │   ├── claude.py          # Claude API Integration
│   │   └── guide_parser.py    # Web Scraping
│   ├── utils/                  # Hilfsfunktionen
│   ├── main.py                 # FastAPI App
│   └── requirements.txt
├── uploads/                    # User-Uploads
├── docker-compose.yml
├── .env.example
├── CLAUDE.md                   # Projekt-Dokumentation für Claude
└── README.md
```

---

## 🐛 Troubleshooting

### Probleme und Lösungen

#### Frontend verbindet nicht mit Backend
```bash
# Prüfe ob Backend läuft:
docker-compose logs backend

# Prüfe CORS-Einstellungen:
# In .env: CORS_ORIGINS sollte Frontend-URL enthalten
```

#### KI-Empfehlungen funktionieren nicht
```bash
# Prüfe API-Key:
echo $CLAUDE_API_KEY

# Prüfe Backend-Logs:
docker-compose logs backend | grep -i "claude"

# Test API-Key:
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $CLAUDE_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

#### Datenbank-Fehler
```bash
# SQLite-Datenbank neu erstellen:
rm backend/travelmind.db
docker-compose restart backend

# PostgreSQL Connection-String prüfen:
# DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

---

## 🚢 Deployment (Produktion)

### Mit Docker Compose

1. **Production Compose File**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Umgebungsvariablen setzen**
   ```env
   # Wichtig für Produktion:
   BACKEND_RELOAD=false
   LOG_LEVEL=WARNING
   CORS_ORIGINS=https://deine-domain.com
   ```

3. **Reverse Proxy (Nginx)**
   ```nginx
   server {
       listen 80;
       server_name deine-domain.com;

       location / {
           proxy_pass http://localhost:5173;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }

       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

4. **SSL mit Let's Encrypt**
   ```bash
   certbot --nginx -d deine-domain.com
   ```

---

## 🤝 Contributing

Beiträge sind willkommen! Bitte beachte:

1. Fork das Repository
2. Erstelle einen Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Committe deine Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Öffne einen Pull Request

### Development Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

---

## 🔐 Sicherheit

### Best Practices

1. **JWT_SECRET ändern**
   ```bash
   # Generiere sicheren Key:
   openssl rand -hex 32
   ```

2. **Starke Passwörter verwenden**
   - Mindestens 8 Zeichen
   - Buchstaben, Zahlen, Sonderzeichen

3. **HTTPS in Produktion**
   - Nutze Reverse Proxy (Nginx, Caddy)
   - SSL-Zertifikate (Let's Encrypt)

4. **API-Key schützen**
   - Nie im Git commiten
   - Nutze `.env` Datei
   - Setze passende Berechtigungen

---

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizensiert. Siehe `LICENSE` Datei für Details.

---

## 🙏 Danksagungen

- **Anthropic** für die Claude AI API
- **FastAPI** Community
- **React** Team
- **Tailwind CSS** Contributors
- Alle Open Source Libraries die dieses Projekt möglich machen

---

## 📞 Support & Community

- **Issues**: [GitHub Issues](https://github.com/dein-username/travelmind/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dein-username/travelmind/discussions)

---

## 🗺️ Roadmap

### Geplante Features

- [ ] Mobile App (React Native)
- [ ] Offline-Modus (PWA)
- [ ] Mehrsprachigkeit (i18n)
- [ ] Foto-Galerien mit Lightbox
- [ ] Social Features (Reisen teilen)
- [ ] Import aus Google Maps/TripIt
- [ ] Wetter-Integration
- [ ] Flug-Tracking
- [ ] Hotel-Buchungen-Integration
- [ ] Collaborative Planning (Echtzeit)
- [ ] Kalender-Export (iCal)
- [ ] Backup & Sync

---

**Made with ❤️ and ☕ by the TravelMind Team**

*Happy Travels! 🌍✈️*
