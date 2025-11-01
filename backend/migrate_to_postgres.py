#!/usr/bin/env python3
"""
Migration script to copy data from SQLite to PostgreSQL
"""

import asyncio
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime
import sys

# Database URLs
SQLITE_URL = "sqlite:///./data/travelmind.db"
POSTGRES_URL = "postgresql+asyncpg://travelmind:travelmind@db:5432/travelmind"

async def migrate():
    """Migrate data from SQLite to PostgreSQL"""

    print("🔄 Starting migration from SQLite to PostgreSQL...")

    # Connect to SQLite (sync)
    sqlite_conn = sqlite3.connect("./data/travelmind.db")
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # Connect to PostgreSQL (async)
    pg_engine = create_async_engine(POSTGRES_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        try:
            # Migrate Users
            print("\n📊 Migrating users...")
            users = sqlite_cursor.execute("SELECT * FROM users").fetchall()
            print(f"   Found {len(users)} users")

            for user in users:
                # Convert datetime strings to datetime objects
                created_at = datetime.fromisoformat(user["created_at"]) if user["created_at"] else None
                updated_at = datetime.fromisoformat(user["updated_at"]) if user["updated_at"] else None

                await session.execute(
                    text("""
                        INSERT INTO users (id, username, email, hashed_password, created_at, updated_at)
                        VALUES (:id, :username, :email, :hashed_password, :created_at, :updated_at)
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": user["id"],
                        "username": user["username"],
                        "email": user["email"],
                        "hashed_password": user["hashed_password"],
                        "created_at": created_at,
                        "updated_at": updated_at
                    }
                )
            await session.commit()
            print(f"   ✅ Migrated {len(users)} users")

            # Migrate User Settings
            print("\n📊 Migrating user settings...")
            try:
                settings = sqlite_cursor.execute("SELECT * FROM user_settings").fetchall()
                print(f"   Found {len(settings)} settings")

                for setting in settings:
                    created_at = datetime.fromisoformat(setting["created_at"]) if setting["created_at"] else None
                    updated_at = datetime.fromisoformat(setting["updated_at"]) if setting["updated_at"] else None

                    await session.execute(
                        text("""
                            INSERT INTO user_settings (id, user_id, ai_provider, encrypted_api_key, created_at, updated_at)
                            VALUES (:id, :user_id, :ai_provider, :encrypted_api_key, :created_at, :updated_at)
                            ON CONFLICT (id) DO NOTHING
                        """),
                        {
                            "id": setting["id"],
                            "user_id": setting["user_id"],
                            "ai_provider": setting["ai_provider"],
                            "encrypted_api_key": setting["encrypted_api_key"],
                            "created_at": created_at,
                            "updated_at": updated_at
                        }
                    )
                await session.commit()
                print(f"   ✅ Migrated {len(settings)} settings")
            except sqlite3.OperationalError:
                print("   ⚠️  No user_settings table found (skipping)")

            # Migrate Trips
            print("\n📊 Migrating trips...")
            trips = sqlite_cursor.execute("SELECT * FROM trips").fetchall()
            print(f"   Found {len(trips)} trips")

            for trip in trips:
                start_date = datetime.fromisoformat(trip["start_date"]) if trip["start_date"] else None
                end_date = datetime.fromisoformat(trip["end_date"]) if trip["end_date"] else None
                created_at = datetime.fromisoformat(trip["created_at"]) if trip["created_at"] else None
                updated_at = datetime.fromisoformat(trip["updated_at"]) if trip["updated_at"] else None

                await session.execute(
                    text("""
                        INSERT INTO trips (id, owner_id, title, destination, description, start_date, end_date,
                                         latitude, longitude, interests, budget, currency, cover_image, created_at, updated_at)
                        VALUES (:id, :owner_id, :title, :destination, :description, :start_date, :end_date,
                                :latitude, :longitude, :interests, :budget, :currency, :cover_image, :created_at, :updated_at)
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": trip["id"],
                        "owner_id": trip["owner_id"],
                        "title": trip["title"],
                        "destination": trip["destination"],
                        "description": trip["description"],
                        "start_date": start_date,
                        "end_date": end_date,
                        "latitude": trip["latitude"],
                        "longitude": trip["longitude"],
                        "interests": trip["interests"],
                        "budget": trip["budget"],
                        "currency": trip["currency"],
                        "cover_image": trip["cover_image"] if "cover_image" in trip.keys() else None,
                        "created_at": created_at,
                        "updated_at": updated_at
                    }
                )
            await session.commit()
            print(f"   ✅ Migrated {len(trips)} trips")

            # Migrate Diary Entries
            print("\n📊 Migrating diary entries...")
            try:
                entries = sqlite_cursor.execute("SELECT * FROM diary_entries").fetchall()
                print(f"   Found {len(entries)} diary entries")

                for entry in entries:
                    await session.execute(
                        text("""
                            INSERT INTO diary_entries (id, trip_id, title, content, entry_date, location_name,
                                                      latitude, longitude, mood, weather, rating, photos, tags,
                                                      created_at, updated_at)
                            VALUES (:id, :trip_id, :title, :content, :entry_date, :location_name,
                                    :latitude, :longitude, :mood, :weather, :rating, :photos, :tags,
                                    :created_at, :updated_at)
                            ON CONFLICT (id) DO NOTHING
                        """),
                        {
                            "id": entry["id"],
                            "trip_id": entry["trip_id"],
                            "title": entry["title"],
                            "content": entry["content"],
                            "entry_date": entry["entry_date"],
                            "location_name": entry["location_name"],
                            "latitude": entry["latitude"],
                            "longitude": entry["longitude"],
                            "mood": entry["mood"],
                            "weather": entry["weather"],
                            "rating": entry["rating"],
                            "photos": entry["photos"],
                            "tags": entry["tags"],
                            "created_at": entry["created_at"],
                            "updated_at": entry["updated_at"]
                        }
                    )
                await session.commit()
                print(f"   ✅ Migrated {len(entries)} diary entries")
            except sqlite3.OperationalError:
                print("   ⚠️  No diary_entries table found (skipping)")

            # Migrate Places
            print("\n📊 Migrating places...")
            try:
                places = sqlite_cursor.execute("SELECT * FROM places").fetchall()
                print(f"   Found {len(places)} places")

                for place in places:
                    await session.execute(
                        text("""
                            INSERT INTO places (id, trip_id, name, description, address, latitude, longitude,
                                              category, visit_date, visited, website, phone, cost, currency,
                                              rating, notes, photos, created_at, updated_at)
                            VALUES (:id, :trip_id, :name, :description, :address, :latitude, :longitude,
                                    :category, :visit_date, :visited, :website, :phone, :cost, :currency,
                                    :rating, :notes, :photos, :created_at, :updated_at)
                            ON CONFLICT (id) DO NOTHING
                        """),
                        {
                            "id": place["id"],
                            "trip_id": place["trip_id"],
                            "name": place["name"],
                            "description": place["description"],
                            "address": place["address"],
                            "latitude": place["latitude"],
                            "longitude": place["longitude"],
                            "category": place["category"],
                            "visit_date": place["visit_date"],
                            "visited": place["visited"],
                            "website": place["website"],
                            "phone": place["phone"],
                            "cost": place["cost"],
                            "currency": place["currency"],
                            "rating": place["rating"],
                            "notes": place["notes"],
                            "photos": place["photos"],
                            "created_at": place["created_at"],
                            "updated_at": place["updated_at"]
                        }
                    )
                await session.commit()
                print(f"   ✅ Migrated {len(places)} places")
            except sqlite3.OperationalError:
                print("   ⚠️  No places table found (skipping)")

            # Migrate Expenses
            print("\n📊 Migrating expenses...")
            try:
                expenses = sqlite_cursor.execute("SELECT * FROM expenses").fetchall()
                print(f"   Found {len(expenses)} expenses")

                for expense in expenses:
                    await session.execute(
                        text("""
                            INSERT INTO expenses (id, trip_id, title, amount, currency, category, date,
                                                description, created_at, updated_at)
                            VALUES (:id, :trip_id, :title, :amount, :currency, :category, :date,
                                    :description, :created_at, :updated_at)
                            ON CONFLICT (id) DO NOTHING
                        """),
                        {
                            "id": expense["id"],
                            "trip_id": expense["trip_id"],
                            "title": expense["title"],
                            "amount": expense["amount"],
                            "currency": expense["currency"],
                            "category": expense["category"],
                            "date": expense["date"],
                            "description": expense["description"],
                            "created_at": expense["created_at"],
                            "updated_at": expense["updated_at"]
                        }
                    )
                await session.commit()
                print(f"   ✅ Migrated {len(expenses)} expenses")
            except sqlite3.OperationalError:
                print("   ⚠️  No expenses table found (skipping)")

            print("\n✅ Migration completed successfully!")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            await session.rollback()
            raise
        finally:
            sqlite_conn.close()
            await pg_engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
