"""
Pytest configuration and fixtures for TravelMind tests
"""

import os as _os
import sys
from pathlib import Path

# Der Leak-Abgleich der Passwortregeln (utils/password_policy.py) fragt bei
# Have I Been Pwned nach. In der Testsuite ist er ABGESCHALTET — nicht aus
# Bequemlichkeit, sondern weil ein Test, der vom Netz abhaengt, sporadisch rot
# wird und irgendwann uebersprungen. Die Regel selbst wird in
# test_password_policy.py vollstaendig geprueft, mit eingespeister Abfrage
# und in allen drei Betriebsarten.
#
# Muss VOR dem Import von utils.password_policy stehen: der Modus wird beim
# Importieren gelesen.
_os.environ.setdefault("PASSWORD_BREACH_CHECK", "off")

# Add parent directory to Python path so we can import from backend
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from main import app

# NEBENWIRKUNGS-IMPORTE: jedes Modul registriert seine Tabelle an Base.metadata.
# Ohne sie legt create_all() in der Testdatenbank nicht alle Tabellen an — am
# 2026-08-25 entfernte autoflake sie und test_register_success fiel mit
# 'no such table: settings' auf 500. Das noqa haelt sie fest.
from models.audit_log import AuditLog  # noqa: F401
from models.database import Base, get_db  # noqa: F401
from models.diary import DiaryEntry  # noqa: F401
from models.expense import Expense  # noqa: F401
from models.media import Media  # noqa: F401
from models.notification import Notification  # noqa: F401
from models.participant import Participant  # noqa: F401
from models.place import Place  # noqa: F401
from models.place_list import PlaceList  # noqa: F401
from models.route import Route  # noqa: F401
from models.settings import Settings  # noqa: F401

# Import all models to register them with Base.metadata
from models.trip import Trip  # noqa: F401
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from utils.rate_limits import limiter

# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override and disabled rate limiting"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Disable rate limiting for tests
    limiter.enabled = False

    # httpx 0.28 hat die Abkuerzung `AsyncClient(app=...)` entfernt; der
    # ASGI-Transport muss seither ausdruecklich uebergeben werden.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    limiter.enabled = True


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=User.hash_password("testpass123"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, test_user: User) -> str:
    """Get authentication token for test user"""
    response = await client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Get authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}


# ── Gemeinsame Fixtures ─────────────────────────────────────────────────────
#
# Bis 2026-08-25 baute jede Testdatei sich Reise, Zweitnutzer und deren Token
# selbst. Das ist nicht nur Doppelarbeit: jede Kopie kann anders sein, und ein
# Test, der eine Berechtigung prueft, haengt dann an einem Aufbau, ueber den er
# nichts aussagt. Vorhandene Dateien duerfen die Namen weiter lokal
# ueberschreiben — pytest laesst die naehere Definition gewinnen.


@pytest_asyncio.fixture
async def test_trip(db_session: AsyncSession, test_user: User):
    """Eine Reise, die dem test_user gehoert."""
    from datetime import datetime

    trip = Trip(
        title="Testreise nach Lissabon",
        destination="Lissabon",
        description="Zum Pruefen",
        latitude=38.7223,
        longitude=-9.1393,
        start_date=datetime(2026, 9, 1),
        end_date=datetime(2026, 9, 8),
        budget=1200.0,
        currency="EUR",
        interests=["culture", "food"],
        owner_id=test_user.id,
    )
    db_session.add(trip)
    await db_session.commit()
    await db_session.refresh(trip)
    return trip


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Ein zweiter, unbeteiligter Nutzer — fuer jede Zugriffspruefung noetig."""
    user = User(
        username="otheruser",
        email="other@example.com",
        hashed_password=User.hash_password("otherpass123"),
        full_name="Other User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_auth_headers(client: AsyncClient, other_user: User) -> dict:
    response = await client.post(
        "/api/auth/login",
        data={"username": "otheruser", "password": "otherpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=User.hash_password("adminpass123"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    response = await client.post(
        "/api/auth/login",
        data={"username": "adminuser", "password": "adminpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest_asyncio.fixture
async def test_place(db_session: AsyncSession, test_trip):
    """Ein Ort in der Testreise."""
    place = Place(
        name="Torre de Belém",
        description="Turm am Tejo",
        latitude=38.6916,
        longitude=-9.2160,
        category="sight",
        trip_id=test_trip.id,
    )
    db_session.add(place)
    await db_session.commit()
    await db_session.refresh(place)
    return place
