"""
Wächter gegen eine ganze Fehlerklasse, gefunden am 2026-08-25.

`routes/data_export.py` deklarierte den Parameter als `request` OHNE
Typangabe. FastAPI kann daraus nicht ableiten, dass das Starlette-Objekt
gemeint ist, und macht daraus einen **Pflicht-Query-Parameter**. Folge: die
drei DSGVO-Endpunkte (Datenmitnahme nach Artikel 20, Löschantrag nach Artikel
17) antworteten auf JEDEN Aufruf mit 422. Sie haben nie funktioniert.

Auffallen konnte das nicht: der Import ist gültig, der Code lädt, die
Anwendung startet, `/docs` zeigt die Endpunkte an. Nur benutzt hat sie
offenbar nie jemand.

Dieser Wächter fragt nicht den Quelltext, sondern das **fertige
OpenAPI-Schema** — also das, was die Anwendung tatsächlich anbietet.
"""

import pytest
from main import app

VERDAECHTIGE_NAMEN = {"request", "req", "db", "session", "current_user", "background_tasks"}


def _alle_parameter():
    """Alle Query-/Path-Parameter aller Operationen aus dem erzeugten Schema."""
    schema = app.openapi()
    for pfad, operationen in schema.get("paths", {}).items():
        for methode, operation in operationen.items():
            if methode not in ("get", "post", "put", "patch", "delete"):
                continue
            for parameter in operation.get("parameters", []):
                yield pfad, methode, parameter


def test_das_schema_ist_ueberhaupt_erzeugbar():
    """Positivkontrolle: ohne diesen Fall wäre alles unten auch dann grün,
    wenn `app.openapi()` gar nichts lieferte."""
    schema = app.openapi()
    assert len(schema["paths"]) > 50, len(schema.get("paths", {}))


def test_es_gibt_ueberhaupt_parameter_zu_pruefen():
    """Zweite Positivkontrolle: der Scanner muss etwas sehen."""
    assert sum(1 for _ in _alle_parameter()) > 20


@pytest.mark.parametrize("name", sorted(VERDAECHTIGE_NAMEN))
def test_kein_infrastruktur_objekt_wird_zum_query_parameter(name):
    """`request`, `db` und Co. sind Abhängigkeiten des Endpunkts, keine
    Eingaben des Nutzers. Taucht so ein Name im Schema auf, fehlt die
    Typangabe — und der Endpunkt ist mit 422 tot."""
    treffer = [
        f"{methode.upper()} {pfad}" for pfad, methode, parameter in _alle_parameter() if parameter.get("name") == name
    ]
    assert treffer == [], f"'{name}' ist ein Query-Parameter geworden: {treffer}"


def test_jede_operation_hat_eine_beschreibung():
    """Kein Sicherheitsproblem, aber die Grundlage einer benutzbaren
    API-Dokumentation — und billig zu halten."""
    schema = app.openapi()
    ohne = [
        f"{methode.upper()} {pfad}"
        for pfad, operationen in schema["paths"].items()
        for methode, operation in operationen.items()
        if methode in ("get", "post", "put", "patch", "delete")
        and not (operation.get("summary") or operation.get("description"))
    ]
    assert ohne == [], f"{len(ohne)} Operationen ohne Beschreibung: {ohne[:10]}"
