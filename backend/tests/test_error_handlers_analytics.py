"""
Wächter für die Fehlerbehandlung (`utils/error_handlers.py`, vorher 50 %) und
die Auswertung (`routes/analytics.py`, 63 %).

Die Fehlerbehandlung ist die letzte Stelle, an der etwas das Haus verlässt.
Zwei Eigenschaften müssen dort gleichzeitig gelten, und sie ziehen in
verschiedene Richtungen:

* Der Nutzer bekommt eine **verständliche** Meldung mit einer Kennung, an der
  die Oberfläche sie unterscheiden kann — kein nacktes „Internal Server
  Error".
* Die Antwort verrät **nichts über das Innere**: kein SQL, keine Tabellen-
  oder Spaltennamen, kein Dateipfad, kein Stacktrace.

Beides wird hier geprüft, statt nur den Statuscode anzusehen.
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.requests import Request
from utils.error_handlers import (
    StandardError,
    general_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    standard_error_handler,
)


def _anfrage(pfad="/api/etwas"):
    return Request({"type": "http", "method": "GET", "path": pfad, "headers": [], "query_string": b""})


async def _inhalt(antwort):
    import json

    return json.loads(antwort.body)


# ── StandardError ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_standardfehler_behaelt_kennung_und_status():
    fehler = StandardError("Reise nicht gefunden", status_code=404, error_code="TRIP_NOT_FOUND", details={"id": 7})
    antwort = await standard_error_handler(_anfrage("/api/trips/7"), fehler)
    assert antwort.status_code == 404
    daten = await _inhalt(antwort)
    assert daten["error"] == "TRIP_NOT_FOUND"
    assert daten["message"] == "Reise nicht gefunden"
    assert daten["details"] == {"id": 7}
    assert daten["path"] == "/api/trips/7"


@pytest.mark.asyncio
async def test_standardfehler_hat_brauchbare_vorgaben():
    antwort = await standard_error_handler(_anfrage(), StandardError("Etwas ging schief"))
    assert antwort.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert (await _inhalt(antwort))["error"] == "INTERNAL_ERROR"


# ── Datenbankfehler ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_doppelter_eintrag_wird_zu_409():
    fehler = IntegrityError("INSERT …", {}, Exception("UNIQUE constraint failed: users.username"))
    antwort = await integrity_error_handler(_anfrage(), fehler)
    assert antwort.status_code == status.HTTP_409_CONFLICT
    assert (await _inhalt(antwort))["error"] == "DUPLICATE_ENTRY"


@pytest.mark.asyncio
async def test_postgres_formulierung_wird_genauso_erkannt():
    """SQLite sagt "UNIQUE constraint failed", PostgreSQL "duplicate key
    value". Die Tests laufen auf SQLite, die Produktion auf PostgreSQL — ohne
    diesen Fall wäre nur die Hälfte geprüft, die im Betrieb nie vorkommt."""
    fehler = IntegrityError("INSERT …", {}, Exception('duplicate key value violates unique constraint "users_pkey"'))
    antwort = await integrity_error_handler(_anfrage(), fehler)
    assert antwort.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_fehlender_verweis_wird_zu_400():
    fehler = IntegrityError("INSERT …", {}, Exception("FOREIGN KEY constraint failed"))
    antwort = await integrity_error_handler(_anfrage(), fehler)
    assert antwort.status_code == status.HTTP_400_BAD_REQUEST
    assert (await _inhalt(antwort))["error"] == "INVALID_REFERENCE"


@pytest.mark.asyncio
async def test_unbekannter_integritaetsfehler_bleibt_400():
    fehler = IntegrityError("INSERT …", {}, Exception("etwas ganz anderes"))
    antwort = await integrity_error_handler(_anfrage(), fehler)
    assert antwort.status_code == status.HTTP_400_BAD_REQUEST
    assert (await _inhalt(antwort))["error"] == "DATABASE_ERROR"


@pytest.mark.asyncio
async def test_die_antwort_verraet_KEINE_tabellen_oder_spalten():
    """Der eigentliche Zweck der Fehlerbehandlung. Eine durchgereichte
    SQL-Meldung ist eine Landkarte des Schemas."""
    roh = 'duplicate key value violates unique constraint "users_email_key" DETAIL: Key (email)=(a@b.de) exists.'
    antwort = await integrity_error_handler(_anfrage(), IntegrityError("INSERT …", {}, Exception(roh)))
    text = str(await _inhalt(antwort))
    for verraeterisch in ("users_email_key", "a@b.de", "DETAIL", "INSERT"):
        assert verraeterisch not in text, f"{verraeterisch!r} steht in der Antwort"


@pytest.mark.asyncio
async def test_allgemeiner_datenbankfehler_wird_zu_500():
    antwort = await sqlalchemy_error_handler(_anfrage(), SQLAlchemyError("Verbindung weg"))
    assert antwort.status_code == 500
    assert (await _inhalt(antwort))["error"] == "DATABASE_ERROR"
    assert "Verbindung weg" not in str(await _inhalt(antwort))


@pytest.mark.asyncio
async def test_unerwartete_ausnahme_wird_zu_500_ohne_innenansicht():
    antwort = await general_exception_handler(_anfrage(), ValueError("/home/jemand/geheim/pfad.py Zeile 42: kaputt"))
    assert antwort.status_code == 500
    daten = await _inhalt(antwort)
    assert daten["error"] == "INTERNAL_ERROR"
    assert "/home/jemand" not in str(daten)


# ── Über die echte Anwendung ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_eingabefehler_nennen_das_betroffene_feld(client: AsyncClient, auth_headers, test_trip):
    """Eine Fehlermeldung ohne Feldnamen zwingt den Nutzer zum Raten."""
    antwort = await client.post(
        f"/api/places/{test_trip.id}/places",
        headers=auth_headers,
        json={"name": "Ohne Koordinaten"},
    )
    assert antwort.status_code == 422
    daten = antwort.json()
    assert daten["error"] == "VALIDATION_ERROR"
    felder = {f["field"] for f in daten["details"]["validation_errors"]}
    assert "body.latitude" in felder and "body.longitude" in felder, felder


@pytest.mark.asyncio
async def test_doppelte_registrierung_meldet_sich_verstaendlich(client: AsyncClient, test_user):
    antwort = await client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "anders@example.com",
            "password": "ein-ziemlich-langes-und-eigenes-passwort",
        },
    )
    assert antwort.status_code in (400, 409)
    assert "hashed_password" not in antwort.text


# ── Auswertung ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auswertung_ohne_reisen(client: AsyncClient, auth_headers):
    daten = (await client.get("/api/analytics/summary", headers=auth_headers)).json()
    assert daten["trips"] == 0
    assert daten["total_spend"] == 0.0
    assert daten["primary_currency"] == "EUR"


@pytest.mark.asyncio
async def test_auswertung_zaehlt_reisetage_einschliesslich(client: AsyncClient, auth_headers, test_trip):
    """01.09. bis 08.09. sind ACHT Tage, nicht sieben: beide Randtage zählen.
    Ein Abzug von eins ist der wahrscheinlichste Fehler."""
    daten = (await client.get("/api/analytics/summary", headers=auth_headers)).json()
    assert daten["trips"] == 1
    assert daten["travel_days"] == 8, daten


@pytest.mark.asyncio
async def test_auswertung_summiert_ausgaben(client: AsyncClient, auth_headers, test_trip):
    for betrag, kategorie in ((20.0, "food"), (12.5, "food"), (7.5, "transport")):
        await client.post(
            f"/api/budget/{test_trip.id}/expenses",
            headers=auth_headers,
            json={"title": "Posten", "amount": betrag, "category": kategorie, "date": "2026-09-02"},
        )
    daten = (await client.get("/api/analytics/summary", headers=auth_headers)).json()
    assert daten["total_spend"] == pytest.approx(40.0)
    nach_kategorie = {e["category"]: e["amount"] for e in daten["spend_by_category"]}
    assert nach_kategorie["food"] == pytest.approx(32.5)


@pytest.mark.asyncio
async def test_auswertung_zeigt_KEINE_fremden_reisen(client: AsyncClient, other_auth_headers, test_trip):
    daten = (await client.get("/api/analytics/summary", headers=other_auth_headers)).json()
    assert daten["trips"] == 0


@pytest.mark.asyncio
async def test_auswertung_ohne_anmeldung(client: AsyncClient):
    assert (await client.get("/api/analytics/summary")).status_code == 401
