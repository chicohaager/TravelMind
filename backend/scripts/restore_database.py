#!/usr/bin/env python3
"""
Restore Script for TravelMind — companion to backup_database.py.

Restores the database and/or the uploads (photos) archive produced by
backup_database.py. Overwrites existing data, so it asks for confirmation
unless --yes is given.

Usage:
    # Restore both database and uploads
    python restore_database.py --database ./backups/travelmind_backup_20260623_120000.dump \
                               --uploads  ./backups/travelmind_uploads_20260623_120000.tar.gz

    # Restore only uploads, into a custom directory, without prompt
    python restore_database.py --uploads ./backups/...tar.gz --uploads-dir ./uploads --yes
"""

import os
import sys
import argparse
import shutil
import subprocess
import gzip
import tarfile
import logging
from pathlib import Path

# backup_database lives in the same directory; Python adds the script dir to sys.path.
from backup_database import parse_database_url, get_database_url

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def confirm(message: str, assume_yes: bool) -> bool:
    """Ask the user to confirm a destructive action (unless --yes)."""
    if assume_yes:
        return True
    print(message)
    return input("Type 'yes' to proceed: ").strip().lower() == "yes"


def restore_database(backup_file: Path, db_config: dict) -> None:
    """Restore the database from a backup file (SQLite copy/gunzip, or pg_restore)."""
    if db_config["type"] == "sqlite":
        db_path = Path(db_config["path"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if backup_file.suffix == ".gz":
            with gzip.open(backup_file, "rb") as f_in, open(db_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(backup_file, db_path)
        logger.info(f"Database restored to: {db_path}")
    else:
        cmd = [
            "pg_restore",
            "-h", db_config["host"],
            "-p", str(db_config["port"]),
            "-U", db_config["username"],
            "-d", db_config["database"],
            "-c",            # drop objects before recreating
            "--if-exists",   # avoid noisy errors when objects are absent
            str(backup_file),
        ]
        env = os.environ.copy()
        if db_config.get("password"):
            env["PGPASSWORD"] = db_config["password"]
        try:
            subprocess.run(cmd, env=env, check=True)
            logger.info(f"Database restored from: {backup_file}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"pg_restore failed: {e}")
        except FileNotFoundError:
            raise RuntimeError("pg_restore not found. Install PostgreSQL client tools.")


def restore_uploads(archive: Path, uploads_dir: str) -> None:
    """
    Extract an uploads archive into the parent of the uploads directory.

    The archive contains a single top-level folder (e.g. "uploads"); extracting
    into the parent recreates it. Existing files are overwritten.
    """
    target = Path(uploads_dir)
    parent = target.parent if target.parent != Path("") else Path(".")
    parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive, "r:gz") as tar:
        # filter="data" (Python 3.12+) blocks unsafe members (absolute paths, ..).
        tar.extractall(parent, filter="data")
    logger.info(f"Uploads restored into: {parent.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Restore a TravelMind backup (database and/or uploads)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--database", "-d", type=str, help="Database backup file to restore")
    parser.add_argument("--uploads", "-u", type=str, help="Uploads archive (.tar.gz) to restore")
    parser.add_argument(
        "--uploads-dir",
        type=str,
        default=os.getenv("UPLOAD_DIR", "./uploads"),
        help="Target uploads directory (default: $UPLOAD_DIR or ./uploads)",
    )
    parser.add_argument("--database-url", type=str, help="Override DATABASE_URL")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if not args.database and not args.uploads:
        parser.error("Provide --database and/or --uploads to restore.")

    db_config = parse_database_url(args.database_url or get_database_url())

    # Validate inputs up front
    db_file = Path(args.database) if args.database else None
    if db_file and not db_file.exists():
        logger.error(f"Database backup not found: {db_file}")
        sys.exit(1)
    uploads_file = Path(args.uploads) if args.uploads else None
    if uploads_file and not uploads_file.exists():
        logger.error(f"Uploads archive not found: {uploads_file}")
        sys.exit(1)

    # Confirm (destructive)
    lines = ["⚠️  This will OVERWRITE existing data:"]
    if db_file:
        target = db_config["path"] if db_config["type"] == "sqlite" else db_config["database"]
        lines.append(f"   • Database ({db_config['type']}): {target}")
    if uploads_file:
        lines.append(f"   • Uploads directory: {Path(args.uploads_dir).resolve()}")
    if not confirm("\n".join(lines), args.yes):
        print("Aborted.")
        sys.exit(0)

    try:
        if db_file:
            restore_database(db_file, db_config)
        if uploads_file:
            restore_uploads(uploads_file, args.uploads_dir)
        print("\n✅ Restore successful!")
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
