# 💾 Backup & Restore

TravelMind has **two** pieces of irreplaceable data. Back up **both** — the
database alone is not enough, because it only references your photos by path.

| What | Where | Why it matters |
|------|-------|----------------|
| **Database** | PostgreSQL (or SQLite in dev) | Trips, diary entries, places, captions, GPS, users |
| **Uploads** | `backend/uploads/` (photos) | The actual images — **cannot be regenerated** |

Two scripts handle both:

- `backend/scripts/backup_database.py` — creates a database dump **and** a
  `tar.gz` of the uploads directory (matching timestamps).
- `backend/scripts/restore_database.py` — restores the database and/or uploads.

> PostgreSQL backups need the client tools (`pg_dump` / `pg_restore`) on `PATH`.

---

## Create a backup

Run from the `backend/` directory:

```bash
# Database + uploads, keep the 14 most recent of each
python scripts/backup_database.py --output /var/backups/travelmind --keep 14

# Skip the photos (database only)
python scripts/backup_database.py --skip-uploads

# Point at a custom uploads directory
python scripts/backup_database.py --uploads-dir /data/uploads
```

The database connection comes from `DATABASE_URL` (override with `--database-url`).
This produces a matching pair, e.g.:

```
travelmind_backup_20260623_120000.dump      # PostgreSQL (or .db for SQLite)
travelmind_uploads_20260623_120000.tar.gz   # photos
```

List existing backups:

```bash
python scripts/backup_database.py --output /var/backups/travelmind --list
```

`--keep N` prunes old backups, retaining the N most recent of **each** type
(every database dump keeps its matching uploads archive).

---

## Restore a backup

`restore_database.py` **overwrites** existing data and asks for confirmation
(skip with `--yes`). Restore the database, the uploads, or both:

```bash
# Restore both (recommended: use the matching timestamped pair)
python scripts/restore_database.py \
  --database /var/backups/travelmind/travelmind_backup_20260623_120000.dump \
  --uploads  /var/backups/travelmind/travelmind_uploads_20260623_120000.tar.gz

# Restore only the photos into a specific directory
python scripts/restore_database.py \
  --uploads /var/backups/travelmind/travelmind_uploads_20260623_120000.tar.gz \
  --uploads-dir ./uploads
```

After restoring the database to a new PostgreSQL instance, make sure the schema
exists first (the app creates tables on startup, or run your migrations).

---

## Automate (generic Linux / cron)

Daily backup at 03:00, keeping 30 days, written to a separate disk:

```cron
0 3 * * * cd /opt/travelmind/backend && /opt/travelmind/venv/bin/python \
  scripts/backup_database.py --output /mnt/backupdisk/travelmind --keep 30 \
  >> /var/log/travelmind-backup.log 2>&1
```

### 3-2-1 rule

Keep **3** copies, on **2** different media, with **1** off-site. A backup that
sits on the same disk as the live data protects against accidental deletion, but
**not** against disk failure. Periodically copy `/var/backups/travelmind` to an
external drive or remote storage (rsync, rclone, object storage, …).

---

## Appendix: ZimaOS

On ZimaOS the root filesystem is read-only and there is no native Python, so
TravelMind runs in Docker and the backup runs **inside the backend container**.
Persistent data lives under `/DATA`.

**Assumptions** (adapt to your deployment): the backend container is named
`travelmind-backend`, its uploads are at `/app/uploads`, and a host backups
directory is bind-mounted in:

```
/DATA/AppData/travelmind/backups   ->  /app/backups   (in the backend container)
```

Manual backup via `docker exec` (note the `DOCKER_CONFIG`, required on ZimaOS):

```bash
export DOCKER_CONFIG=/DATA/.docker
docker exec travelmind-backend \
  python scripts/backup_database.py --output ./backups --uploads-dir ./uploads --keep 30
```

The backups land on `/DATA/AppData/travelmind/backups`. For real resilience,
copy them to a **second disk** (ZimaOS mounts data disks under `/media/sdX`),
e.g. `/media/sdb/backups/travelmind`, or sync them off-box.

### Scheduling with zima-cron

ZimaOS has no host cron; use a `zima-cron` container (Debian + `cron`) with the
Docker socket mounted so it can exec into the backend container. Place a cron
file at `/DATA/AppData/zima-cron/config/travelmind`:

```cron
# Daily at 03:00 — TravelMind database + uploads
0 3 * * * root DOCKER_CONFIG=/DATA/.docker docker exec travelmind-backend python scripts/backup_database.py --output ./backups --uploads-dir ./uploads --keep 30 >> /var/log/cron/travelmind.log 2>&1
```

Restore on ZimaOS works the same way via `docker exec ... python scripts/restore_database.py ...`.
