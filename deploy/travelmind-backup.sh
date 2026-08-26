#!/usr/bin/env bash
#
# TravelMind — Sicherung von Datenbank und Fotos.
#
# WARUM DIESES SKRIPT UND NICHT backend/scripts/backup_database.py:
# Jenes Skript ruft `pg_dump` im Backend-Container auf — dort gibt es keins.
# Am 2026-08-25 in der laufenden Produktion gemessen:
#
#     docker exec travelmind-backend python /app/scripts/backup_database.py …
#     ERROR - pg_dump not found. Please install PostgreSQL client tools.
#
# Nachinstallieren waere die naheliegende Antwort und die falsche: Debian
# bookworm liefert pg_dump 15, der Server laeuft auf 16, und pg_dump verweigert
# den Dienst gegen eine neuere Serverversion. Dieses Skript benutzt stattdessen
# den pg_dump DES DATENBANK-CONTAINERS. Damit koennen die Versionen per
# Konstruktion nicht auseinanderlaufen.
#
# Aufruf:
#   travelmind-backup.sh [--ziel <verzeichnis>] [--behalten <n>]
#
set -euo pipefail

ZIEL="${TRAVELMIND_BACKUP_DIR:-/DATA/AppData/travelmind/backups}"
DATEN="${TRAVELMIND_DATA:-/DATA/AppData/travelmind}"
BEHALTEN="${TRAVELMIND_BACKUP_KEEP:-14}"
DB_CONTAINER="${TRAVELMIND_DB_CONTAINER:-travelmind-db}"
DB_NAME="${POSTGRES_DB:-travelmind}"
DB_USER="${POSTGRES_USER:-travelmind}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ziel)      ZIEL="$2"; shift 2 ;;
    --behalten)  BEHALTEN="$2"; shift 2 ;;
    *) echo "Unbekanntes Argument: $1" >&2; exit 2 ;;
  esac
done

STEMPEL="$(date +%Y%m%d-%H%M%S)"
DUMP="$ZIEL/travelmind-db-$STEMPEL.dump"
FOTOS="$ZIEL/travelmind-uploads-$STEMPEL.tar.gz"
MANIFEST="$ZIEL/travelmind-$STEMPEL.manifest"

melde() { printf '%s  %s\n' "$(date +%H:%M:%S)" "$*"; }

mkdir -p "$ZIEL"

# ── 1. Datenbank ──────────────────────────────────────────────────────────
melde "Datenbank sichern …"
# -Fc: eigenes Format. Es laesst sich mit pg_restore pruefen UND teilweise
# zurueckspielen — ein reiner SQL-Text kann beides nicht.
# Der Dump entsteht IM Datenbank-Container als echte Datei und wird erst
# danach herausgeholt. Grund: ein Archiv im eigenen Format muss durchsuchbar
# sein — ueber eine Pipe kann pg_restore es nicht lesen. Genau daran ist der
# erste Versuch am 2026-08-25 gescheitert ("nicht lesbar", obwohl der Dump in
# Ordnung war).
IM_CONTAINER="/tmp/travelmind-$STEMPEL.dump"
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc -f "$IM_CONTAINER"

# Ein Dump, den pg_restore nicht LESEN kann, ist kein Dump. Diese Pruefung
# kostet Sekunden und faengt genau den Fall ab, in dem die Sicherung jede
# Nacht laeuft und nichts taugt.
if ! docker exec "$DB_CONTAINER" pg_restore --list "$IM_CONTAINER" > /dev/null 2>&1; then
  melde "FEHLER: der erzeugte Dump ist mit pg_restore nicht lesbar."
  docker exec "$DB_CONTAINER" rm -f "$IM_CONTAINER" || true
  exit 1
fi
tabellen="$(docker exec "$DB_CONTAINER" pg_restore --list "$IM_CONTAINER" 2>/dev/null | grep -c 'TABLE DATA' || true)"
docker cp "$DB_CONTAINER:$IM_CONTAINER" "$DUMP"
docker exec "$DB_CONTAINER" rm -f "$IM_CONTAINER" || true
melde "Datenbank gesichert: $(du -h "$DUMP" | cut -f1), $tabellen Tabellen mit Daten"

if [[ "$tabellen" -lt 1 ]]; then
  melde "FEHLER: der Dump enthaelt keine einzige Tabelle mit Daten."
  rm -f "$DUMP"
  exit 1
fi

# ── 2. Fotos ──────────────────────────────────────────────────────────────
# Die Bilder lassen sich NICHT wiederherstellen, wenn sie fehlen — anders als
# alles andere. Deshalb sind sie kein Zusatz, sondern der wichtigere Teil.
melde "Fotos sichern …"
anzahl_vorher="$(find "$DATEN/uploads" -type f 2>/dev/null | wc -l)"
tar czf "$FOTOS" -C "$DATEN" uploads
anzahl_im_archiv="$(tar tzf "$FOTOS" | grep -vc '/$' || true)"
melde "Fotos gesichert: $(du -h "$FOTOS" | cut -f1), $anzahl_im_archiv Dateien"

if [[ "$anzahl_im_archiv" -lt "$anzahl_vorher" ]]; then
  melde "FEHLER: im Archiv sind $anzahl_im_archiv Dateien, im Verzeichnis waren $anzahl_vorher."
  exit 1
fi

# ── 3. Manifest ───────────────────────────────────────────────────────────
{
  echo "# TravelMind-Sicherung $STEMPEL"
  echo "# Zum Pruefen: sha256sum -c <diese Datei>"
  sha256sum "$DUMP" "$FOTOS" | sed "s#$ZIEL/##"
} > "$MANIFEST"

# ── 4. Aufraeumen ─────────────────────────────────────────────────────────
# Nach ANZAHL, nicht nach Alter: bei einem laengeren Ausfall der Automatik
# wuerde eine Altersregel die letzten guten Staende mitnehmen.
for muster in "travelmind-db-*.dump" "travelmind-uploads-*.tar.gz" "travelmind-*.manifest"; do
  # shellcheck disable=SC2012,SC2086
  # SC2012: `ls -t` nach Zeit ist hier genau das Gewollte.
  # SC2086: $muster MUSS unquotiert bleiben — sonst findet das Glob nichts.
  ls -t "$ZIEL"/$muster 2>/dev/null | tail -n "+$((BEHALTEN + 1))" | while read -r alt; do
    melde "entferne alten Stand: $(basename "$alt")"
    rm -f "$alt"
  done
done

melde "Fertig. Vorhandene Staende: $(find "$ZIEL" -maxdepth 1 -name "travelmind-db-*.dump" | wc -l)"
