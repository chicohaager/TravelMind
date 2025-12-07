"""
Database configuration and session management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment (PostgreSQL only)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://travelmind:travelmind@localhost:5432/travelmind")

# Convert database URL for async support
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine for PostgreSQL
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
    PostgreSQL only.
    """
    from sqlalchemy import text

    try:
        # Check users table columns
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users'
        """))
        user_columns = [row[0] for row in result.fetchall()]

        if 'ai_provider' not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN ai_provider VARCHAR(10)"))
            print("  ✓ Added ai_provider column to users table")

        if 'encrypted_api_key' not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN encrypted_api_key TEXT"))
            print("  ✓ Added encrypted_api_key column to users table")

        if 'encryption_salt' not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN encryption_salt VARCHAR(32)"))
            print("  ✓ Added encryption_salt column to users table")

        # Check places table columns
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='places'
        """))
        place_columns = [row[0] for row in result.fetchall()]

        migrations = [
            ('color', "ALTER TABLE places ADD COLUMN color VARCHAR(7) DEFAULT '#6366F1'"),
            ('icon_type', "ALTER TABLE places ADD COLUMN icon_type VARCHAR(50) DEFAULT 'location'"),
            ('image_url', "ALTER TABLE places ADD COLUMN image_url VARCHAR(1000)"),
            ('tags', "ALTER TABLE places ADD COLUMN tags JSON"),
            ('external_links', "ALTER TABLE places ADD COLUMN external_links JSON"),
            ('google_place_id', "ALTER TABLE places ADD COLUMN google_place_id VARCHAR(200)"),
            ('external_rating', "ALTER TABLE places ADD COLUMN external_rating FLOAT"),
            ('review_count', "ALTER TABLE places ADD COLUMN review_count INTEGER"),
            ('list_id', "ALTER TABLE places ADD COLUMN list_id INTEGER REFERENCES place_lists(id) ON DELETE SET NULL"),
        ]

        for column, sql in migrations:
            if column not in place_columns:
                await conn.execute(text(sql))
                print(f"  ✓ Added {column} column to places table")

    except Exception as e:
        print(f"  ⚠️  Migration warning: {e}")


async def init_default_settings(conn):
    """
    Initialize default application settings (PostgreSQL only)
    """
    from sqlalchemy import text

    try:
        # Check if settings table exists
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
        from models import audit_log  # Audit logging

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
