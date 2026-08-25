#!/bin/sh
#
# TravelMind — Restore-Probe.
#
# Eine Sicherung ist erst dann eine, wenn sie sich zurueckspielen laesst.
# Alles andere ist eine Datei mit einem beruhigenden Namen.
#
# Am 2026-08-25 lag im Sicherungsverzeichnis genau EINE Datei, vom 24. Juni —
# und die 104 MB Fotos hatten ueberhaupt keine Sicherung. Niemand hat das
# bemerkt, weil niemand je versucht hat, etwas zurueckzuholen.
#
# Die Probe spielt den juengsten Stand in eine WEGWERF-Datenbank, zaehlt dort
# die Zeilen und vergleicht sie mit der laufenden. Die Wegwerf-Datenbank wird
# in jedem Fall wieder entfernt — auch bei Abbruch.
#
set -eu

ZIEL="${BACKUP_DIR:-/backups}"
QUELLE="${UPLOADS_DIR:-/uploads}"
DB_HOST="${PGHOST:-db}"
DB_NAME="${PGDATABASE:-travelmind}"
DB_USER="${PGUSER:-travelmind}"
PROBE_DB="travelmind_probe_$$"

melde() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

aufraeumen() {
  psql -h "$DB_HOST" -U "$DB_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $PROBE_DB;" >/dev/null 2>&1 || true
}
trap aufraeumen EXIT INT TERM

# ── Juengsten Stand finden ────────────────────────────────────────────────
# shellcheck disable=SC2012
# `ls -t` nach Zeit ist hier genau das Gewollte.
DUMP="$(ls -t "$ZIEL"/travelmind-db-*.dump 2>/dev/null | head -1 || true)"
if [ -z "$DUMP" ]; then
  melde "FEHLER: kein Datenbank-Stand in $ZIEL gefunden."
  exit 1
fi
STEMPEL="$(basename "$DUMP" | sed 's/travelmind-db-//; s/\.dump$//')"
FOTOS="$ZIEL/travelmind-uploads-$STEMPEL.tar.gz"
MANIFEST="$ZIEL/travelmind-$STEMPEL.manifest"
melde "geprueft wird der Stand vom $STEMPEL"

# ── 1. Pruefsummen ────────────────────────────────────────────────────────
if [ -f "$MANIFEST" ]; then
  # Kein --quiet: das kennt busybox nicht (alpine). Stattdessen die Ausgabe
  # umleiten — portabel zwischen GNU und busybox.
  if (cd "$ZIEL" && sha256sum -c "$(basename "$MANIFEST")" >/dev/null 2>&1); then
    melde "Pruefsummen stimmen"
  else
    melde "FEHLER: Pruefsummen weichen ab — der Stand ist beschaedigt."
    exit 1
  fi
else
  melde "FEHLER: kein Manifest zu diesem Stand — Pruefsummen nicht vergleichbar."
  exit 1
fi

# ── 2. In eine Wegwerf-Datenbank zurueckspielen ───────────────────────────
melde "Wegwerf-Datenbank $PROBE_DB anlegen und zurueckspielen …"
psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "CREATE DATABASE $PROBE_DB;" >/dev/null

# --exit-on-error: ohne das laeuft pg_restore ueber Fehler hinweg und meldet
# am Ende trotzdem Erfolg — genau die Sorte stiller Fehlschlag, die eine
# Sicherung wertlos macht, ohne dass es auffaellt.
if ! pg_restore -h "$DB_HOST" -U "$DB_USER" -d "$PROBE_DB" --exit-on-error "$DUMP"; then
  melde "FEHLER: pg_restore ist gescheitert."
  exit 1
fi
melde "zurueckgespielt"

# ── 3. Zeilen vergleichen ─────────────────────────────────────────────────
abweichung=0
for t in users trips places diary_entries media expenses; do
  echt="$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME"  -t -A -c "SELECT count(*) FROM $t;" 2>/dev/null || echo '-')"
  probe="$(psql -h "$DB_HOST" -U "$DB_USER" -d "$PROBE_DB" -t -A -c "SELECT count(*) FROM $t;" 2>/dev/null || echo '-')"
  if [ "$echt" = "$probe" ]; then
    printf '    %-15s %6s = %-6s ok\n' "$t" "$echt" "$probe"
  else
    printf '    %-15s %6s != %-6s ABWEICHUNG\n' "$t" "$echt" "$probe"
    abweichung=1
  fi
done

# Positivkontrolle: haette der Vergleich ueberhaupt anschlagen koennen?
# Zwei leere Datenbanken waeren sonst "ok" — und das Ergebnis wertlos.
nutzer="$(psql -h "$DB_HOST" -U "$DB_USER" -d "$PROBE_DB" -t -A -c "SELECT count(*) FROM users;" 2>/dev/null || echo 0)"
if [ "$nutzer" -lt 1 ]; then
  melde "FEHLER: die zurueckgespielte Datenbank hat keinen einzigen Nutzer — der Vergleich haette nichts belegt."
  exit 1
fi

[ "$abweichung" -eq 0 ] || {
  melde "FEHLER: die zurueckgespielten Daten weichen von der laufenden Datenbank ab."
  exit 1
}

# ── 4. Fotos ──────────────────────────────────────────────────────────────
if [ ! -f "$FOTOS" ]; then
  melde "FEHLER: zu diesem Stand gibt es kein Foto-Archiv ($FOTOS)."
  exit 1
fi
# Wirklich AUSPACKEN, nicht nur auflisten: ein Inhaltsverzeichnis kann
# vollstaendig sein, waehrend die Daten dahinter beschaedigt sind.
tmp="$(mktemp -d)"
tar xzf "$FOTOS" -C "$tmp"
entpackt="$(find "$tmp" -type f | wc -l)"
auf_platte="$(find "$QUELLE" -type f | wc -l)"
rm -rf "$tmp"
printf '    %-15s %6s entpackt, %s auf Platte\n' "uploads" "$entpackt" "$auf_platte"
if [ "$entpackt" -lt "$auf_platte" ]; then
  melde "FEHLER: es wurden weniger Fotos entpackt als auf der Platte liegen."
  exit 1
fi

melde "PROBE BESTANDEN — dieser Stand laesst sich zurueckspielen."
