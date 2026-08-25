#!/usr/bin/env bash
#
# Prueft die nginx-Konfiguration gegen die Eigenschaften, die am 2026-08-25
# in der Produktion falsch waren. Laeuft ohne Container: es wird die DATEI
# geprueft. Die Wirkung wird nach dem Ausrollen zusaetzlich gegen die
# laufende Instanz gemessen (siehe --live).
#
set -euo pipefail
CONF="$(dirname "${BASH_SOURCE[0]}")/nginx.conf"
fehler=0

pruefe() {
  local name="$1" muster="$2"
  if grep -qE "$muster" "$CONF"; then
    printf '  ok    %s\n' "$name"
  else
    printf '  FEHLT %s\n' "$name"; fehler=1
  fi
}

echo "nginx.conf:"
pruefe "Uploadgrenze gesetzt (sonst 1 MB, kein Handyfoto)"  '^\s*client_max_body_size\s+([2-9]|[1-9][0-9])m;'
pruefe "laeuft unprivilegiert auf 8080"                      '^\s*listen\s+8080;'
pruefe "Ratenbegrenzung fuer /api/"                          'limit_req_zone.*zone=api'
pruefe "strengere Grenze fuer /api/auth/"                    'limit_req_zone.*zone=auth'
pruefe "X-Forwarded-For wird weitergereicht"                 'proxy_set_header\s+X-Forwarded-For'
pruefe "SPA-Rueckfall auf index.html"                        'try_files.*index\.html'
pruefe "echte Client-IP hinter dem Proxy"                     'real_ip_header\s+X-Forwarded-For'
pruefe "Vertrauen nur fuer private Netze"                    'set_real_ip_from\s+192\.168\.0\.0/16'
pruefe "Protokoll zeigt die Weiterleitungskette"             'log_format\s+mit_proxy'

# Gegenkontrolle: kein OEFFENTLICHES Netz darf vertraut werden — sonst kann
# jeder von aussen seine Adresse faelschen und die Ratenbegrenzung umgehen.
if grep -E '^\s*set_real_ip_from' "$CONF" | grep -qvE '(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|127\.)'; then
  printf '  FEHLER  set_real_ip_from vertraut einem Netz ausserhalb von RFC 1918\n'; fehler=1
else
  printf '  ok    kein oeffentliches Netz in set_real_ip_from\n'
fi

# Gegenkontrolle: ein Muster, das NICHT zutreffen darf.
if grep -qE '^\s*user\s+' "$CONF"; then
  printf '  FEHLER  user-Direktiv vorhanden — das Image laeuft unprivilegiert\n'; fehler=1
else
  printf '  ok    kein user-Direktiv\n'
fi

if [[ "${1:-}" == "--live" ]]; then
  ZIEL="${2:?Adresse angeben, z.B. http://<host>:8190}"
  echo
  echo "gegen $ZIEL gemessen:"
  tmp="$(mktemp)"; head -c 2000000 /dev/urandom > "$tmp"
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 \
      -X POST -F "file=@$tmp;type=image/jpeg" "$ZIEL/api/diary/1/upload-photo")"
  rm -f "$tmp"
  if [[ "$code" == "413" ]]; then
    printf '  FEHLER  2 MB werden mit 413 abgewiesen — kein Handyfoto hochladbar\n'; fehler=1
  else
    printf '  ok    2 MB kommen bis zum Backend durch (HTTP %s, 401 = Anmeldung faellig)\n' "$code"
  fi
fi

exit $fehler
