#!/usr/bin/env python3
"""
Waechter: keine privaten Daten in getrackten Dateien.

Dieses Repo ist OEFFENTLICH (github.com/chicohaager/TravelMind). Am 2026-08-26
stand in `deploy/ausrollen.sh` der Vorgabewert `<benutzer>@<lan-ip>` — also
Kontoname und Host in einer Zeile, fuer jeden lesbar, waehrend die Instanz
oeffentlich erreichbar gemacht wurde.

`detect-secrets` (schon im pre-commit) hat es nicht gefunden und konnte es
nicht: es sucht Schluessel nach Entropie. Ein Benutzername und eine
LAN-Adresse haben keine Entropie — sie sind trotzdem die halbe Anmeldung.

Der Waechter prueft die ANDERE Haelfte: private Identifikatoren.

    python3 scripts/keine-privaten-daten.py            # getrackte Dateien
    python3 scripts/keine-privaten-daten.py --selbsttest  # kann er rot werden?
"""
import pathlib
import re
import subprocess
import sys

# Jedes Muster hat einen Positivkontrollfall in SELBSTTEST_SPERRT — ein
# Waechter ohne bewiesene Rotfaerbung ist eine Zusicherung ohne Pruefung.
MUSTER = [
    ("LAN-Adresse", re.compile(
        r"\b(?:192\.168\.\d{1,3}\.\d{1,3}"
        r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")),
    ("Tailscale-Adresse", re.compile(
        r"\b100\.(?:[6-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")),
    # `leaflet@1.9.4` und `travelmind-frontend@1.0.0` sind Paketbezeichner,
    # keine Adressen — der Teil hinter dem @ muss wie eine Domain aussehen.
    ("echte E-Mail", re.compile(
        r"[\w.+-]{3,}@(?!\d+\.\d)[\w-]{3,}\.[a-z]{2,}\b", re.I)),
    # Nur die KONFIGURATIONS-Form mit festgeschriebenem Wert. `password:
    # e.target.value` in einer Komponente gibt nichts preis — der Wert steht
    # dort nicht. Ein Muster, das beides trifft, faerbt taeglich falsch rot
    # und wird dann weggeklickt; danach schuetzt es auch dort nicht mehr, wo
    # es recht haette (2026-08-09 belegt).
    ("Passwort-Zuweisung", re.compile(
        r"(?m)^[^\n#]{0,40}?(?<![\w.-])"
        r"(?:[A-Z][A-Z0-9_]*_)?(?:PASS(?:WOR[DT])?|PASSWD|PWD|SECRET|TOKEN|API[_-]?KEY)"
        r"(?:_[A-Z0-9_]+)?\s*[:=]\s*"
        r"[\"']?(?![\w.]*\.(?:value|env|target)\b)"
        r"(?=[A-Za-z0-9!@#%^&*_+./-]{8,}[\"']?\s*$)"
        r"[A-Za-z0-9!@#%^&*_+./-]*[0-9!@#%^&*+][A-Za-z0-9!@#%^&*_+./-]*[\"']?\s*$")),
    ("Anbieter-Schluessel", re.compile(
        r"\b(?:sk-ant-[\w-]{20,}|sk-[A-Za-z0-9]{32,}|gsk_[A-Za-z0-9]{40,}"
        r"|AIza[\w-]{35}|ghp_[A-Za-z0-9]{36}|AKIA[0-9A-Z]{16})\b")),
    ("privater Schluessel", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# Freistellungen sind ENGER als die Regel: nur nachweislich Unschaedliches.
# Eine Ausnahme so breit wie das Muster loescht das Muster (2026-07-30 belegt).
HARMLOS = re.compile(
    r"\$\{?[A-Z_]{2,}\}?"                                  # ${VAR} / $VAR
    r"|<[a-z][\w-]*>"                                      # <host>, <benutzer>
    r"|\b(?:example|beispiel|dummy|placeholder|test|fake|optional)\b"
    r"|\b(?:chang|your|dein|my|our)[-_e]*(?:this|me|it|here)?\b"      # your-…-change-this
    r"|x{3,}"                                                     # xxx-Platzhalter
    r"|@[\w-]+\.local\b"                                          # admin@…​.local
    r"|\b(?:127\.0\.0\.1|0\.0\.0\.0|localhost)\b"
    r"|\b(?:203\.0\.113|192\.0\.2|198\.51\.100)\."         # RFC 5737
    r"|\d{1,3}(?:\.\d{1,3}){3}/\d{1,2}"                     # CIDR = Netzbereich
    r"|@(?:example|ejemplo|exemple|esempio|beispiel|test|domain|email|"
    r"your\w*|dein\w*|mail)\.[a-z]{2,}"                     # Platzhalter, 4 Sprachen
    r"|@(?:test|localhost)\b",
    re.I)

# Dateien, die per Konstruktion Muster ENTHALTEN muessen: der Waechter selbst
# und seine Faelle. Je Pfad benannt, nie als Glob ueber ein Verzeichnis.
AUSNAHMEN = {"scripts/keine-privaten-daten.py"}

# Konkrete private Werte — Betreibername, eigene Domain, feste Adressen —
# stehen NICHT hier: ein Waechter, der die gesuchten Werte im Klartext
# mitliefert, veroeffentlicht genau das, was er schuetzen soll. Am 2026-08-26
# standen in diesem Selbsttest eine echte Tailscale-Adresse und eine echte
# Domain, weil ich echte Werte als Testdaten uebernommen hatte.
#
# Format je Zeile:  <regex>  TAB  <probetext>
# Der Probetext ist die Positivkontrolle: der Selbsttest prueft, dass das
# Muster gegen ihn anschlaegt, und druckt dabei weder Muster noch Probe. Ohne
# Probetext wird das Muster geladen, im Selbsttest aber als UNGEPRUEFT
# gemeldet — nicht als gruen. Zeilen mit `#` sind Kommentare.
#
# Ohne die Datei prueft der Waechter nur die generischen Muster darueber —
# die wirken auch in CI, wo es diese Datei nicht gibt.
PRIVATLISTE = pathlib.Path(__file__).resolve().parent / "private-werte.txt"


def private_muster():
    if not PRIVATLISTE.is_file():
        return []
    zeilen = PRIVATLISTE.read_text(encoding="utf-8").splitlines()
    muster = []
    for nr, z in enumerate(zeilen, 1):
        z = z.strip()
        if not z or z.startswith("#"):
            continue
        regex, _, probe = z.partition("\t")
        try:
            muster.append((f"privater Wert #{nr}", re.compile(regex.strip(), re.I),
                           probe.strip()))
        except re.error as fehler:
            print(f"! {PRIVATLISTE.name}:{nr} ist kein gueltiger Regex: {fehler}")
    return muster


PRIVAT = private_muster()


MUSTER += [(n, rx) for n, rx, _ in PRIVAT]

SELBSTTEST_SPERRT = [
    ("HOST=benutzer@<host>", "LAN-Adresse"),
    ("ssh admin@100.101.102.103", "Tailscale-Adresse"),
    ("mailto:vorname.name@firma.de", "echte E-Mail"),
    ("POSTGRES_PASSWORD=Tr4vel!Mind2026", "Passwort-Zuweisung"),
    ("SECRET_KEY=9f3ac7be21d04e5fa8c6b1", "Passwort-Zuweisung"),
    ("    PUSHOVER_TOKEN: aq7x2mn4kd8vb3wr6ty9pl5sz1cf0h", "Passwort-Zuweisung"),
    ("export DB_PASSWORD=Sommer2026!Reise", "Passwort-Zuweisung"),
    ("ANTHROPIC_API_KEY=sk-ant-api03-" + "A" * 40, "Anbieter-Schluessel"),
    ("-----BEGIN OPENSSH PRIVATE KEY-----", "privater Schluessel"),
]
SELBSTTEST_LAESST_DURCH = [
    'HOST="${TRAVELMIND_HOST:-}"',
    "z.B. http://<host>:8190",
    "set_real_ip_from 192.168.0.0/16;",
    "proxy_pass http://127.0.0.1:8000;",
    "user@example.com",
    "password: changeme",
    "login('testnutzer', 'geheim')",
    # Die 62 Fehlalarme vom 2026-08-26 — je Form ein Fall, damit eine
    # Verengung nicht spaeter still zurueckgedreht wird.
    "  onChange={(e) => setNewUserData({ ...newUserData, password: e.target.value })}",
    "    new_password: passwordForm.new_password,",
    "  const passwordInput = page.getByLabel(/password|passwort/i);",
    "Passwoerter: mindestens 8 Zeichen, keine Komplexitaetspruefung.",
    "# Anmeldung und Passwort-Zuruecksetzung: strengere Zone (1 r/s, burst 5).",
    "set_real_ip_from 10.0.0.0/8;",
    '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">',
    "const release = import.meta.env.VITE_SENTRY_RELEASE || 'travelmind-frontend@1.0.0'",
    '  "emailPlaceholder": "usuario@ejemplo.com",',
    '  "emailPlaceholder": "votre.email@exemple.com",',
    "JWT_SECRET=your-super-secret-jwt-key-change-this-in-production",
    "MAPBOX_ACCESS_TOKEN=your-mapbox-token-optional",
    "PASSWORD_BREACH_CHECK=best-effort",
    "# SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx",
    'email = input("Enter email (default: admin@travelmind.local): ")',
    '    email="demo@travelmind.local",',
    "roh = '... Key (email)=(a@b.de) exists.'",
    "  \"deprecated\": \"Support may be purchased from x@yz.me\"",
    'NEUES_PASSWORT = "ein-neues-und-ziemlich-eigenes-passwort"',
]


def treffer_in(zeile):
    """
    Eine Freistellung gilt nur, wenn sie den TREFFER ueberlappt — nicht, wenn
    sie irgendwo in seiner Naehe steht.

    Vorher wurde ein 30-Zeichen-Umfeld geprueft. Damit entschuldigte das
    `${VAR}`-Muster die Zeile

        HOST="${TRAVELMIND_HOST:-<benutzer>@<lan-ip>}"

    vollstaendig: die Ausnahme war so breit wie die Regel und loeschte sie.
    Der Waechter meldete gruen, obwohl genau dieses Leck in der Datei stand —
    gefunden hat es erst die Sabotage-Gegenprobe, nicht der Selbsttest.
    """
    frei = [(m.start(), m.end()) for m in HARMLOS.finditer(zeile)]
    gefunden = set()
    for name, rx in MUSTER:
        for m in rx.finditer(zeile):
            if any(a < m.end() and m.start() < b for a, b in frei):
                continue
            gefunden.add(name)
    return gefunden


def selbsttest():
    fehler = 0
    for text, erwartet in SELBSTTEST_SPERRT:
        g = treffer_in(text)
        ok = erwartet in g
        fehler += 0 if ok else 1
        print(f"  {'OK   ' if ok else 'BLIND'} {erwartet:22s} <- {text[:46]}")
    print("  --- muessen durchgehen ---")
    for text in SELBSTTEST_LAESST_DURCH:
        g = treffer_in(text)
        ok = not g
        fehler += 0 if ok else 1
        print(f"  {'OK   ' if ok else 'FALSCH'} {str(sorted(g)):24s} <- {text[:46]}")
    if PRIVAT:
        print(f"  --- {len(PRIVAT)} private Muster aus {PRIVATLISTE.name} ---")
        for name, rx, probe in PRIVAT:
            # Weder Muster noch Probe werden gedruckt.
            if not probe:
                print(f"  OFFEN {name}: kein Probetext — UNGEPRUEFT")
                fehler += 1
                continue
            ok = bool(rx.search(probe)) and bool(treffer_in(probe))
            print(f"  {'OK   ' if ok else 'BLIND'} {name}")
            fehler += 0 if ok else 1
    else:
        print(f"  --- keine {PRIVATLISTE.name}: nur generische Muster aktiv ---")
    n = len(SELBSTTEST_SPERRT) + len(SELBSTTEST_LAESST_DURCH)
    print(f"\n{n} Faelle, {fehler} Fehler")
    return 1 if fehler else 0


def pruefe(dateien):
    befunde = []
    for pfad in dateien:
        if pfad in AUSNAHMEN:
            continue
        try:
            with open(pfad, encoding="utf-8", errors="strict") as f:
                for nr, zeile in enumerate(f, 1):
                    for name in treffer_in(zeile):
                        befunde.append((pfad, nr, name, zeile.strip()[:110]))
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue  # Binaerdatei oder geloescht — nicht Gegenstand dieser Pruefung
    for pfad, nr, name, zeile in befunde:
        print(f"✗ {pfad}:{nr}  [{name}]\n    {zeile}")
    if befunde:
        print(f"\n{len(befunde)} private Angabe(n) in getrackten Dateien. "
              f"Dieses Repo ist oeffentlich.")
        return 1
    print(f"✓ {len(dateien)} getrackte Dateien, keine privaten Angaben.")
    return 0


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        sys.exit(selbsttest())
    argumente = [a for a in sys.argv[1:] if not a.startswith("-")]
    if argumente:
        dateien = argumente
    else:
        dateien = subprocess.run(["git", "ls-files"], capture_output=True,
                                 text=True, check=True).stdout.split("\n")
        dateien = [d for d in dateien if d]
    sys.exit(pruefe(dateien))
