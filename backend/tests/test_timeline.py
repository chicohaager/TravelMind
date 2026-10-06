"""
Wächter für die Zeitplanung (`routes/timeline.py`, vorher 34 % gedeckt).

Die Zeitplanung ist die einzige Stelle, an der die Entfernungsrechnung
(`calculate_distance`) und die Nächster-Nachbar-Optimierung laufen. Beides
liefert bei einem Fehler PLAUSIBLE Zahlen — eine falsche Reihenfolge sieht aus
wie eine Reihenfolge. Deshalb wird hier gegen bekannte Entfernungen geprüft
und nicht nur darauf, dass etwas zurückkommt.
"""

from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from models.place import Place
from routes.timeline import calculate_distance
from sqlalchemy.ext.asyncio import AsyncSession

# ── Entfernungsrechnung ─────────────────────────────────────────────────────


def test_gleicher_punkt_ergibt_null():
    assert calculate_distance(52.52, 13.405, 52.52, 13.405) == pytest.approx(0.0, abs=1e-9)


def test_berlin_hamburg_rund_255_km():
    """Bekannte Luftlinie. Eine Rechnung, die nur 'irgendeine Zahl' liefert,
    besteht diesen Test nicht."""
    d = calculate_distance(52.5200, 13.4050, 53.5511, 9.9937)
    assert 250 < d < 262, d


def test_ein_breitengrad_sind_rund_111_km():
    d = calculate_distance(0.0, 0.0, 1.0, 0.0)
    assert 110 < d < 112, d


def test_entfernung_ist_symmetrisch():
    a = calculate_distance(38.72, -9.14, 41.15, -8.61)
    b = calculate_distance(41.15, -8.61, 38.72, -9.14)
    assert a == pytest.approx(b)


def test_datumsgrenze_wird_kurz_gerechnet():
    """Gegenkontrolle gegen eine naive Differenzbildung: über die Datumsgrenze
    sind es 20 km, nicht der halbe Erdumfang."""
    d = calculate_distance(0.0, 179.9, 0.0, -179.9)
    assert d < 30, d


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def orte_am_tag(db_session: AsyncSession, test_trip):
    """Drei Orte am 2026-09-02, absichtlich in einer schlechten Reihenfolge:
    Lissabon → Porto → Lissabon-Vorort. Optimiert gehören die beiden
    Lissabonner nebeneinander."""
    daten = [
        ("Baixa", 38.7100, -9.1400, 0),
        ("Porto", 41.1500, -8.6100, 1),
        ("Belém", 38.6916, -9.2160, 2),
    ]
    orte = []
    for name, lat, lon, ordnung in daten:
        p = Place(
            name=name,
            latitude=lat,
            longitude=lon,
            trip_id=test_trip.id,
            visit_date=datetime(2026, 9, 2),
            order=ordnung,
        )
        db_session.add(p)
        orte.append(p)
    await db_session.commit()
    for p in orte:
        await db_session.refresh(p)
    return orte


# ── Endpunkte ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_leere_zeitplanung(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.get(f"/api/timeline/{test_trip.id}/timeline", headers=auth_headers)
    assert antwort.status_code == 200
    assert antwort.json() == []


@pytest.mark.asyncio
async def test_ohne_anmeldung_kein_zugriff(client: AsyncClient, test_trip):
    assert (await client.get(f"/api/timeline/{test_trip.id}/timeline")).status_code == 401


@pytest.mark.asyncio
async def test_fremde_reise_wird_abgewiesen(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.get(f"/api/timeline/{test_trip.id}/timeline", headers=other_auth_headers)
    assert antwort.status_code == 403


@pytest.mark.asyncio
async def test_ort_in_die_planung_aufnehmen(client: AsyncClient, auth_headers, test_trip, test_place):
    antwort = await client.post(
        f"/api/timeline/{test_trip.id}/timeline",
        headers=auth_headers,
        json={"place_id": test_place.id, "day_date": "2026-09-03", "notes": "vormittags"},
    )
    assert antwort.status_code == 201, antwort.text
    daten = antwort.json()
    assert daten["place_id"] == test_place.id
    assert daten["day_date"] == "2026-09-03"
    assert daten["notes"] == "vormittags"


@pytest.mark.asyncio
async def test_aufgenommener_ort_taucht_in_der_tagesliste_auf(client: AsyncClient, auth_headers, test_trip, test_place):
    await client.post(
        f"/api/timeline/{test_trip.id}/timeline",
        headers=auth_headers,
        json={"place_id": test_place.id, "day_date": "2026-09-03"},
    )
    tage = (await client.get(f"/api/timeline/{test_trip.id}/timeline", headers=auth_headers)).json()
    assert len(tage) == 1
    assert tage[0]["day_date"] == "2026-09-03"
    assert [e["place_name"] for e in tage[0]["entries"]] == [test_place.name]


@pytest.mark.asyncio
async def test_unbekannter_ort_ergibt_404(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.post(
        f"/api/timeline/{test_trip.id}/timeline",
        headers=auth_headers,
        json={"place_id": 999999, "day_date": "2026-09-03"},
    )
    assert antwort.status_code == 404


@pytest.mark.asyncio
async def test_ort_einer_fremden_reise_ergibt_404(client: AsyncClient, auth_headers, test_trip, db_session, test_user):
    from models.trip import Trip

    andere = Trip(title="Andere", destination="Porto", owner_id=test_user.id)
    db_session.add(andere)
    await db_session.commit()
    await db_session.refresh(andere)
    fremder_ort = Place(name="Fremd", latitude=1.0, longitude=1.0, trip_id=andere.id)
    db_session.add(fremder_ort)
    await db_session.commit()
    await db_session.refresh(fremder_ort)

    antwort = await client.post(
        f"/api/timeline/{test_trip.id}/timeline",
        headers=auth_headers,
        json={"place_id": fremder_ort.id, "day_date": "2026-09-03"},
    )
    assert antwort.status_code == 404


@pytest.mark.asyncio
async def test_fremder_darf_nichts_aufnehmen(client: AsyncClient, other_auth_headers, test_trip, test_place):
    antwort = await client.post(
        f"/api/timeline/{test_trip.id}/timeline",
        headers=other_auth_headers,
        json={"place_id": test_place.id, "day_date": "2026-09-03"},
    )
    assert antwort.status_code == 403


@pytest.mark.asyncio
async def test_aus_der_planung_entfernen(client: AsyncClient, auth_headers, test_trip, test_place):
    await client.post(
        f"/api/timeline/{test_trip.id}/timeline",
        headers=auth_headers,
        json={"place_id": test_place.id, "day_date": "2026-09-03"},
    )
    weg = await client.delete(f"/api/timeline/{test_trip.id}/timeline/{test_place.id}", headers=auth_headers)
    assert weg.status_code == 200
    assert (await client.get(f"/api/timeline/{test_trip.id}/timeline", headers=auth_headers)).json() == []


@pytest.mark.asyncio
async def test_eintrag_verschieben(client: AsyncClient, auth_headers, test_trip, test_place):
    await client.post(
        f"/api/timeline/{test_trip.id}/timeline",
        headers=auth_headers,
        json={"place_id": test_place.id, "day_date": "2026-09-03"},
    )
    antwort = await client.put(
        f"/api/timeline/{test_trip.id}/timeline/{test_place.id}",
        headers=auth_headers,
        json={"visit_date": "2026-09-05", "notes": "verschoben"},
    )
    assert antwort.status_code == 200, antwort.text
    tage = (await client.get(f"/api/timeline/{test_trip.id}/timeline", headers=auth_headers)).json()
    assert tage[0]["day_date"] == "2026-09-05"


@pytest.mark.asyncio
async def test_reihenfolge_von_hand_setzen(client: AsyncClient, auth_headers, test_trip, orte_am_tag):
    ids = [o.id for o in orte_am_tag]
    umgedreht = list(reversed(ids))
    antwort = await client.post(f"/api/timeline/{test_trip.id}/timeline/reorder", headers=auth_headers, json=umgedreht)
    assert antwort.status_code == 200
    tage = (await client.get(f"/api/timeline/{test_trip.id}/timeline", headers=auth_headers)).json()
    assert [e["place_id"] for e in tage[0]["entries"]] == umgedreht


@pytest.mark.asyncio
async def test_optimieren_stellt_die_nahen_orte_zusammen(client: AsyncClient, auth_headers, test_trip, orte_am_tag):
    """Der eigentliche Zweck: Baixa und Belém liegen 5 km auseinander, Porto
    275 km entfernt. Nach dem Optimieren darf Porto nicht mehr zwischen den
    beiden stehen."""
    antwort = await client.post(
        f"/api/timeline/{test_trip.id}/timeline/optimize?day_date=2026-09-02", headers=auth_headers
    )
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["reordered_count"] == 3

    tage = (await client.get(f"/api/timeline/{test_trip.id}/timeline", headers=auth_headers)).json()
    namen = [e["place_name"] for e in tage[0]["entries"]]
    assert namen.index("Porto") != 1, f"Porto steht weiterhin in der Mitte: {namen}"


@pytest.mark.asyncio
async def test_optimieren_bei_einem_einzigen_ort(client: AsyncClient, auth_headers, test_trip, test_place):
    await client.post(
        f"/api/timeline/{test_trip.id}/timeline",
        headers=auth_headers,
        json={"place_id": test_place.id, "day_date": "2026-09-03"},
    )
    antwort = await client.post(
        f"/api/timeline/{test_trip.id}/timeline/optimize?day_date=2026-09-03", headers=auth_headers
    )
    assert antwort.status_code == 200
    assert antwort.json()["success"] is True


@pytest.mark.asyncio
async def test_unbekannte_reise_ergibt_404(client: AsyncClient, auth_headers):
    antwort = await client.get("/api/timeline/999999/timeline", headers=auth_headers)
    assert antwort.status_code == 404
