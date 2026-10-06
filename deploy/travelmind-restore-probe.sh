#!/usr/bin/env bash
#
# TravelMind — Restore-Probe.
#
# Eine Sicherung ist erst dann eine, wenn sie sich zurueckspielen laesst.
# Alles andere ist eine Datei mit einem beruhigenden Namen.
#
# Am 2026-08-25 lag in /DATA/AppData/travelmind/backups genau EINE Datei, vom
# 24. Juni — und die 104 MB Fotos hatten ueberhaupt keine Sicherung. Niemand
# haette das bemerkt, weil niemand je versucht hat, etwas zurueckzuholen.
#
# Diese Probe spielt den juengsten Stand in eine WEGWERF-Datenbank zurueck,
# zaehlt dort die Zeilen und vergleicht sie mit der laufenden. Die
# Wegwerf-Datenbank wird danach in jedem Fall entfernt — auch bei Abbruch.
#
# Aufruf:
#   travelmind-restore-probe.sh [--ziel <verzeichnis>]
#
set -euo pipefail

ZIEL="${TRAVELMIND_BACKUP_DIR:-/DATA/AppData/travelmind/backups}"
DB_CONTAINER="${TRAVELMIND_DB_CONTAINER:-travelmind-db}"
DB_NAME="${POSTGRES_DB:-travelmind}"
DB_USER="${POSTGRES_USER:-travelmind}"
PROBE_DB="travelmind_probe_$$"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ziel) ZIEL="$2"; shift 2 ;;
    *) echo "Unbekanntes Argument: $1" >&2; exit 2 ;;
  esac
done

melde() { printf '%s  %s\n' "$(date +%H:%M:%S)" "$*"; }

aufraeumen() {
  docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $PROBE_DB;" >/dev/null 2>&1 || true
}
trap aufraeumen EXIT

# ── Juengsten Stand finden ────────────────────────────────────────────────
DUMP="$(find "$ZIEL" -maxdepth 1 -name 'travelmind-db-*.dump' -printf '%T@ %p\n' \
        | sort -rn | head -1 | cut -d' ' -f2- || true)"
if [[ -z "$DUMP" ]]; then
  melde "FEHLER: kein Datenbank-Stand in $ZIEL gefunden."
  exit 1
fi
STEMPEL="$(basename "$DUMP" | sed 's/travelmind-db-//; s/\.dump//')"
FOTOS="$ZIEL/travelmind-uploads-$STEMPEL.tar.gz"
melde "geprueft wird der Stand vom $STEMPEL"

# ── 1. Pruefsummen ────────────────────────────────────────────────────────
MANIFEST="$ZIEL/travelmind-$STEMPEL.manifest"
if [[ -f "$MANIFEST" ]]; then
  if (cd "$ZIEL" && sha256sum -c --quiet "$MANIFEST"); then
    melde "Pruefsummen stimmen"
  else
    melde "FEHLER: Pruefsummen weichen ab — der Stand ist beschaedigt."
    exit 1
  fi
else
  melde "WARNUNG: kein Manifest zu diesem Stand, Pruefsummen nicht vergleichbar"
fi

# ── 2. Datenbank in eine Wegwerf-Datenbank zurueckspielen ─────────────────
melde "Wegwerf-Datenbank $PROBE_DB anlegen und zurueckspielen …"
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $PROBE_DB;" >/dev/null

# Wie beim Sichern: das Archiv muss als DATEI vorliegen, nicht als Pipe —
# pg_restore muss darin springen koennen.
IM_CONTAINER="/tmp/probe-$$.dump"
docker cp "$DUMP" "$DB_CONTAINER:$IM_CONTAINER"

# --exit-on-error: sonst laeuft pg_restore ueber Fehler hinweg und meldet
# am Ende trotzdem Erfolg — genau die Sorte stiller Fehlschlag, die eine
# Sicherung wertlos macht, ohne dass es auffaellt.
if ! docker exec "$DB_CONTAINER" pg_restore -U "$DB_USER" -d "$PROBE_DB" --exit-on-error "$IM_CONTAINER"; then
  melde "FEHLER: pg_restore ist gescheitert."
  docker exec "$DB_CONTAINER" rm -f "$IM_CONTAINER" || true
  exit 1
fi
docker exec "$DB_CONTAINER" rm -f "$IM_CONTAINER" || true
melde "zurueckgespielt"

# ── 3. Zeilen vergleichen ─────────────────────────────────────────────────
TABELLEN=(users trips places diary_entries media expenses)
abweichung=0
for t in "${TABELLEN[@]}"; do
  echt="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"  -t -A -c "SELECT count(*) FROM $t;" 2>/dev/null || echo "-")"
  probe="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$PROBE_DB" -t -A -c "SELECT count(*) FROM $t;" 2>/dev/null || echo "-")"
  if [[ "$echt" == "$probe" ]]; then
    printf '    %-15s %6s = %-6s ok\n' "$t" "$echt" "$probe"
  else
    printf '    %-15s %6s ≠ %-6s ABWEICHUNG\n' "$t" "$echt" "$probe"
    abweichung=1
  fi
done

# Positivkontrolle: haette der Vergleich ueberhaupt anschlagen koennen?
# Eine leere Datenbank auf beiden Seiten waere sonst "ok".
gesamt="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$PROBE_DB" -t -A -c "SELECT count(*) FROM users;" 2>/dev/null || echo 0)"
if [[ "$gesamt" -lt 1 ]]; then
  melde "FEHLER: die zurueckgespielte Datenbank enthaelt keinen einzigen Nutzer — der Vergleich haette nichts belegt."
  exit 1
fi

if [[ "$abweichung" -ne 0 ]]; then
  melde "FEHLER: die zurueckgespielten Daten weichen von der laufenden Datenbank ab."
  exit 1
fi

# ── 4. Fotos ──────────────────────────────────────────────────────────────
if [[ -f "$FOTOS" ]]; then
  im_archiv="$(tar tzf "$FOTOS" | grep -vc '/$' || true)"
  auf_platte="$(find "${TRAVELMIND_DATA:-/DATA/AppData/travelmind}/uploads" -type f | wc -l)"
  # Wirklich AUSPACKEN, nicht nur auflisten: ein Inhaltsverzeichnis kann
  # vollstaendig sein, waehrend die Daten dahinter beschaedigt sind.
  tmp="$(mktemp -d)"
  tar xzf "$FOTOS" -C "$tmp"
  entpackt="$(find "$tmp" -type f | wc -l)"
  rm -rf "$tmp"
  printf '    %-15s %6s im Archiv, %s entpackt, %s auf Platte\n' "uploads" "$im_archiv" "$entpackt" "$auf_platte"
  if [[ "$entpackt" -lt "$auf_platte" ]]; then
    melde "FEHLER: es wurden weniger Fotos entpackt als auf der Platte liegen."
    exit 1
  fi
else
  melde "FEHLER: zu diesem Stand gibt es kein Foto-Archiv ($FOTOS)."
  exit 1
fi

melde "PROBE BESTANDEN — dieser Stand laesst sich zurueckspielen."
