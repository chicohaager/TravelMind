#!/usr/bin/env bash
#
# TravelMind — Ausrollen und Zurückrollen.
#
# Fasst zusammen, was am 2026-08-25 zwanzigmal von Hand gemacht wurde. Der
# Punkt ist nicht die Bequemlichkeit, sondern dass ein Ausrollen ohne Rückweg
# kein Ausrollen ist: Images tragen den Commit-SHA als Tag, alte Stände bleiben
# liegen, und `--zurueck` setzt den Tag eine Zeile weiter zurück.
#
#   ausrollen.sh                      baut, überträgt und startet HEAD
#   ausrollen.sh --nur-frontend       nur das Frontend neu bauen
#   ausrollen.sh --zurueck            auf den vorher ausgerollten Stand zurück
#   ausrollen.sh --staende            zeigt, was auf dem Host liegt
#
set -euo pipefail

HOST="${TRAVELMIND_HOST:-<benutzer>@<host>}"
FERN="${TRAVELMIND_REMOTE_DIR:-/DATA/AppData/travelmind}"
COMPOSE="${TRAVELMIND_COMPOSE:-/usr/lib/docker/cli-plugins/docker-compose}"
WURZEL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

melde()  { printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
fehler() { printf '\n\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

fern() { ssh -o BatchMode=yes "$HOST" "$@"; }

# Der Parameter-Datei wird der Tag entnommen und geschrieben. Sie enthaelt
# KEINE Geheimnisse — die stehen in .env und werden hier nie angefasst.
parameter_lesen() {
  fern "docker run --rm -v $FERN:/d:ro alpine:latest grep '^TRAVELMIND_TAG=' /d/deploy-params.conf" \
    2>/dev/null | cut -d= -f2 | tr -d '\r\n'
}

compose_auf() {
  fern "cd $FERN && $COMPOSE -f docker-compose.prod.yml --env-file .env --env-file deploy-params.conf up -d ${1:-}"
}

tag_setzen() {
  local neu="$1"
  fern "docker run --rm -v $FERN:/d alpine:latest sh -c \"sed -i 's/^TRAVELMIND_TAG=.*/TRAVELMIND_TAG=$neu/' /d/deploy-params.conf\""
}

# ── Argumente ─────────────────────────────────────────────────────────────
NUR=""
MODUS="ausrollen"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --nur-frontend) NUR="frontend"; shift ;;
    --nur-backend)  NUR="backend";  shift ;;
    --zurueck)      MODUS="zurueck"; shift ;;
    --staende)      MODUS="staende"; shift ;;
    *) fehler "Unbekanntes Argument: $1" ;;
  esac
done

# ── Stände anzeigen ───────────────────────────────────────────────────────
if [[ "$MODUS" == "staende" ]]; then
  melde "Auf dem Host vorhandene Images"
  fern "docker images --format '{{.Repository}}:{{.Tag}}\t{{.CreatedSince}}' | grep travelmind | sort"
  melde "Aktuell ausgerollt"
  echo "  TRAVELMIND_TAG=$(parameter_lesen)"
  exit 0
fi

# ── Zurückrollen ──────────────────────────────────────────────────────────
if [[ "$MODUS" == "zurueck" ]]; then
  aktuell="$(parameter_lesen)"
  melde "Aktuell ausgerollt: $aktuell"
  # Der vorherige Stand ist der zweitjuengste Image-Tag auf dem HOST — nicht
  # der zweitjuengste Commit. Was nicht auf dem Host liegt, kann man nicht
  # zurueckrollen.
  vorher="$(fern "docker images --format '{{.Tag}}\t{{.CreatedAt}}' travelmind-backend | sort -k2 -r | awk -v akt=\"$aktuell\" '\$1 != akt && \$1 != \"latest\" {print \$1; exit}'")"
  [[ -n "$vorher" ]] || fehler "Kein frueherer Stand auf dem Host gefunden."
  melde "Zurueck auf: $vorher"
  tag_setzen "$vorher"
  compose_auf
  melde "Zurueckgerollt. Pruefung folgt."
else
  # ── Ausrollen ───────────────────────────────────────────────────────────
  cd "$WURZEL"
  [[ -z "$(git status --porcelain)" ]] || fehler "Arbeitsverzeichnis ist nicht sauber — erst committen."
  SHA="$(git rev-parse --short HEAD)"
  melde "Ausrollen von $SHA"

  ZWISCHEN="$(mktemp -d)"
  trap 'rm -rf "$ZWISCHEN"' EXIT

  bauen=()
  [[ "$NUR" == "frontend" ]] || bauen+=("backend")
  [[ "$NUR" == "backend"  ]] || bauen+=("frontend")

  for teil in "${bauen[@]}"; do
    melde "Baue travelmind-$teil:$SHA"
    docker build -q -f "$teil/Dockerfile.prod" -t "travelmind-$teil:$SHA" "$teil/" >/dev/null
  done
  # Was nicht gebaut wurde, bekommt den neuen Tag auf den alten Inhalt —
  # sonst zeigt die Compose auf ein Image, das es nicht gibt.
  for teil in backend frontend; do
    if ! printf '%s\n' "${bauen[@]}" | grep -qx "$teil"; then
      alt="$(parameter_lesen)"
      docker tag "travelmind-$teil:$alt" "travelmind-$teil:$SHA"
    fi
  done

  melde "Uebertragen"
  docker save "travelmind-backend:$SHA" "travelmind-frontend:$SHA" | gzip -1 > "$ZWISCHEN/images.tgz"
  lokal_summe="$(sha256sum "$ZWISCHEN/images.tgz" | cut -c1-16)"
  ssh -o BatchMode=yes "$HOST" "cat > /tmp/travelmind-$SHA.tgz" < "$ZWISCHEN/images.tgz"
  fern_summe="$(fern "sha256sum /tmp/travelmind-$SHA.tgz | cut -c1-16")"
  [[ "$lokal_summe" == "$fern_summe" ]] || fehler "Pruefsumme nach der Uebertragung weicht ab ($lokal_summe != $fern_summe)."
  fern "gunzip -c /tmp/travelmind-$SHA.tgz | docker load >/dev/null && rm -f /tmp/travelmind-$SHA.tgz"

  melde "Compose und Parameter aktualisieren"
  # Erst wegraeumen, was dort liegt: legt ein `docker run -v` ein fehlendes
  # Ziel an, entsteht ein VERZEICHNIS mit diesem Namen — und scp scheitert
  # danach mit "Permission denied", was nach einem Rechteproblem aussieht.
  fern "rm -rf /tmp/tm-compose.yml /tmp/tm-skripte.tgz"
  scp -q -o BatchMode=yes docker-compose.prod.yml "$HOST:/tmp/tm-compose.yml"
  tar czf "$ZWISCHEN/skripte.tgz" -C deploy backup waechter
  scp -q -o BatchMode=yes "$ZWISCHEN/skripte.tgz" "$HOST:/tmp/tm-skripte.tgz"
  # WICHTIG: die beiden Skriptverzeichnisse werden GELEERT, nicht geloescht.
  #
  # `rm -rf /d/deploy/backup` entfernt das Verzeichnis, auf das die
  # Bind-Mounts der laufenden Container zeigen. Ein Bind-Mount haengt am
  # INODE: das neu angelegte Verzeichnis ist ein anderes, und der laufende
  # Container sieht danach ein LEERES /skripte. Am 2026-08-25 gemessen — die
  # taegliche Sicherung war seit dem ersten Ausrollen stillgelegt und haette
  # um 03:00 mit "no such file or directory" abgebrochen. Aufgefallen ist es
  # nur zufaellig, weil ein `docker exec` von Hand scheiterte.
  fern "docker run --rm -v $FERN:/d -v /tmp/tm-compose.yml:/in1:ro -v /tmp/tm-skripte.tgz:/in2:ro alpine:latest sh -c '
      set -e
      cp /in1 /d/docker-compose.prod.yml && chmod 644 /d/docker-compose.prod.yml
      mkdir -p /d/deploy/backup /d/deploy/waechter
      find /d/deploy/backup /d/deploy/waechter -mindepth 1 -delete
      tar xzf /in2 -C /d/deploy && chmod 755 /d/deploy/*/*.sh
  '"
  tag_setzen "$SHA"
  compose_auf "$NUR"

  # Sicherung und Waechter lesen ihre Skripte beim START. `compose up -d`
  # laesst sie unberuehrt, weil sich ihr Image nicht geaendert hat — sie
  # liefen also mit dem Stand von vorhin weiter. Deshalb ausdruecklich neu
  # starten, wenn die Skripte mitgegangen sind.
  if [[ -z "$NUR" ]]; then
    melde "Sicherung und Waechter neu starten (sie lesen ihre Skripte beim Start)"
    fern "docker restart travelmind-backup travelmind-waechter >/dev/null" || true
  fi
fi

# ── Prüfung ───────────────────────────────────────────────────────────────
melde "Warte auf gesunde Container"
for _ in $(seq 1 30); do
  ungesund="$(fern "docker ps --filter name=travelmind --format '{{.Names}} {{.Status}}' | grep -c -E 'starting|unhealthy'" || echo 0)"
  [[ "$ungesund" == "0" ]] && break
  sleep 5
done

melde "Zustand"
fern "docker ps --filter name=travelmind --format '  {{.Names}}  {{.Image}}  {{.Status}}'"

melde "Von aussen"
port="$(fern "docker run --rm -v $FERN:/d:ro alpine:latest grep '^TRAVELMIND_PORT=' /d/deploy-params.conf" 2>/dev/null | cut -d= -f2 | tr -d '\r\n')"
adresse="http://${HOST#*@}:${port:-8190}"
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$adresse/" || echo 000)"
gesund="$(curl -s --max-time 20 "$adresse/api/health" | head -c 200 || true)"
echo "  $adresse/            HTTP $code"
echo "  $adresse/api/health  $(echo "$gesund" | cut -c1-60)…"

[[ "$code" == "200" ]] || fehler "Die Oberflaeche antwortet nicht mit 200."
echo "$gesund" | grep -q '"status":"healthy"' || fehler "Die API meldet sich nicht als gesund."

melde "Fertig — ausgerollt und geprueft."
