#!/bin/bash
#
# TravelMind Database Backup Script
#
# Usage:
#   ./backup.sh                 # Create backup
#   ./backup.sh --list          # List backups
#   ./backup.sh --restore FILE  # Restore from backup
#
# Schedule with cron (daily at 2 AM):
#   0 2 * * * /path/to/TravelMind/backend/scripts/backup.sh >> /var/log/travelmind-backup.log 2>&1
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$BACKEND_DIR")"

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Default settings
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
KEEP_BACKUPS="${KEEP_BACKUPS:-7}"
COMPRESS="${COMPRESS:-true}"

# Activate virtual environment if exists
if [ -f "$BACKEND_DIR/venv/bin/activate" ]; then
    source "$BACKEND_DIR/venv/bin/activate"
fi

# Build command
CMD="python $SCRIPT_DIR/backup_database.py --output $BACKUP_DIR --keep $KEEP_BACKUPS"

if [ "$COMPRESS" = "true" ]; then
    CMD="$CMD --compress"
fi

# Pass through any arguments
CMD="$CMD $@"

# Run backup
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting backup..."
$CMD
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup complete."
