"""
Wächter für die Reise selbst (`routes/trips.py`, vorher 47 %).

Die Reise ist der Behälter für alles andere: Orte, Tagebuch, Ausgaben,
Routen, Medien. Zwei Eigenschaften sind deshalb hier wichtiger als anderswo:

* **Löschen räumt wirklich auf.** Bleiben Orte oder Einträge einer gelöschten
  Reise stehen, sammeln sie sich unsichtbar an — und tauchen bei der nächsten
  Auswertung als Geisterdaten wieder auf.
* **Niemand sieht fremde Reisen.** Weder in der Liste, noch einzeln, noch
  über die Zusammenfassung.
"""

import pytest
from httpx import AsyncClient
from models.diary import DiaryEntry
from models.place import Place
from models.trip import Trip
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

REISE = {
    "title": "Herbst in Porto",
    "destination": "Porto",
    "description": "Wein und Fluss",
    "start_date": "2026-10-01T00:00:00",
    "end_date": "2026-10-08T00:00:00",
    "budget": 900.0,
    "currency": "EUR",
    "interests": ["food", "culture"],
}


# ── Anlegen und Lesen ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reise_anlegen(client: AsyncClient, auth_headers):
    antwort = await client.post("/api/trips", headers=auth_headers, json=REISE)
    assert antwort.status_code == 201, antwort.text
    daten = antwort.json()
    assert daten["title"] == REISE["title"]
    assert daten["interests"] == ["food", "culture"]


@pytest.mark.asyncio
@pytest.mark.parametrize("datum", ["2026-10-01", "2026-10-01T00:00:00", "2026-10-01T00:00:00Z"])
async def test_datum_wird_in_allen_drei_schreibweisen_angenommen(client: AsyncClient, auth_headers, datum):
    """CLAUDE.md behauptete bis 2026-08-25, ein Datum ohne Uhrzeit werde
    abgewiesen. Gemessen an allen fünf Modellen mit Datumsfeld (Reise,
    Tagebuch, Ort, Zeitplanung, Ausgabe) stimmt das NICHT: Pydantic v2
    ergänzt Mitternacht. Die Behauptung ist korrigiert, und hier steht das
    gemessene Verhalten, damit es nicht wieder zur Erinnerung wird."""
    antwort = await client.post("/api/trips", headers=auth_headers, json={**REISE, "start_date": datum})
    assert antwort.status_code == 201, antwort.text
    assert antwort.json()["start_date"].startswith("2026-10-01T00:00:00")


@pytest.mark.asyncio
async def test_reise_ohne_titel_wird_abgewiesen(client: AsyncClient, auth_headers):
    antwort = await client.post("/api/trips", headers=auth_headers, json={"destination": "Porto"})
    assert antwort.status_code == 422


@pytest.mark.asyncio
async def test_eigene_reisen_auflisten(client: AsyncClient, auth_headers, test_trip):
    await client.post("/api/trips", headers=auth_headers, json=REISE)
    liste = (await client.get("/api/trips", headers=auth_headers)).json()
    titel = {t["title"] for t in liste}
    assert {test_trip.title, REISE["title"]} <= titel


@pytest.mark.asyncio
async def test_die_liste_zeigt_KEINE_fremden_reisen(client: AsyncClient, other_auth_headers, test_trip):
    liste = (await client.get("/api/trips", headers=other_auth_headers)).json()
    assert liste == []


@pytest.mark.asyncio
async def test_einzelne_reise_lesen(client: AsyncClient, auth_headers, test_trip):
    daten = (await client.get(f"/api/trips/{test_trip.id}", headers=auth_headers)).json()
    assert daten["id"] == test_trip.id
    assert daten["destination"] == test_trip.destination


@pytest.mark.asyncio
async def test_fremde_reise_ist_nicht_lesbar(client: AsyncClient, other_auth_headers, test_trip):
    assert (await client.get(f"/api/trips/{test_trip.id}", headers=other_auth_headers)).status_code == 403


@pytest.mark.asyncio
async def test_unbekannte_reise_ergibt_404(client: AsyncClient, auth_headers):
    assert (await client.get("/api/trips/999999", headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_seitenweises_auflisten(client: AsyncClient, auth_headers):
    for i in range(5):
        await client.post("/api/trips", headers=auth_headers, json={**REISE, "title": f"Reise {i}"})
    seite = (await client.get("/api/trips?skip=1&limit=2", headers=auth_headers)).json()
    assert len(seite) == 2


# ── Ändern ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reise_aendern_ist_ein_teilupdate(client: AsyncClient, auth_headers, test_trip):
    """Anders als bei den Orten: hier sind alle Felder optional. Wer nur den
    Titel schickt, darf das Reiseziel nicht verlieren."""
    antwort = await client.put(f"/api/trips/{test_trip.id}", headers=auth_headers, json={"title": "Neuer Titel"})
    assert antwort.status_code == 200, antwort.text
    daten = antwort.json()
    assert daten["title"] == "Neuer Titel"
    assert daten["destination"] == test_trip.destination


@pytest.mark.asyncio
async def test_fremder_aendert_keine_reise(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.put(f"/api/trips/{test_trip.id}", headers=other_auth_headers, json={"title": "Gekapert"})
    assert antwort.status_code == 403


@pytest.mark.asyncio
async def test_unbekannte_reise_aendern_ergibt_404(client: AsyncClient, auth_headers):
    assert (await client.put("/api/trips/999999", headers=auth_headers, json={"title": "X"})).status_code == 404


# ── Löschen ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reise_loeschen(client: AsyncClient, auth_headers, test_trip, db_session: AsyncSession):
    weg = await client.delete(f"/api/trips/{test_trip.id}", headers=auth_headers)
    assert weg.status_code == 204
    uebrig = (await db_session.execute(select(Trip).where(Trip.id == test_trip.id))).scalar_one_or_none()
    assert uebrig is None


@pytest.mark.asyncio
async def test_loeschen_raeumt_orte_und_tagebuch_mit_ab(
    client: AsyncClient, auth_headers, test_trip, test_place, db_session: AsyncSession
):
    """Hier ist die Kaskade RICHTIG: was zu einer gelöschten Reise gehört,
    hat ohne sie keine Bedeutung mehr. Anders als bei den Ortslisten, wo sie
    ein Datenverlust war."""
    await client.post(
        f"/api/diary/{test_trip.id}",
        headers=auth_headers,
        json={"title": "Tag 1", "content": "Text", "entry_date": "2026-09-01T10:00:00"},
    )
    vorher_orte = (await db_session.execute(select(func.count(Place.id)).where(Place.trip_id == test_trip.id))).scalar()
    vorher_eintraege = (
        await db_session.execute(select(func.count(DiaryEntry.id)).where(DiaryEntry.trip_id == test_trip.id))
    ).scalar()
    # Positivkontrolle: es gibt überhaupt etwas mit abzuräumen.
    assert vorher_orte == 1 and vorher_eintraege == 1

    assert (await client.delete(f"/api/trips/{test_trip.id}", headers=auth_headers)).status_code == 204

    nachher_orte = (
        await db_session.execute(select(func.count(Place.id)).where(Place.trip_id == test_trip.id))
    ).scalar()
    nachher_eintraege = (
        await db_session.execute(select(func.count(DiaryEntry.id)).where(DiaryEntry.trip_id == test_trip.id))
    ).scalar()
    assert nachher_orte == 0, "Orte der gelöschten Reise sind übrig geblieben"
    assert nachher_eintraege == 0, "Tagebucheinträge der gelöschten Reise sind übrig geblieben"


@pytest.mark.asyncio
async def test_fremder_loescht_keine_reise(
    client: AsyncClient, other_auth_headers, test_trip, db_session: AsyncSession
):
    antwort = await client.delete(f"/api/trips/{test_trip.id}", headers=other_auth_headers)
    assert antwort.status_code == 403
    uebrig = (await db_session.execute(select(Trip).where(Trip.id == test_trip.id))).scalar_one_or_none()
    assert uebrig is not None


@pytest.mark.asyncio
async def test_ohne_anmeldung_keine_reisen(client: AsyncClient, test_trip):
    assert (await client.get("/api/trips")).status_code == 401
    assert (await client.post("/api/trips", json=REISE)).status_code == 401
