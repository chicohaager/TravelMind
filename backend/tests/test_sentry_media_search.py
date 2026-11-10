"""
Wächter für drei kleinere Bereiche mit je einer teuren Lücke:

* **Sentry-Filter** (`utils/sentry.py`, vorher 29 %). `before_send_filter`
  entscheidet, was das Haus verlässt. Ein Fehler dort schickt fremde Server
  mit Zugangsdaten los — genau die Klasse Fehler, die niemand bemerkt, weil
  sie funktioniert.
* **Medien** (`routes/media.py`, 70 %) — die Galerie darf nur die eigenen
  Bilder zeigen.
* **Suche** (`routes/search.py`, 73 %) — eine Suche, die fremde Treffer
  liefert, ist ein Leck mit Komfortfunktion.
"""

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from utils import sentry

# ── Sentry-Filter ───────────────────────────────────────────────────────────


def test_ohne_DSN_wird_sentry_nicht_gestartet(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert sentry.init_sentry() is False


def test_zugangsdaten_werden_aus_den_kopfzeilen_entfernt():
    ereignis = {
        "request": {
            "headers": {
                "authorization": "Bearer ein-echtes-token",
                "cookie": "session=geheim",
                "x-api-key": "sk-geheim",
                "user-agent": "Firefox",
            }
        }
    }
    gefiltert = sentry.before_send_filter(ereignis, {})
    kopfzeilen = gefiltert["request"]["headers"]
    assert kopfzeilen["authorization"] == "[Filtered]"
    assert kopfzeilen["cookie"] == "[Filtered]"
    assert kopfzeilen["x-api-key"] == "[Filtered]"
    # Gegenkontrolle: Harmloses bleibt stehen, sonst ist der Bericht wertlos.
    assert kopfzeilen["user-agent"] == "Firefox"


def test_kein_wert_ueberlebt_das_filtern():
    """Die schärfere Formulierung derselben Zusicherung: nicht 'die drei
    Namen wurden ersetzt', sondern 'keiner der Geheimwerte steht noch
    irgendwo im Ereignis'."""
    geheim = "Bearer sehr-geheimes-token-1234567890"
    ereignis = {"request": {"headers": {"authorization": geheim}}}
    assert geheim not in repr(sentry.before_send_filter(ereignis, {}))


def test_client_fehler_werden_NICHT_verschickt():
    """Ein 404 ist kein Programmfehler. Ohne diesen Filter besteht der
    Fehlerbericht aus Tippfehlern in Adressen."""
    fehler = HTTPException(status_code=404, detail="Nicht gefunden")
    ereignis = {"exception": {"values": []}}
    assert sentry.before_send_filter(ereignis, {"exc_info": (HTTPException, fehler, None)}) is None


def test_server_fehler_werden_verschickt():
    """Die Gegenkontrolle — sonst filtert der Filter alles und niemand merkt
    es."""
    fehler = HTTPException(status_code=500, detail="Kaputt")
    ereignis = {"exception": {"values": []}}
    assert sentry.before_send_filter(ereignis, {"exc_info": (HTTPException, fehler, None)}) is not None


def test_echte_ausnahmen_werden_verschickt():
    fehler = ValueError("etwas ist wirklich kaputt")
    ereignis = {"exception": {"values": []}}
    assert sentry.before_send_filter(ereignis, {"exc_info": (ValueError, fehler, None)}) is not None


def test_ereignis_ohne_ausnahme_geht_unveraendert_durch():
    ereignis = {"message": "nur eine Meldung"}
    assert sentry.before_send_filter(ereignis, {}) == ereignis


def test_die_hilfsfunktionen_laufen_auch_ohne_sentry():
    """Sie werden im Betrieb aufgerufen, auch wenn kein DSN gesetzt ist. Eine
    Ausnahme hier würde einen funktionierenden Endpunkt zerlegen."""
    sentry.set_user_context(1, "testuser", "test@example.com")
    sentry.add_breadcrumb("etwas passierte", category="test")
    sentry.capture_message("eine Meldung", level="info", extra_feld="wert")
    sentry.capture_exception(ValueError("x"), extra_feld="wert")
    sentry.clear_user_context()


# ── Medien ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_leere_galerie(client: AsyncClient, auth_headers):
    antwort = await client.get("/api/media/gallery", headers=auth_headers)
    assert antwort.status_code == 200
    assert antwort.json() == []


@pytest.mark.asyncio
async def test_medien_einer_reise_ohne_bilder(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.get(f"/api/media/trip/{test_trip.id}", headers=auth_headers)
    assert antwort.status_code == 200
    assert antwort.json() == []


@pytest.mark.asyncio
async def test_fremde_reise_ohne_medien(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.get(f"/api/media/trip/{test_trip.id}", headers=other_auth_headers)
    assert antwort.status_code in (403, 404)


@pytest.mark.asyncio
async def test_galerie_ohne_anmeldung(client: AsyncClient):
    assert (await client.get("/api/media/gallery")).status_code == 401


@pytest.mark.asyncio
async def test_unbekanntes_medium_ergibt_404(client: AsyncClient, auth_headers):
    assert (await client.delete("/api/media/999999", headers=auth_headers)).status_code == 404


# ── Suche ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_suche_findet_die_eigene_reise(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.get("/api/search?q=Lissabon", headers=auth_headers)
    assert antwort.status_code == 200, antwort.text
    daten = antwort.json()
    assert daten["total"] >= 1
    assert any(test_trip.title in str(t) for t in daten["results"]), daten["results"]


@pytest.mark.asyncio
async def test_suche_findet_FREMDE_reisen_nicht(client: AsyncClient, other_auth_headers, test_trip):
    """Der wichtigste Test hier: eine Suche über alle Datensätze wäre ein
    bequemes Leseloch in fremde Konten."""
    daten = (await client.get("/api/search?q=Lissabon", headers=other_auth_headers)).json()
    assert daten["total"] == 0, daten["results"]


@pytest.mark.asyncio
async def test_suche_ohne_treffer(client: AsyncClient, auth_headers, test_trip):
    daten = (await client.get("/api/search?q=Kleinkleckersdorf", headers=auth_headers)).json()
    assert daten["total"] == 0


@pytest.mark.asyncio
async def test_suche_ohne_anmeldung(client: AsyncClient):
    assert (await client.get("/api/search?q=x")).status_code == 401
