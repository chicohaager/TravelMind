# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TravelMind is a self-hosted travel planning and diary application with AI assistance powered by Claude API. The app uses a FastAPI backend (Python) with React frontend (Vite), SQLite/PostgreSQL database, and provides features for trip planning, diary entries, budget tracking, and AI-powered travel recommendations.

## Development Commands

### Backend (FastAPI/Python)

```bash
# Start development server (with hot reload)
cd backend
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
pytest -v  # verbose mode
pytest backend/tests/  # specific directory
```

### Frontend (React/Vite)

```bash
# Start development server
cd frontend
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Install dependencies
npm install

# Linting
npm run lint

# Code formatting
npm run format
```

### Docker

```bash
# Start all services (development)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Rebuild containers
docker-compose build --no-cache
```

## Architecture

### Backend Structure

**Layered Architecture Pattern:**
- **Routes** (`backend/routes/`): FastAPI routers handling HTTP endpoints
- **Services** (`backend/services/`): Business logic layer (e.g., Claude AI integration)
- **Models** (`backend/models/`): SQLAlchemy ORM models and database schema
- **Utils** (`backend/utils/`): Helper functions and utilities

**Database Models:**
- `User`: User accounts with authentication
- `Trip`: Main trip entity with destination, dates, budget, interests
- `Participant`: Many-to-many relationship for trip collaboration
- `DiaryEntry`: Markdown-based travel journal entries
- `Place`: Points of interest with GPS coordinates
- `Expense`: Budget tracking for trips

**Key Routes:**
- `/api/auth/*`: JWT authentication (register, login, logout)
- `/api/trips/*`: CRUD operations for trips
- `/api/diary/*`: Diary entry management
- `/api/places/*`: POI management
- `/api/timeline/*`: Timeline view aggregation
- `/api/budget/*`: Expense tracking and budget overview
- `/api/ai/*`: Multi-provider AI integration endpoints (Groq, Claude, OpenAI, Gemini)

### Frontend Structure

**Component Organization:**
- `src/pages/`: Route-level components (Home, Trips, TripDetail, Diary, AIAssistant)
- `src/components/`: Reusable UI components
- `src/components/layout/`: Layout components (Navbar, Sidebar, Layout wrapper)
- `src/contexts/`: React contexts (AuthContext for user state)
- `src/services/`: API client with axios

**State Management:**
- React Query for server state (trips, diary entries, places)
- React Context for authentication state
- Local component state for UI interactions

### Database

**Async SQLAlchemy 2.0:**
- Async database operations throughout
- Connection pooling configured differently for SQLite vs PostgreSQL
- Database initialized automatically on app startup via `init_db()` in `main.py:lifespan`

**Session Management:**
- Use `get_db()` dependency for route handlers
- Sessions are automatically committed/rolled back
- Example usage in routes:
  ```python
  from models.database import get_db

  @router.get("/trips")
  async def get_trips(db: AsyncSession = Depends(get_db)):
      result = await db.execute(select(Trip))
      return result.scalars().all()
  ```

## AI Integration (Multi-Provider)

**Service Location:** `backend/services/ai_service.py`

**Supported Providers:**
- **Groq (FREE!)**: llama-3.3-70b-versatile - Fast, free inference with Llama 3.3
- **Claude (Anthropic)**: claude-3-5-sonnet-20241022
- **OpenAI**: gpt-4-turbo-preview
- **Google Gemini**: gemini-pro

**User Configuration:**
- Each user configures their own AI provider and API key in Settings
- API keys are encrypted using Fernet symmetric encryption
- Stored securely in the database (never exposed in API responses)
- Users can validate their API key before saving

**Core Methods:**
- `suggest_destinations()`: Recommends 5 destinations based on interests, duration, budget
- `plan_trip()`: Creates detailed multi-day itinerary
- `describe_destination()`: Generates poetic destination descriptions
- `chat()`: Conversational Q&A about destinations
- `get_local_tips()`: Local recommendations by category

**Response Handling:**
- Prompts request structured JSON output
- Service parses JSON from AI response
- Falls back to raw response if JSON parsing fails

**Security:**
- API keys encrypted with SECRET_KEY from environment
- Encryption service: `backend/utils/encryption.py`
- Keys decrypted only when needed for API calls
- Never returned in API responses

## Environment Configuration

**Required Variables:**
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `JWT_SECRET`: Secret key for JWT token signing
- `SECRET_KEY`: Secret key for encrypting API keys (IMPORTANT: Keep this secure!)

**Optional Variables:**
- `BACKEND_PORT`: Backend port (default: 8000)
- `BACKEND_RELOAD`: Enable hot reload (default: true)
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated)
- `ENABLE_AI_FEATURES`: Toggle AI features (default: true)
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, WARNING, ERROR)

**User-Specific Configuration (in Settings UI):**
- AI Provider (Groq, Claude, OpenAI, or Gemini)
- API Key for selected provider
  - **Groq (FREE!)**: Get from https://console.groq.com/ - No credit card required
  - Claude: Get from https://console.anthropic.com/
  - OpenAI: Get from https://platform.openai.com/
  - Gemini: Get from https://makersuite.google.com/

See `.env.example` for complete configuration reference.

## Testing

**Backend Tests:**
- Framework: pytest with pytest-asyncio
- Test directory: `backend/tests/`
- Run all tests: `pytest`
- Run with coverage: `pytest --cov=backend`

**Frontend Tests:**
- Framework: React Testing Library (when added)
- Component tests: `npm test`

## API Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Authentication Flow

**JWT-based authentication:**
1. User registers/logs in via `/api/auth/register` or `/api/auth/login`
2. Backend returns JWT access token
3. Frontend stores token and includes in Authorization header: `Bearer <token>`
4. Protected routes validate token via JWT middleware
5. Token includes user ID and username in payload

**Implementation:**
- Password hashing: bcrypt via passlib
- Token generation: python-jose
- Token validation: FastAPI dependency injection

## File Upload

**Upload Handling:**
- Directory: `./uploads/` (created automatically on startup)
- Max file size: 10MB (configurable via `MAX_UPLOAD_SIZE_MB`)
- Allowed extensions: jpg, jpeg, png, gif, webp, pdf
- Files served via `/uploads` static file mount

## Database Migrations

**Alembic Setup:**
- Alembic is installed but migrations not yet initialized
- To set up: `cd backend && alembic init alembic`
- Current approach: Auto-create tables on startup via `init_db()`

## Design System

**Styling:**
- Tailwind CSS with custom configuration
- Primary color: Indigo (`#6366F1`)
- Secondary color: Orange (`#F59E0B`)
- Typography: Inter (body), Poppins (headings)
- Dark mode support built-in

**Custom Classes:**
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-outline`: Button variants
- `.card`: Card container with shadow and padding
- `.input`: Form input styling
- `.badge`: Tag/badge components

**Animation:**
- Framer Motion for page transitions and component animations
- Smooth transitions configured in Tailwind

## Common Patterns

**Adding a New API Endpoint:**
1. Create/update router in `backend/routes/`
2. Define Pydantic schemas for request/response
3. Implement handler using async/await
4. Use `get_db()` dependency for database access
5. Include router in `main.py`

**Adding a New Database Model:**
1. Create model file in `backend/models/`
2. Inherit from `Base` (declarative_base)
3. Define columns and relationships
4. Import in `models/database.py:init_db()` to register
5. Restart backend to auto-create table

**Adding a New Frontend Page:**
1. Create component in `frontend/src/pages/`
2. Add route in `App.jsx`
3. Update navigation in `Navbar.jsx` or `Sidebar.jsx`
4. Use React Query for data fetching
5. Follow existing component patterns

## Troubleshooting

**Database locked (SQLite):**
- SQLite uses NullPool to avoid connection conflicts
- Consider PostgreSQL for production

**CORS errors:**
- Check `CORS_ORIGINS` in `.env` matches frontend URL
- Development: `http://localhost:5173` for Vite
- Default ports: Backend 8000, Frontend 5173

**Claude API errors:**
- Verify `CLAUDE_API_KEY` is set correctly
- Check API quota at Anthropic console
- Review logs for detailed error messages

**Import errors in backend:**
- All models must be imported in `models/database.py:init_db()` for table creation
- Routes are imported in `main.py` - ensure new routes are added there

## Project Status

**Production-ready features:**
- Complete API structure with all major endpoints
- Claude AI integration with multiple use cases
- Authentication and user management
- Database models and relationships
- React frontend with routing and layout
- Docker containerization

**In development:**
- Map integration (Leaflet setup present, needs component integration)
- PWA offline capabilities
- PDF export functionality
- WebSocket for real-time collaboration
- Comprehensive test coverage
