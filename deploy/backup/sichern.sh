#!/bin/sh
#
# TravelMind — Sicherung von Datenbank und Fotos.
#
# Laeuft IM Compose-Netz, in einem postgres:16-alpine-Container. Daraus folgen
# drei Eigenschaften, die die erste Fassung dieses Skripts nicht hatte:
#
#   • Kein Docker-Socket. Die erste Fassung rief `docker exec` und brauchte
#     dafuer Zugriff auf den Socket — das ist faktisch Root auf dem Host.
#     pg_dump kann ueber das Netz arbeiten; mehr braucht es nicht.
#   • Keine Root-Rechte auf dem Host, kein systemd-Zugriff.
#   • Die pg_dump-Version kann nicht von der Serverversion abweichen: beide
#     kommen aus demselben Image-Stand.
#
# Warum ueberhaupt: `backend/scripts/backup_database.py` ruft pg_dump im
# Backend-Container auf — dort gibt es keins. Am 2026-08-25 gemessen:
#     ERROR - pg_dump not found. Please install PostgreSQL client tools.
# Nachinstallieren waere die falsche Antwort: Debian bookworm liefert pg_dump
# 15, der Server laeuft auf 16, und pg_dump verweigert den Dienst gegen eine
# neuere Serverversion.
#
set -eu

ZIEL="${BACKUP_DIR:-/backups}"
QUELLE="${UPLOADS_DIR:-/uploads}"
BEHALTEN="${BACKUP_KEEP:-14}"
DB_HOST="${PGHOST:-db}"
DB_NAME="${PGDATABASE:-travelmind}"
DB_USER="${PGUSER:-travelmind}"

STEMPEL="$(date +%Y%m%d-%H%M%S)"
DUMP="$ZIEL/travelmind-db-$STEMPEL.dump"
FOTOS="$ZIEL/travelmind-uploads-$STEMPEL.tar.gz"
MANIFEST="$ZIEL/travelmind-$STEMPEL.manifest"

melde() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

mkdir -p "$ZIEL"

# ── 1. Datenbank ──────────────────────────────────────────────────────────
melde "Datenbank sichern (${DB_USER}@${DB_HOST}/${DB_NAME}) …"
# -Fc: eigenes Format. Es laesst sich mit pg_restore PRUEFEN und teilweise
# zurueckspielen; ein reiner SQL-Text kann beides nicht.
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -Fc -f "$DUMP"

# Ein Dump, den pg_restore nicht lesen kann, ist kein Dump. Diese Pruefung
# kostet Sekunden und faengt genau den Fall ab, in dem die Sicherung jede
# Nacht laeuft und nichts taugt.
if ! pg_restore --list "$DUMP" > /dev/null 2>&1; then
  melde "FEHLER: der erzeugte Dump ist mit pg_restore nicht lesbar."
  rm -f "$DUMP"
  exit 1
fi

tabellen="$(pg_restore --list "$DUMP" 2>/dev/null | grep -c 'TABLE DATA' || true)"
melde "Datenbank gesichert: $(du -h "$DUMP" | cut -f1), $tabellen Tabellen mit Daten"
if [ "$tabellen" -lt 1 ]; then
  melde "FEHLER: der Dump enthaelt keine einzige Tabelle mit Daten."
  rm -f "$DUMP"
  exit 1
fi

# ── 2. Fotos ──────────────────────────────────────────────────────────────
# Die Bilder lassen sich NICHT neu erzeugen, wenn sie fehlen — anders als
# alles andere. Sie sind kein Zusatz, sondern der wichtigere Teil.
melde "Fotos sichern …"
auf_platte="$(find "$QUELLE" -type f | wc -l)"
tar czf "$FOTOS" -C "$(dirname "$QUELLE")" "$(basename "$QUELLE")"
im_archiv="$(tar tzf "$FOTOS" | grep -vc '/$' || true)"
melde "Fotos gesichert: $(du -h "$FOTOS" | cut -f1), $im_archiv Dateien"
if [ "$im_archiv" -lt "$auf_platte" ]; then
  melde "FEHLER: im Archiv sind $im_archiv Dateien, auf der Platte liegen $auf_platte."
  exit 1
fi

# ── 3. Manifest ───────────────────────────────────────────────────────────
# NUR Pruefsummenzeilen, keine Kommentare. busybox' sha256sum -c ueberspringt
# Kommentarzeilen NICHT, sondern haelt sie fuer Dateinamen — am 2026-08-25
# gemessen: zwei erfundene "FAILED" neben zwei echten "OK", Exit 1. Die
# Erlaeuterung steht in docs/BACKUP.md, nicht in der Pruefdatei.
#
# Erst in eine Nebendatei, dann umbenennen: so gibt es nie ein halbfertiges
# Manifest, das wie ein vollstaendiges aussieht.
manifest_roh="$MANIFEST.teil"
(cd "$ZIEL" && sha256sum "travelmind-db-$STEMPEL.dump" "travelmind-uploads-$STEMPEL.tar.gz") > "$manifest_roh"
mv "$manifest_roh" "$MANIFEST"

# ── 4. Aufraeumen ─────────────────────────────────────────────────────────
# Nach ANZAHL, nicht nach Alter: faellt die Automatik laenger aus, wuerde eine
# Altersregel ausgerechnet die letzten guten Staende mitnehmen.
for muster in 'travelmind-db-*.dump' 'travelmind-uploads-*.tar.gz' 'travelmind-*.manifest'; do
  # shellcheck disable=SC2012,SC2086
  # SC2012: `ls -t` sortiert nach Zeit — genau das ist hier gewollt.
  # SC2086: $muster MUSS unquotiert bleiben, sonst greift das Glob nicht.
  ls -t "$ZIEL"/$muster 2>/dev/null | tail -n "+$((BEHALTEN + 1))" | while read -r alt; do
    melde "entferne alten Stand: $(basename "$alt")"
    rm -f "$alt"
  done
done

melde "Fertig. Vorhandene Staende: $(find "$ZIEL" -maxdepth 1 -name 'travelmind-db-*.dump' | wc -l)"
