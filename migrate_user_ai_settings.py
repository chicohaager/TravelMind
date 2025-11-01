#!/usr/bin/env python3
"""
Migration script to add AI settings columns to users table
Run this script AFTER stopping the backend server
"""

import sqlite3
import sys

def migrate():
    db_path = "data/travelmind.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        migrations_needed = []

        if 'ai_provider' not in columns:
            migrations_needed.append("ai_provider")

        if 'encrypted_api_key' not in columns:
            migrations_needed.append("encrypted_api_key")

        if not migrations_needed:
            print("✅ Database is already up to date!")
            return True

        print(f"🔧 Adding columns: {', '.join(migrations_needed)}")

        # Add columns
        if 'ai_provider' in migrations_needed:
            cursor.execute("ALTER TABLE users ADD COLUMN ai_provider VARCHAR(10);")
            print("  ✓ Added ai_provider column")

        if 'encrypted_api_key' in migrations_needed:
            cursor.execute("ALTER TABLE users ADD COLUMN encrypted_api_key TEXT;")
            print("  ✓ Added encrypted_api_key column")

        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("You can now start the backend server.")
        return True

    except sqlite3.OperationalError as e:
        if "readonly database" in str(e) or "database is locked" in str(e):
            print("❌ Error: Database is locked!")
            print("\nPlease follow these steps:")
            print("1. Stop the backend server")
            print("2. Run this migration script again")
            print("3. Start the backend server")
            return False
        else:
            print(f"❌ Database error: {e}")
            return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("TravelMind Database Migration")
    print("Adding AI settings columns to users table")
    print("=" * 60)
    print()

    success = migrate()
    sys.exit(0 if success else 1)
