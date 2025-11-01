# 🏗️ TravelMind - Architektur-Dokumentation

## Systemübersicht

TravelMind ist eine moderne, dreischichtige Web-Anwendung:

```
┌─────────────────────────────────────────────────────┐
│                  Client (Browser)                    │
│  • React 18 (UI Framework)                          │
│  • Tailwind CSS (Styling)                           │
│  • Framer Motion (Animationen)                      │
│  • Leaflet (Karten)                                 │
└─────────────────┬───────────────────────────────────┘
                  │
                  │ HTTP/REST + WebSocket
                  │
┌─────────────────▼───────────────────────────────────┐
│              Application Server                      │
│  • FastAPI (Python)                                 │
│  • Uvicorn (ASGI Server)                            │
│  • Pydantic (Validation)                            │
│  • SQLAlchemy (ORM)                                 │
└─────────────────┬───────────────────────────────────┘
                  │
                  ├──────────────┐
                  │              │
┌─────────────────▼───┐    ┌────▼──────────────┐
│    Database         │    │  External APIs    │
│  • SQLite/Postgres  │    │  • Claude API     │
│  • Alembic          │    │  • Maps API       │
└─────────────────────┘    └───────────────────┘
```

## Frontend-Architektur

### Technologie-Stack

- **React 18**: Component-basierte UI
- **Vite**: Build-Tool (schneller als Webpack)
- **React Router**: Client-Side Routing
- **Tailwind CSS**: Utility-First CSS
- **Framer Motion**: Animations-Library
- **React Query**: Server State Management
- **Zustand**: Client State Management (geplant)
- **Axios**: HTTP-Client

### Verzeichnisstruktur

```
frontend/src/
├── components/          # Wiederverwendbare Komponenten
│   ├── layout/         # Layout-Komponenten
│   │   ├── Layout.jsx
│   │   ├── Navbar.jsx
│   │   └── Sidebar.jsx
│   ├── ui/             # UI-Basiskomponenten (geplant)
│   └── features/       # Feature-spezifische Komponenten (geplant)
│
├── pages/              # Seiten-Komponenten (Route Targets)
│   ├── Home.jsx
│   ├── Trips.jsx
│   ├── TripDetail.jsx
│   ├── AIAssistant.jsx
│   ├── Diary.jsx
│   └── NotFound.jsx
│
├── services/           # API-Services
│   └── api.js         # Axios-Client + API-Funktionen
│
├── hooks/             # Custom React Hooks (geplant)
│   ├── useAuth.js
│   ├── useTrips.js
│   └── useAI.js
│
├── styles/            # Globale Styles
│   └── index.css
│
├── assets/            # Statische Assets
│
├── App.jsx            # Haupt-App (Routing)
└── main.jsx           # Entry Point
```

### Component-Hierarchie

```
App (Routing)
└── Layout
    ├── Navbar
    ├── Sidebar
    └── Outlet (Route Content)
        ├── Home
        ├── Trips
        │   └── TripCard (mehrere)
        ├── TripDetail
        │   ├── TripHeader
        │   ├── TripMap
        │   ├── PlacesList
        │   └── DiaryEntries
        ├── AIAssistant
        │   ├── ChatMessages
        │   ├── ChatInput
        │   └── QuickActions
        └── Diary
            └── DiaryEntry (mehrere)
```

### State Management

**Server State** (React Query):
```javascript
// Trips abrufen
const { data, isLoading } = useQuery({
  queryKey: ['trips'],
  queryFn: tripsService.getAll
})

// Trip erstellen
const mutation = useMutation({
  mutationFn: tripsService.create,
  onSuccess: () => {
    queryClient.invalidateQueries(['trips'])
  }
})
```

**Client State** (Zustand - geplant):
```javascript
// Store für UI-State
const useUIStore = create((set) => ({
  darkMode: false,
  sidebarOpen: false,
  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen }))
}))
```

## Backend-Architektur

### Technologie-Stack

- **FastAPI**: Modernes Python Web Framework
- **Uvicorn**: ASGI Server
- **SQLAlchemy 2.0**: ORM (async)
- **Alembic**: Datenbank-Migrationen
- **Pydantic**: Data Validation
- **python-jose**: JWT-Tokens
- **passlib**: Password Hashing
- **anthropic**: Claude API Client

### Verzeichnisstruktur

```
backend/
├── models/                 # Datenbank-Modelle
│   ├── database.py        # DB-Setup & Session
│   ├── user.py
│   ├── trip.py
│   ├── diary.py
│   └── place.py
│
├── routes/                # API-Endpunkte
│   ├── __init__.py
│   ├── ai.py             # /api/ai/*
│   ├── trips.py          # /api/trips/*
│   ├── diary.py          # /api/diary/*
│   ├── places.py         # /api/places/*
│   ├── auth.py           # /api/auth/*
│   └── users.py          # /api/users/*
│
├── services/              # Business Logic
│   ├── claude.py         # Claude API Integration
│   ├── auth.py           # Auth-Service (geplant)
│   └── email.py          # Email-Service (geplant)
│
├── utils/                 # Hilfsfunktionen
│   ├── jwt.py            # JWT-Funktionen (geplant)
│   └── validators.py     # Custom Validators (geplant)
│
├── tests/                 # Tests
│
├── main.py               # FastAPI App
└── requirements.txt      # Dependencies
```

### API-Struktur

**Layered Architecture:**

```
Request → Router → Service → Model → Database
         ↓
      Pydantic
      Validation
```

**Beispiel-Flow:**

```python
# 1. Request kommt rein
@router.post("/trips")
async def create_trip(trip: TripCreate):  # ← Pydantic Validation
    # 2. Business Logic (Service Layer)
    result = await trip_service.create(trip)

    # 3. Datenbank-Operation (Model Layer)
    # db.add(trip_model)

    return result
```

### Datenbank-Schema

```sql
┌─────────────────┐
│     users       │
├─────────────────┤
│ id (PK)         │
│ username        │
│ email           │
│ hashed_password │
│ created_at      │
└────────┬────────┘
         │
         │ 1:N
         │
┌────────▼────────┐
│     trips       │
├─────────────────┤
│ id (PK)         │
│ owner_id (FK)   │
│ title           │
│ destination     │
│ start_date      │
│ end_date        │
│ budget          │
│ interests (JSON)│
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
    │ 1:N      │ 1:N
    │          │
┌───▼──────┐  ┌▼──────────┐
│  places  │  │   diary   │
├──────────┤  │  entries  │
│ id (PK)  │  ├───────────┤
│ trip_id  │  │ id (PK)   │
│ name     │  │ trip_id   │
│ lat/lng  │  │ author_id │
│ category │  │ title     │
│ visited  │  │ content   │
└──────────┘  │ photos    │
              └───────────┘
```

### Claude AI Service

**Funktionen:**

```python
class ClaudeService:
    async def suggest_destinations(interests, duration, budget)
    async def plan_trip(destination, duration, interests)
    async def describe_destination(destination)
    async def chat(message, context)
    async def get_local_tips(destination, category)
```

**Prompt-Engineering:**

Jede Funktion nutzt spezielle Prompts:

```python
# Beispiel: Reiseplan
prompt = f"""Du bist ein erfahrener Reiseplaner.
Erstelle einen {duration}-tägigen Plan für {destination}.

Interessen: {', '.join(interests)}

Ausgabe als strukturiertes JSON mit:
- Tages-Aktivitäten
- Restaurants
- Kosten
- Praktische Tipps
"""
```

## API-Endpunkte

### AI-Assistent

```
POST /api/ai/suggest          # Reiseziele vorschlagen
POST /api/ai/plan             # Reiseplan erstellen
POST /api/ai/describe         # Destination beschreiben
POST /api/ai/chat             # Chat mit Claude
POST /api/ai/local-tips       # Lokale Geheimtipps
GET  /api/ai/status           # AI-Status prüfen
```

### Trips

```
GET    /api/trips             # Alle Reisen
POST   /api/trips             # Neue Reise
GET    /api/trips/:id         # Einzelne Reise
PUT    /api/trips/:id         # Reise aktualisieren
DELETE /api/trips/:id         # Reise löschen
GET    /api/trips/:id/summary # Statistiken
```

### Diary

```
GET    /api/diary/:tripId              # Alle Einträge
POST   /api/diary/:tripId              # Neuer Eintrag
PUT    /api/diary/:id                  # Eintrag bearbeiten
DELETE /api/diary/:id                  # Eintrag löschen
POST   /api/diary/:tripId/export       # Export (PDF/MD)
```

### Places

```
GET    /api/places/:tripId/places      # Alle Orte
POST   /api/places/:tripId/places      # Ort hinzufügen
PUT    /api/places/places/:id          # Ort bearbeiten
DELETE /api/places/places/:id          # Ort löschen
PUT    /api/places/places/:id/visited  # Als besucht markieren
```

### Auth

```
POST /api/auth/register       # Registrierung
POST /api/auth/login          # Login
POST /api/auth/logout         # Logout
GET  /api/auth/me             # Aktueller User
POST /api/auth/refresh        # Token erneuern
```

## Sicherheit

### Authentifizierung

**JWT-Token-Flow:**

```
1. Login → Server validiert Credentials
2. Server generiert JWT-Token
3. Client speichert Token (localStorage)
4. Client sendet Token bei jedem Request (Header)
5. Server validiert Token
```

**JWT-Struktur:**

```json
{
  "sub": "user_id",
  "username": "max",
  "exp": 1234567890
}
```

### Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])

# Hash erstellen
hashed = pwd_context.hash(password)

# Verifizieren
is_valid = pwd_context.verify(password, hashed)
```

### CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Datenbank-Zugriff

### Async SQLAlchemy

```python
# Session erstellen
async with AsyncSessionLocal() as session:
    # Query ausführen
    result = await session.execute(
        select(Trip).where(Trip.owner_id == user_id)
    )
    trips = result.scalars().all()
```

### Relationship Loading

```python
# Eager Loading
stmt = select(Trip).options(
    selectinload(Trip.places),
    selectinload(Trip.diary_entries)
)
```

## Deployment

### Docker-Architektur

```
docker-compose.yml
├── backend (FastAPI)
│   └── Port 8000
├── frontend (React/Nginx)
│   └── Port 80/5173
└── db (PostgreSQL)
    └── Port 5432
```

### Build-Prozess

**Frontend:**
```bash
npm run build         # Vite Build
→ dist/              # Static Files
→ Nginx Server       # Serving
```

**Backend:**
```bash
pip install          # Dependencies
→ uvicorn/gunicorn   # ASGI Server
```

## Performance-Optimierung

### Frontend

1. **Code Splitting**: Automatisch durch Vite
2. **Lazy Loading**: React.lazy() für Routes
3. **Image Optimization**: WebP-Format
4. **Caching**: Service Worker (PWA)

### Backend

1. **Async I/O**: Alles async
2. **Connection Pooling**: SQLAlchemy Pool
3. **Query Optimization**: Eager Loading
4. **Caching**: Redis (geplant)

### Datenbank

1. **Indexe**: Auf häufig gesuchten Feldern
2. **Query-Optimierung**: SELECT nur benötigte Felder
3. **N+1 Problem**: Vermeiden durch Eager Loading

## Monitoring & Logging

### Strukturiertes Logging

```python
import structlog

logger = structlog.get_logger()

logger.info("trip_created",
    trip_id=trip.id,
    user_id=user.id,
    destination=trip.destination
)
```

### Health Checks

```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": await check_db(),
        "ai_service": await check_ai()
    }
```

## Testing-Strategie

### Backend Tests

```python
# Unit Tests
def test_create_trip():
    trip = create_trip_service(data)
    assert trip.title == "Test"

# Integration Tests
async def test_api_create_trip(client):
    response = await client.post("/api/trips", json=data)
    assert response.status_code == 201
```

### Frontend Tests

```javascript
// Component Tests
test('renders trip card', () => {
  render(<TripCard trip={mockTrip} />)
  expect(screen.getByText('Lissabon')).toBeInTheDocument()
})

// E2E Tests (Playwright/Cypress)
test('user can create trip', async () => {
  await page.goto('/trips')
  await page.click('text=Neue Reise')
  // ...
})
```

## Erweiterungen (Roadmap)

### Phase 1 - MVP (aktuell)
- ✅ Grundstruktur
- ✅ Claude AI Integration
- ✅ Design-System
- 🚧 Datenbank-Anbindung

### Phase 2 - Features
- 📍 Karten-Integration (Leaflet)
- 📸 Foto-Upload & Galerie
- 📄 PDF-Export
- 🔔 Benachrichtigungen

### Phase 3 - Collaboration
- 👥 Multi-User Support
- 💬 Echtzeit-Chat (WebSocket)
- 🔗 Reisen teilen
- 📊 Kollaborative Planung

### Phase 4 - Advanced
- 📱 Native Mobile App (React Native)
- 🌐 Offline-First (PWA)
- 🔍 Volltextsuche
- 📈 Analytics Dashboard

---

**Dokumentations-Version**: 1.0
**Letztes Update**: 2024-10-09
