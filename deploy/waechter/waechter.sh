#!/bin/sh
#
# TravelMind — Wächter.
#
# Der Grund für diese Datei steht im Befund vom 2026-08-25: Die Produktion war
# seit dem 26. Juni abgeschaltet — zwei Monate — und es ist niemandem
# aufgefallen. Nicht weil niemand hingesehen hätte, sondern weil nichts
# hingesehen hat.
#
# Der Wächter fragt regelmäßig zwei Dinge, und zwar VON AUSSEN durch dieselbe
# Kette, die auch ein Nutzer nimmt:
#
#   1. Antwortet die Oberfläche?
#   2. Antwortet die API — und meldet sie ihre Datenbank als gesund?
#
# Wichtig ist der Zusatz bei 2: Ein HTTP 200 allein sagt nichts. Der
# SPA-Rückfall der Oberfläche beantwortet JEDEN Pfad mit 200, und die API kann
# 200 liefern, während die Datenbank weg ist. Deshalb wird der INHALT geprüft.
#
set -eu

ZIEL_UI="${WATCH_UI:-http://frontend:8080/}"
ZIEL_API="${WATCH_API:-http://backend:8137/api/health}"
TAKT="${WATCH_INTERVAL:-60}"
GEDULD="${WATCH_FAILURES:-3}"

melde() { printf '%s  [waechter] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

benachrichtige() {
  titel="$1"
  text="$2"
  prio="${3:-0}"
  melde "$titel — $text"
  if [ -n "${PUSHOVER_TOKEN:-}" ] && [ -n "${PUSHOVER_USER:-}" ]; then
    if curl -sS --max-time 10 -o /dev/null \
        --form-string "token=$PUSHOVER_TOKEN" \
        --form-string "user=$PUSHOVER_USER" \
        --form-string "title=$titel" \
        --form-string "message=$text" \
        --form-string "priority=$prio" \
        https://api.pushover.net/1/messages.json; then
      melde "Benachrichtigung verschickt"
    else
      # Ein Wächter, dessen Meldeweg still ausfällt, ist schlimmer als keiner:
      # er erzeugt das Gefühl, überwacht zu sein.
      melde "ACHTUNG: die Benachrichtigung konnte NICHT verschickt werden"
    fi
  else
    melde "(kein Pushover konfiguriert — nur im Protokoll)"
  fi
}

pruefe() {
  # Oberfläche: es muss etwas ankommen, nicht nur ein Statuscode.
  # Kein `|| echo 000`: curl schreibt bei einem Fehlschlag ueber -w bereits
  # "000" — der Zusatz haengte eine zweite Null-Gruppe an und das Protokoll
  # meldete "HTTP 000000". Der Exit-Code wird stattdessen ignoriert, weil die
  # Auswertung unten ohnehin ueber den Code laeuft.
  ui_code="$(curl -sS -o /tmp/ui.out -w '%{http_code}' --max-time 10 "$ZIEL_UI" 2>/dev/null || true)"
  ui_code="${ui_code:-000}"
  ui_bytes="$(wc -c < /tmp/ui.out 2>/dev/null || echo 0)"
  if [ "$ui_code" != "200" ] || [ "$ui_bytes" -lt 200 ]; then
    echo "Oberfläche antwortet nicht brauchbar (HTTP $ui_code, $ui_bytes Bytes)"
    return 1
  fi

  # API: Statuscode UND Inhalt. "healthy" muss drinstehen, und die Datenbank
  # darf nicht als ungesund gemeldet sein.
  api_code="$(curl -sS -o /tmp/api.out -w '%{http_code}' --max-time 10 "$ZIEL_API" 2>/dev/null || true)"
  api_code="${api_code:-000}"
  if [ "$api_code" != "200" ]; then
    echo "API antwortet mit HTTP $api_code"
    return 1
  fi
  if ! grep -q '"status":"healthy"' /tmp/api.out; then
    echo "API antwortet, meldet sich aber nicht als gesund"
    return 1
  fi
  if grep -q '"database":{"status":"unhealthy"' /tmp/api.out; then
    echo "API läuft, meldet die Datenbank aber als ungesund"
    return 1
  fi
  return 0
}

melde "gestartet — Takt ${TAKT}s, Alarm nach $GEDULD Fehlversuchen"
melde "  Oberfläche: $ZIEL_UI"
melde "  API:        $ZIEL_API"

fehler=0
war_unten=0

while true; do
  if grund="$(pruefe)"; then
    if [ "$war_unten" -eq 1 ]; then
      benachrichtige "TravelMind ist wieder da" "Die Anwendung antwortet wieder normal." 0
      war_unten=0
    fi
    fehler=0
  else
    fehler=$((fehler + 1))
    melde "Fehlversuch $fehler/$GEDULD: $grund"
    if [ "$fehler" -ge "$GEDULD" ] && [ "$war_unten" -eq 0 ]; then
      # Priorität 1 = an Ruhezeiten vorbei. Ein Ausfall, der bis zum Morgen
      # wartet, ist der Fall vom 26. Juni.
      benachrichtige "TravelMind antwortet nicht" "$grund (seit $GEDULD Versuchen)" 1
      war_unten=1
    fi
  fi
  sleep "$TAKT"
done
