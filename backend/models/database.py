"""
Database configuration and session management
"""

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

# Get database URL from environment (PostgreSQL only)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://travelmind:travelmind@localhost:5432/travelmind")

# Convert database URL for async support
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine for PostgreSQL
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=10, max_overflow=20)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
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

        if "ai_provider" not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN ai_provider VARCHAR(10)"))
            print("  ✓ Added ai_provider column to users table")

        if "encrypted_api_key" not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN encrypted_api_key TEXT"))
            print("  ✓ Added encrypted_api_key column to users table")

        if "encryption_salt" not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN encryption_salt VARCHAR(32)"))
            print("  ✓ Added encryption_salt column to users table")

        if "password_changed_at" not in user_columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN password_changed_at TIMESTAMP WITH TIME ZONE"))
            print("  ✓ Added password_changed_at column to users table")

        # Check participants table columns (trip sharing / permissions)
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='participants'
        """))
        participant_columns = [row[0] for row in result.fetchall()]

        participant_migrations = [
            ("user_id", "ALTER TABLE participants ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"),
            ("permission", "ALTER TABLE participants ADD COLUMN permission VARCHAR(20) DEFAULT 'viewer'"),
            (
                "invitation_status",
                "ALTER TABLE participants ADD COLUMN invitation_status VARCHAR(20) DEFAULT 'pending'",
            ),
            ("invited_at", "ALTER TABLE participants ADD COLUMN invited_at TIMESTAMP WITH TIME ZONE DEFAULT now()"),
            ("accepted_at", "ALTER TABLE participants ADD COLUMN accepted_at TIMESTAMP WITH TIME ZONE"),
        ]

        for column, sql in participant_migrations:
            if column not in participant_columns:
                await conn.execute(text(sql))
                print(f"  ✓ Added {column} column to participants table")

        # Check places table columns
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='places'
        """))
        place_columns = [row[0] for row in result.fetchall()]

        migrations = [
            ("color", "ALTER TABLE places ADD COLUMN color VARCHAR(7) DEFAULT '#6366F1'"),
            ("icon_type", "ALTER TABLE places ADD COLUMN icon_type VARCHAR(50) DEFAULT 'location'"),
            ("image_url", "ALTER TABLE places ADD COLUMN image_url VARCHAR(1000)"),
            ("tags", "ALTER TABLE places ADD COLUMN tags JSON"),
            ("external_links", "ALTER TABLE places ADD COLUMN external_links JSON"),
            ("google_place_id", "ALTER TABLE places ADD COLUMN google_place_id VARCHAR(200)"),
            ("external_rating", "ALTER TABLE places ADD COLUMN external_rating FLOAT"),
            ("review_count", "ALTER TABLE places ADD COLUMN review_count INTEGER"),
            ("list_id", "ALTER TABLE places ADD COLUMN list_id INTEGER REFERENCES place_lists(id) ON DELETE SET NULL"),
        ]

        for column, sql in migrations:
            if column not in place_columns:
                await conn.execute(text(sql))
                print(f"  ✓ Added {column} column to places table")

        # Check trips table columns (public read-only sharing — see migration 0004)
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='trips'
        """))
        trip_columns = [row[0] for row in result.fetchall()]

        trip_migrations = [
            ("is_public", "ALTER TABLE trips ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT false"),
            ("share_token", "ALTER TABLE trips ADD COLUMN share_token VARCHAR(64)"),
        ]

        for column, sql in trip_migrations:
            if column not in trip_columns:
                await conn.execute(text(sql))
                print(f"  ✓ Added {column} column to trips table")

        # Unique index backing share-link lookups (idempotent)
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_trips_share_token ON trips (share_token)"))

    except Exception as e:
        print(f"  ⚠️  Migration warning: {e}")


async def backfill_media(conn):
    """
    Backfill the `media` table from legacy `photos` JSON arrays (PostgreSQL only).

    Idempotent: only inserts rows for a diary entry / place that has photos but no
    media rows yet, so it is safe to run on every startup. Legacy rows carry no
    EXIF metadata (the originals were not processed); thumbnails are derived from
    the WebP naming convention where possible.
    """
    from sqlalchemy import text

    # Derive the thumbnail URL from the WebP naming convention used by utils.images.
    thumb_expr = (
        "CASE WHEN elem.value LIKE '%.webp' "
        "THEN regexp_replace(elem.value, '\\.webp$', '_thumb.webp') "
        "ELSE elem.value END"
    )

    try:
        await conn.execute(text(f"""
            INSERT INTO media (owner_id, trip_id, diary_entry_id, url, thumb_url, order_index, created_at)
            SELECT d.author_id, d.trip_id, d.id, elem.value, {thumb_expr}, (elem.ord - 1)::int, now()
            FROM diary_entries d
            CROSS JOIN LATERAL jsonb_array_elements_text(d.photos::jsonb)
                 WITH ORDINALITY AS elem(value, ord)
            WHERE d.photos IS NOT NULL
              AND jsonb_typeof(d.photos::jsonb) = 'array'
              AND jsonb_array_length(d.photos::jsonb) > 0
              AND NOT EXISTS (SELECT 1 FROM media m WHERE m.diary_entry_id = d.id)
        """))

        await conn.execute(text(f"""
            INSERT INTO media (owner_id, trip_id, place_id, url, thumb_url, order_index, created_at)
            SELECT t.owner_id, p.trip_id, p.id, elem.value, {thumb_expr}, (elem.ord - 1)::int, now()
            FROM places p
            JOIN trips t ON t.id = p.trip_id
            CROSS JOIN LATERAL jsonb_array_elements_text(p.photos::jsonb)
                 WITH ORDINALITY AS elem(value, ord)
            WHERE p.photos IS NOT NULL
              AND jsonb_typeof(p.photos::jsonb) = 'array'
              AND jsonb_array_length(p.photos::jsonb) > 0
              AND NOT EXISTS (SELECT 1 FROM media m WHERE m.place_id = p.id)
        """))
        print("  ✓ Backfilled media table from legacy photos arrays")
    except Exception as e:
        print(f"  ⚠️  Media backfill warning: {e}")


async def create_search_indexes(conn):
    """
    Create GIN full-text indexes (PostgreSQL only).

    Uses the same document expressions as the search queries (routes.search)
    so the planner can use the indexes. Idempotent via IF NOT EXISTS.
    """
    from routes.search import PG_DOCS
    from sqlalchemy import text

    tables = {"trip": "trips", "diary": "diary_entries", "place": "places", "media": "media"}
    try:
        for kind, table in tables.items():
            await conn.execute(
                text(f"CREATE INDEX IF NOT EXISTS ix_{table}_fts ON {table} USING GIN ({PG_DOCS[kind]})")
            )
        print("  ✓ Search (GIN full-text) indexes ensured")
    except Exception as e:
        print(f"  ⚠️  Search index creation warning: {e}")


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
        # Serialize concurrent initializers (e.g. multiple gunicorn workers each
        # running the lifespan) so the idempotent setup below doesn't race on
        # CREATE TYPE/TABLE — Postgres ENUM creation isn't concurrency-safe. The
        # transaction-level advisory lock auto-releases on commit. Postgres only.
        if conn.dialect.name == "postgresql":
            from sqlalchemy import text

            await conn.execute(text("SELECT pg_advisory_xact_lock(727274)"))

        # Import all models here to ensure they're registered
        from models import audit_log  # Audit logging
        from models import media  # Photo/video media
        from models import notification  # In-app notifications
        from models import diary, expense, participant, place, place_list, route, settings, trip, user

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Run migrations for existing tables
        await run_migrations(conn)

        # Backfill media rows from legacy photos arrays
        await backfill_media(conn)

        # Create full-text search indexes (PostgreSQL only)
        await create_search_indexes(conn)

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
