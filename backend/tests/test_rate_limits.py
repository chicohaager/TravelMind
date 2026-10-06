"""
Wächter: jeder API-Endpunkt trägt eine Rate-Begrenzung.

Am 2026-08-25 gemessen: 51 von 123 Endpunkt-Funktionen hatten keine — darunter
das komplette Admin-Modul (13 von 14), Budget (7 von 7), Timeline (6 von 6),
Teilnehmer und Routen (je 5 von 5).

Die Grenzen selbst waren nicht das Problem: `utils/rate_limits.py` definiert
ADMIN_READ, ADMIN_WRITE, ADMIN_DELETE, BUDGET_READ, TIMELINE_READ und alles
Weitere seit jeher. Sie wurden nur nirgends angewandt. Dieselbe Form wie so
vieles in diesem Projekt: die Regel liegt da, sie wirkt nur nicht.

Dieser Test liest den Quelltext mit dem Python-Parser statt mit Textmustern —
ein Muster hätte die vier Funktionen übersehen, die zwei Pfade bedienen.
"""

import ast
from pathlib import Path

import pytest

ROUTES_VERZEICHNIS = Path(__file__).resolve().parent.parent / "routes"


def _endpunkte():
    """Alle Endpunkt-Funktionen mit ihrem Zustand: (Datei, Name, hat_grenze, hat_request)."""
    gefunden = []
    for datei in sorted(ROUTES_VERZEICHNIS.glob("*.py")):
        baum = ast.parse(datei.read_text(encoding="utf-8"))
        for knoten in baum.body:
            if not isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            ist_route = hat_grenze = False
            for dekorator in knoten.decorator_list:
                if not (isinstance(dekorator, ast.Call) and isinstance(dekorator.func, ast.Attribute)):
                    continue
                if not isinstance(dekorator.func.value, ast.Name):
                    continue
                if dekorator.func.value.id == "router":
                    ist_route = True
                if dekorator.func.value.id == "limiter":
                    hat_grenze = True
            if not ist_route:
                continue
            argumente = knoten.args
            hat_request = any(
                a.arg == "request"
                for a in list(argumente.posonlyargs) + list(argumente.args) + list(argumente.kwonlyargs)
            )
            gefunden.append((datei.name, knoten.name, hat_grenze, hat_request))
    return gefunden


ENDPUNKTE = _endpunkte()


def test_der_scanner_findet_ueberhaupt_endpunkte():
    """Positivkontrolle: ohne sie wäre ein leeres Ergebnis unten fälschlich grün."""
    assert len(ENDPUNKTE) > 100, f"nur {len(ENDPUNKTE)} Endpunkte gefunden — der Scanner greift nicht"


def test_jeder_endpunkt_hat_eine_rate_begrenzung():
    ohne = [f"{datei}::{name}" for datei, name, grenze, _ in ENDPUNKTE if not grenze]
    assert ohne == [], "Endpunkte ohne @limiter.limit:\n  " + "\n  ".join(ohne)


def test_jeder_begrenzte_endpunkt_hat_den_request_parameter():
    """
    slowapi liest die Client-Adresse aus dem Request. Fehlt der Parameter,
    bricht der Endpunkt zur LAUFZEIT — nicht beim Import. Ein Fehler, den
    weder Lint noch ein Startversuch findet.
    """
    fehlend = [f"{datei}::{name}" for datei, name, grenze, request in ENDPUNKTE if grenze and not request]
    assert fehlend == [], "begrenzte Endpunkte ohne `request: Request`:\n  " + "\n  ".join(fehlend)


@pytest.mark.parametrize("kunstfall", [("beispiel.py", "ohne_grenze", False, True)])
def test_positivkontrolle_ein_endpunkt_ohne_grenze_faellt_auf(kunstfall):
    """Belegt, dass die Prüfung oben überhaupt anschlagen kann."""
    ohne = [f"{d}::{n}" for d, n, g, _ in [kunstfall] if not g]
    assert ohne == ["beispiel.py::ohne_grenze"]
