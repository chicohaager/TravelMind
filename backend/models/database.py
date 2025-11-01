"""
Database configuration and session management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/travelmind.db")

# Convert database URLs for async support
if DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
if "sqlite" in DATABASE_URL:
    # SQLite specific settings
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=NullPool,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL settings
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency for getting database sessions
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def run_migrations(conn):
    """
    Run manual migrations for schema changes that can't be done by create_all
    """
    from sqlalchemy import text

    try:
        # Check if ai_provider and encrypted_api_key columns exist
        if "sqlite" in DATABASE_URL:
            # SQLite specific migration
            result = await conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]

            if 'ai_provider' not in columns:
                await conn.execute(text("ALTER TABLE users ADD COLUMN ai_provider VARCHAR(10)"))
                print("  ✓ Added ai_provider column to users table")

            if 'encrypted_api_key' not in columns:
                await conn.execute(text("ALTER TABLE users ADD COLUMN encrypted_api_key TEXT"))
                print("  ✓ Added encrypted_api_key column to users table")
        else:
            # PostgreSQL specific migration
            result = await conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='users'
            """))
            columns = [row[0] for row in result.fetchall()]

            if 'ai_provider' not in columns:
                await conn.execute(text("ALTER TABLE users ADD COLUMN ai_provider VARCHAR(10)"))
                print("  ✓ Added ai_provider column to users table")

            if 'encrypted_api_key' not in columns:
                await conn.execute(text("ALTER TABLE users ADD COLUMN encrypted_api_key TEXT"))
                print("  ✓ Added encrypted_api_key column to users table")

        # Add all missing columns to places table
        if "sqlite" in DATABASE_URL:
            result = await conn.execute(text("PRAGMA table_info(places)"))
            columns = [row[1] for row in result.fetchall()]

            if 'color' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN color VARCHAR(7) DEFAULT '#6366F1'"))
                print("  ✓ Added color column to places table")

            if 'icon_type' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN icon_type VARCHAR(50) DEFAULT 'location'"))
                print("  ✓ Added icon_type column to places table")

            if 'image_url' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN image_url VARCHAR(1000)"))
                print("  ✓ Added image_url column to places table")

            if 'tags' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN tags JSON"))
                print("  ✓ Added tags column to places table")

            if 'external_links' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN external_links JSON"))
                print("  ✓ Added external_links column to places table")

            if 'google_place_id' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN google_place_id VARCHAR(200)"))
                print("  ✓ Added google_place_id column to places table")

            if 'external_rating' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN external_rating FLOAT"))
                print("  ✓ Added external_rating column to places table")

            if 'review_count' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN review_count INTEGER"))
                print("  ✓ Added review_count column to places table")

            if 'list_id' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN list_id INTEGER REFERENCES place_lists(id) ON DELETE SET NULL"))
                print("  ✓ Added list_id column to places table")
        else:
            result = await conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='places'
            """))
            columns = [row[0] for row in result.fetchall()]

            if 'color' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN color VARCHAR(7) DEFAULT '#6366F1'"))
                print("  ✓ Added color column to places table")

            if 'icon_type' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN icon_type VARCHAR(50) DEFAULT 'location'"))
                print("  ✓ Added icon_type column to places table")

            if 'image_url' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN image_url VARCHAR(1000)"))
                print("  ✓ Added image_url column to places table")

            if 'tags' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN tags JSON"))
                print("  ✓ Added tags column to places table")

            if 'external_links' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN external_links JSON"))
                print("  ✓ Added external_links column to places table")

            if 'google_place_id' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN google_place_id VARCHAR(200)"))
                print("  ✓ Added google_place_id column to places table")

            if 'external_rating' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN external_rating FLOAT"))
                print("  ✓ Added external_rating column to places table")

            if 'review_count' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN review_count INTEGER"))
                print("  ✓ Added review_count column to places table")

            if 'list_id' not in columns:
                await conn.execute(text("ALTER TABLE places ADD COLUMN list_id INTEGER REFERENCES place_lists(id) ON DELETE SET NULL"))
                print("  ✓ Added list_id column to places table")

        # Add encryption_salt to users table
        if "sqlite" in DATABASE_URL:
            result = await conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]

            if 'encryption_salt' not in columns:
                await conn.execute(text("ALTER TABLE users ADD COLUMN encryption_salt VARCHAR(32)"))
                print("  ✓ Added encryption_salt column to users table")
        else:
            result = await conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='users'
            """))
            columns = [row[0] for row in result.fetchall()]

            if 'encryption_salt' not in columns:
                await conn.execute(text("ALTER TABLE users ADD COLUMN encryption_salt VARCHAR(32)"))
                print("  ✓ Added encryption_salt column to users table")

    except Exception as e:
        print(f"  ⚠️  Migration warning: {e}")


async def init_default_settings(conn):
    """
    Initialize default application settings
    """
    from sqlalchemy import text
    from models.settings import Settings

    try:
        # Check if settings table exists and has data
        if "sqlite" in DATABASE_URL:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"))
            table_exists = result.fetchone() is not None
        else:
            result = await conn.execute(text("SELECT to_regclass('settings')"))
            table_exists = result.scalar() is not None

        if table_exists:
            # Check if registration_open setting exists
            result = await conn.execute(text("SELECT COUNT(*) FROM settings WHERE key = 'registration_open'"))
            count = result.scalar()

            if count == 0:
                # Insert default settings
                await conn.execute(text("""
                    INSERT INTO settings (key, value, value_type, description)
                    VALUES
                    ('registration_open', 'true', 'boolean', 'Allow new user registrations'),
                    ('app_name', 'TravelMind', 'string', 'Application name'),
                    ('max_users', '100', 'integer', 'Maximum number of users (0 = unlimited)')
                """))
                print("  ✓ Initialized default settings")
    except Exception as e:
        print(f"  ⚠️  Settings initialization warning: {e}")


async def init_db():
    """
    Initialize database tables
    """
    async with engine.begin() as conn:
        # Import all models here to ensure they're registered
        from models import user, trip, diary, place, place_list, expense, participant, route, settings

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Run migrations for existing tables
        await run_migrations(conn)

        # Initialize default settings
        await init_default_settings(conn)

    print("✅ Database initialized")


async def drop_db():
    """
    Drop all database tables (use with caution!)
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    print("⚠️  Database dropped")
