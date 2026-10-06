"""
Wächter für die Bildersuche (`services/pexels_service.py`, vorher 18 %) und
die Benachrichtigungen (`routes/notifications.py`, 79 %).

Die Bildersuche hat einen **Rückfall auf ein Platzhalterbild**. Das ist der
gefährlichste Zweig des Moduls: fehlt der API-Schlüssel, ist das Netz weg
oder antwortet Pexels mit einem Fehler, bekommt der Nutzer trotzdem ein
hübsches Bild — und niemand merkt jemals, dass die Bildersuche seit Wochen
nicht läuft. Der Rückfall wird deshalb hier festgenagelt: er MUSS erkennbar
sein (picsum-Adresse) und er muss für denselben Ort denselben Wert liefern,
sonst wechselt das Bild bei jedem Seitenaufruf.

Kein Test geht ins Netz.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from models.notification import Notification
from services import pexels_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ── Bildersuche ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ohne_schluessel_wird_nicht_gesucht(monkeypatch):
    monkeypatch.setattr(pexels_service, "PEXELS_API_KEY", None)
    assert await pexels_service.search_photo("Lissabon") is None


@pytest.mark.asyncio
async def test_platzhalter_ist_als_solcher_erkennbar(monkeypatch):
    """Ohne dieses Merkmal ist von außen nicht zu unterscheiden, ob die
    Bildersuche läuft oder seit Wochen ausgefallen ist."""

    async def nichts(query, per_page=1):
        return None

    monkeypatch.setattr(pexels_service, "search_photo", nichts)
    url = await pexels_service.get_place_photo("Torre de Belém", "attraction", "Lissabon")
    assert "picsum.photos" in url, url


@pytest.mark.asyncio
async def test_der_platzhalter_bleibt_fuer_denselben_ort_gleich(monkeypatch):
    """Ein zufälliges Platzhalterbild wechselte bei jedem Seitenaufruf — das
    sieht aus wie ein Fehler in der Oberfläche."""

    async def nichts(query, per_page=1):
        return None

    monkeypatch.setattr(pexels_service, "search_photo", nichts)
    erst = await pexels_service.get_place_photo("Torre de Belém", "attraction", "Lissabon")
    wieder = await pexels_service.get_place_photo("Torre de Belém", "attraction", "Lissabon")
    assert erst == wieder


@pytest.mark.asyncio
async def test_verschiedene_orte_bekommen_verschiedene_platzhalter(monkeypatch):
    """Gegenkontrolle: sonst wäre der Test darüber auch von einer Konstante
    erfüllt."""

    async def nichts(query, per_page=1):
        return None

    monkeypatch.setattr(pexels_service, "search_photo", nichts)
    a = await pexels_service.get_place_photo("Torre de Belém", "attraction", "Lissabon")
    b = await pexels_service.get_place_photo("Time Out Market", "restaurant", "Lissabon")
    assert a != b


@pytest.mark.asyncio
async def test_ein_treffer_wird_sofort_genommen(monkeypatch):
    gefragt = []

    async def einmal(query, per_page=1):
        gefragt.append(query)
        return "https://images.pexels.com/foto.jpg"

    monkeypatch.setattr(pexels_service, "search_photo", einmal)
    url = await pexels_service.get_place_photo("Torre de Belém", "attraction", "Lissabon")
    assert url == "https://images.pexels.com/foto.jpg"
    assert len(gefragt) == 1, gefragt


@pytest.mark.asyncio
async def test_ein_ortsname_wird_mit_dem_ziel_gesucht(monkeypatch):
    gefragt = []

    async def merken(query, per_page=1):
        gefragt.append(query)
        return None

    monkeypatch.setattr(pexels_service, "search_photo", merken)
    await pexels_service.get_place_photo("Torre de Belém", "attraction", "Lissabon")
    assert gefragt[0] == "Torre de Belém Lissabon"


@pytest.mark.asyncio
async def test_ein_fertiger_suchbegriff_wird_NICHT_verlaengert(monkeypatch):
    """Kommt der Begriff von der KI ("la palma beach sunset"), ist er bereits
    eine Suchanfrage. Ihn noch einmal mit dem Ziel zu verlängern verschlechtert
    das Ergebnis."""
    gefragt = []

    async def merken(query, per_page=1):
        gefragt.append(query)
        return None

    monkeypatch.setattr(pexels_service, "search_photo", merken)
    await pexels_service.get_place_photo("la palma beach sunset", "beach", "La Palma")
    assert gefragt[0] == "la palma beach sunset"


@pytest.mark.asyncio
async def test_zuletzt_wird_ueber_die_kategorie_gesucht(monkeypatch):
    gefragt = []

    async def merken(query, per_page=1):
        gefragt.append(query)
        return None

    monkeypatch.setattr(pexels_service, "search_photo", merken)
    await pexels_service.get_place_photo("Ein Ort", "beach", "La Palma")
    assert gefragt[-1] == "La Palma beach ocean coastline", gefragt


@pytest.mark.asyncio
async def test_unbekannte_kategorie_faellt_auf_travel_zurueck(monkeypatch):
    gefragt = []

    async def merken(query, per_page=1):
        gefragt.append(query)
        return None

    monkeypatch.setattr(pexels_service, "search_photo", merken)
    await pexels_service.get_place_photo("Ein Ort", "gibtesnicht", "La Palma")
    assert gefragt[-1] == "La Palma travel"


# ── Benachrichtigungen ──────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def drei_meldungen(db_session: AsyncSession, test_user, test_trip):
    meldungen = []
    for i in range(3):
        n = Notification(
            user_id=test_user.id,
            type="trip_invitation",
            trip_id=test_trip.id,
            actor_name="Jemand",
            trip_title=test_trip.title,
            is_read=False,
        )
        db_session.add(n)
        meldungen.append(n)
    await db_session.commit()
    for n in meldungen:
        await db_session.refresh(n)
    return meldungen


@pytest.mark.asyncio
async def test_ohne_meldungen_ist_die_liste_leer(client: AsyncClient, auth_headers):
    assert (await client.get("/api/notifications", headers=auth_headers)).json() == []
    assert (await client.get("/api/notifications/unread-count", headers=auth_headers)).json()["count"] == 0


@pytest.mark.asyncio
async def test_meldungen_werden_gezaehlt(client: AsyncClient, auth_headers, drei_meldungen):
    assert (await client.get("/api/notifications/unread-count", headers=auth_headers)).json()["count"] == 3


@pytest.mark.asyncio
async def test_einzelne_meldung_als_gelesen_markieren(client: AsyncClient, auth_headers, drei_meldungen):
    antwort = await client.patch(f"/api/notifications/{drei_meldungen[0].id}/read", headers=auth_headers)
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["is_read"] is True
    assert (await client.get("/api/notifications/unread-count", headers=auth_headers)).json()["count"] == 2


@pytest.mark.asyncio
async def test_alle_als_gelesen_markieren(client: AsyncClient, auth_headers, drei_meldungen):
    antwort = await client.post("/api/notifications/read-all", headers=auth_headers)
    assert antwort.status_code == 200, antwort.text
    assert (await client.get("/api/notifications/unread-count", headers=auth_headers)).json()["count"] == 0


@pytest.mark.asyncio
async def test_fremde_meldungen_sind_unsichtbar(client: AsyncClient, other_auth_headers, drei_meldungen):
    assert (await client.get("/api/notifications", headers=other_auth_headers)).json() == []
    assert (await client.get("/api/notifications/unread-count", headers=other_auth_headers)).json()["count"] == 0


@pytest.mark.asyncio
async def test_fremde_meldung_laesst_sich_nicht_markieren(
    client: AsyncClient, other_auth_headers, drei_meldungen, db_session: AsyncSession
):
    antwort = await client.patch(f"/api/notifications/{drei_meldungen[0].id}/read", headers=other_auth_headers)
    assert antwort.status_code in (403, 404)
    gelesen = (
        await db_session.execute(select(Notification.is_read).where(Notification.id == drei_meldungen[0].id))
    ).scalar_one()
    assert gelesen is False


@pytest.mark.asyncio
async def test_unbekannte_meldung_ergibt_404(client: AsyncClient, auth_headers):
    assert (await client.patch("/api/notifications/999999/read", headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_meldungen_ohne_anmeldung(client: AsyncClient):
    assert (await client.get("/api/notifications")).status_code == 401
