#!/usr/bin/env python3
"""
Database Backup Script for TravelMind

Supports both SQLite and PostgreSQL databases.
Can be run manually or scheduled via cron.

Usage:
    python backup_database.py                    # Backup with defaults
    python backup_database.py --output /backups  # Custom output directory
    python backup_database.py --keep 30          # Keep last 30 backups
    python backup_database.py --compress         # Compress with gzip
"""

import os
import sys
import argparse
import shutil
import subprocess
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        "sqlite:///./data/travelmind.db"
    )


def parse_database_url(url: str) -> dict:
    """Parse database URL into components."""
    if url.startswith("sqlite"):
        # SQLite: sqlite:///./data/travelmind.db
        path = url.replace("sqlite:///", "").replace("sqlite://", "")
        return {
            "type": "sqlite",
            "path": path
        }
    else:
        # PostgreSQL: postgresql://user:pass@host:port/dbname
        parsed = urlparse(url)
        return {
            "type": "postgresql",
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip("/"),
            "username": parsed.username,
            "password": parsed.password
        }


def backup_sqlite(db_path: str, output_dir: Path, compress: bool = False) -> Path:
    """
    Backup SQLite database.

    Uses file copy with SQLite backup API for consistency.
    """
    db_file = Path(db_path)

    if not db_file.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"travelmind_backup_{timestamp}.db"
    backup_path = output_dir / backup_name

    logger.info(f"Backing up SQLite database: {db_path}")

    # Use sqlite3 to create a consistent backup
    try:
        import sqlite3

        # Connect to source database
        source = sqlite3.connect(db_path)

        # Create backup
        backup = sqlite3.connect(str(backup_path))
        source.backup(backup)

        backup.close()
        source.close()

        logger.info(f"SQLite backup created: {backup_path}")

    except ImportError:
        # Fallback to file copy if sqlite3 not available
        logger.warning("sqlite3 module not available, using file copy")
        shutil.copy2(db_path, backup_path)

    # Compress if requested
    if compress:
        compressed_path = backup_path.with_suffix(".db.gz")
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        backup_path.unlink()
        backup_path = compressed_path
        logger.info(f"Compressed backup: {backup_path}")

    return backup_path


def backup_postgresql(config: dict, output_dir: Path, compress: bool = False) -> Path:
    """
    Backup PostgreSQL database using pg_dump.

    Requires pg_dump to be installed on the system.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"travelmind_backup_{timestamp}.sql"
    backup_path = output_dir / backup_name

    logger.info(f"Backing up PostgreSQL database: {config['database']}")

    # Build pg_dump command
    cmd = [
        "pg_dump",
        "-h", config["host"],
        "-p", str(config["port"]),
        "-U", config["username"],
        "-d", config["database"],
        "-F", "c",  # Custom format (compressed)
        "-f", str(backup_path.with_suffix(".dump"))
    ]

    # Set password via environment
    env = os.environ.copy()
    if config.get("password"):
        env["PGPASSWORD"] = config["password"]

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        backup_path = backup_path.with_suffix(".dump")
        logger.info(f"PostgreSQL backup created: {backup_path}")

    except subprocess.CalledProcessError as e:
        logger.error(f"pg_dump failed: {e.stderr}")
        raise RuntimeError(f"PostgreSQL backup failed: {e.stderr}")
    except FileNotFoundError:
        logger.error("pg_dump not found. Please install PostgreSQL client tools.")
        raise RuntimeError("pg_dump not found")

    # Additional compression for custom format backups
    if compress:
        compressed_path = backup_path.with_suffix(".dump.gz")
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        backup_path.unlink()
        backup_path = compressed_path
        logger.info(f"Compressed backup: {backup_path}")

    return backup_path


def cleanup_old_backups(output_dir: Path, keep: int = 7) -> int:
    """
    Remove old backups, keeping only the most recent ones.

    Returns the number of backups removed.
    """
    # Find all backup files
    patterns = ["travelmind_backup_*.db", "travelmind_backup_*.db.gz",
                "travelmind_backup_*.dump", "travelmind_backup_*.dump.gz",
                "travelmind_backup_*.sql", "travelmind_backup_*.sql.gz"]

    backup_files = []
    for pattern in patterns:
        backup_files.extend(output_dir.glob(pattern))

    # Sort by modification time (newest first)
    backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    # Remove old backups
    removed = 0
    for backup_file in backup_files[keep:]:
        logger.info(f"Removing old backup: {backup_file}")
        backup_file.unlink()
        removed += 1

    return removed


def get_backup_info(output_dir: Path) -> list:
    """Get information about existing backups."""
    patterns = ["travelmind_backup_*.db", "travelmind_backup_*.db.gz",
                "travelmind_backup_*.dump", "travelmind_backup_*.dump.gz",
                "travelmind_backup_*.sql", "travelmind_backup_*.sql.gz"]

    backup_files = []
    for pattern in patterns:
        backup_files.extend(output_dir.glob(pattern))

    backups = []
    for f in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True):
        stat = f.stat()
        backups.append({
            "name": f.name,
            "size": stat.st_size,
            "size_human": format_size(stat.st_size),
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "path": str(f)
        })

    return backups


def format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def main():
    parser = argparse.ArgumentParser(
        description="Backup TravelMind database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create a backup with default settings
    python backup_database.py

    # Create compressed backup in custom directory
    python backup_database.py --output /var/backups/travelmind --compress

    # Keep only last 14 backups
    python backup_database.py --keep 14

    # List existing backups
    python backup_database.py --list

    # Restore from backup (SQLite)
    python backup_database.py --restore /path/to/backup.db
        """
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./backups",
        help="Output directory for backups (default: ./backups)"
    )

    parser.add_argument(
        "--keep", "-k",
        type=int,
        default=7,
        help="Number of backups to keep (default: 7)"
    )

    parser.add_argument(
        "--compress", "-c",
        action="store_true",
        help="Compress backup with gzip"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List existing backups"
    )

    parser.add_argument(
        "--restore", "-r",
        type=str,
        help="Restore from backup file"
    )

    parser.add_argument(
        "--database-url",
        type=str,
        help="Override DATABASE_URL environment variable"
    )

    args = parser.parse_args()

    # Get database configuration
    db_url = args.database_url or get_database_url()
    db_config = parse_database_url(db_url)

    # Setup output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # List backups
    if args.list:
        backups = get_backup_info(output_dir)
        if not backups:
            print("No backups found.")
        else:
            print(f"\nExisting backups in {output_dir}:\n")
            print(f"{'Name':<50} {'Size':<12} {'Created'}")
            print("-" * 80)
            for b in backups:
                print(f"{b['name']:<50} {b['size_human']:<12} {b['created']}")
            print(f"\nTotal: {len(backups)} backup(s)")
        return

    # Restore from backup
    if args.restore:
        restore_path = Path(args.restore)
        if not restore_path.exists():
            logger.error(f"Backup file not found: {restore_path}")
            sys.exit(1)

        if db_config["type"] == "sqlite":
            # For SQLite, just copy the file
            db_path = Path(db_config["path"])

            # Handle compressed backups
            if restore_path.suffix == ".gz":
                with gzip.open(restore_path, 'rb') as f_in:
                    with open(db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(restore_path, db_path)

            logger.info(f"Database restored from: {restore_path}")
        else:
            # For PostgreSQL, use pg_restore
            cmd = [
                "pg_restore",
                "-h", db_config["host"],
                "-p", str(db_config["port"]),
                "-U", db_config["username"],
                "-d", db_config["database"],
                "-c",  # Clean (drop) database objects before recreating
                str(restore_path)
            ]

            env = os.environ.copy()
            if db_config.get("password"):
                env["PGPASSWORD"] = db_config["password"]

            try:
                subprocess.run(cmd, env=env, check=True)
                logger.info(f"Database restored from: {restore_path}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Restore failed: {e}")
                sys.exit(1)

        return

    # Create backup
    try:
        if db_config["type"] == "sqlite":
            backup_path = backup_sqlite(
                db_config["path"],
                output_dir,
                compress=args.compress
            )
        else:
            backup_path = backup_postgresql(
                db_config,
                output_dir,
                compress=args.compress
            )

        # Get backup size
        size = backup_path.stat().st_size
        logger.info(f"Backup complete: {backup_path} ({format_size(size)})")

        # Cleanup old backups
        removed = cleanup_old_backups(output_dir, keep=args.keep)
        if removed > 0:
            logger.info(f"Removed {removed} old backup(s)")

        print(f"\n✅ Backup successful!")
        print(f"   File: {backup_path}")
        print(f"   Size: {format_size(size)}")

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
