"""
Pytest configuration and fixtures for TravelMind tests
"""

import sys
from pathlib import Path

# Add parent directory to Python path so we can import from backend
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
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

    async with AsyncClient(app=app, base_url="http://test") as ac:
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
