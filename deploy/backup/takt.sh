#!/bin/sh
#
# TravelMind — Takt für die Sicherung.
#
# Ein winziger Scheduler statt cron oder systemd. Grund: beides braucht
# Root auf dem Host. Dieser Container läuft im Compose-Verbund, wird mit
# ihm gestartet und gestoppt, und ist in `docker ps` sichtbar — ein
# ausgefallener Zeitgeber fällt damit auf, statt still zu verschwinden.
#
# BACKUP_UHRZEIT ist eine Uhrzeit in HH:MM (lokale Zeit des Containers,
# gesetzt über TZ). Der Takt prüft jede Minute, ob sie erreicht ist.
#
# Nach JEDER Sicherung läuft die Restore-Probe. Nicht wöchentlich, nicht
# "gelegentlich": eine Sicherung, die nie zurückgespielt wurde, ist eine
# Behauptung. Die Probe kostet hier zwei Sekunden.
#
set -eu

UHRZEIT="${BACKUP_UHRZEIT:-03:00}"
SOFORT="${BACKUP_BEIM_START:-nein}"

melde() { printf '%s  [takt] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

lauf() {
  melde "Sicherung beginnt"
  if /skripte/sichern.sh; then
    melde "Sicherung fertig — jetzt die Restore-Probe"
    if /skripte/probe.sh; then
      melde "ERGEBNIS: Sicherung erstellt UND zurückspielbar"
      return 0
    fi
    melde "ALARM: die Sicherung wurde erstellt, ist aber NICHT zurückspielbar."
    return 1
  fi
  melde "ALARM: die Sicherung ist gescheitert."
  return 1
}

melde "gestartet — tägliche Sicherung um $UHRZEIT (TZ=${TZ:-nicht gesetzt})"

if [ "$SOFORT" = "ja" ]; then
  melde "BACKUP_BEIM_START=ja — ein Lauf sofort"
  lauf || true
fi

letzter_tag=""
while true; do
  jetzt="$(date +%H:%M)"
  heute="$(date +%Y-%m-%d)"
  if [ "$jetzt" = "$UHRZEIT" ] && [ "$heute" != "$letzter_tag" ]; then
    letzter_tag="$heute"
    lauf || true
  fi
  sleep 30
done
