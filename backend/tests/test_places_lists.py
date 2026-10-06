"""
Wächter für Orte und Ortslisten (`routes/places.py`, vorher 40 % gedeckt).

`places.py` ist mit 425 Anweisungen das größte Routenmodul und hält die Daten,
die ein Nutzer von Hand eingegeben hat. Die Zugriffsprüfungen sind hier
besonders wichtig: die Änderungs- und Löschendpunkte adressieren einen Ort
über SEINE ID, nicht über die Reise — eine fehlende Prüfung ist damit direkt
eine fremde Reise, die sich bearbeiten lässt (IDOR).
"""

import pytest
from httpx import AsyncClient
from models.place import Place
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ORT = {
    "name": "Castelo de São Jorge",
    "description": "Historische Burg",
    "latitude": 38.7139,
    "longitude": -9.1334,
    "category": "sight",
}


# ── Orte ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_neue_reise_hat_keine_orte(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.get(f"/api/places/{test_trip.id}/places", headers=auth_headers)
    assert antwort.status_code == 200
    assert antwort.json() == []


@pytest.mark.asyncio
async def test_ort_anlegen(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.post(f"/api/places/{test_trip.id}/places", headers=auth_headers, json=ORT)
    assert antwort.status_code == 201, antwort.text
    daten = antwort.json()
    assert daten["name"] == ORT["name"]
    assert daten["latitude"] == pytest.approx(ORT["latitude"])


@pytest.mark.asyncio
async def test_angelegter_ort_erscheint_in_der_liste(client: AsyncClient, auth_headers, test_trip):
    await client.post(f"/api/places/{test_trip.id}/places", headers=auth_headers, json=ORT)
    liste = (await client.get(f"/api/places/{test_trip.id}/places", headers=auth_headers)).json()
    assert [o["name"] for o in liste] == [ORT["name"]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "feld,wert",
    [("latitude", 91.0), ("latitude", -91.0), ("longitude", 181.0), ("longitude", -181.0), ("rating", 6)],
)
async def test_unmoegliche_werte_werden_abgewiesen(client: AsyncClient, auth_headers, test_trip, feld, wert):
    """Gegenkontrolle zu den Erfolgsfällen: die Grenzen im Schema müssen auch
    wirklich greifen. 91 Grad Breite gibt es nicht."""
    antwort = await client.post(f"/api/places/{test_trip.id}/places", headers=auth_headers, json={**ORT, feld: wert})
    assert antwort.status_code == 422


@pytest.mark.asyncio
async def test_ort_aendern(client: AsyncClient, auth_headers, test_trip, test_place):
    # PUT ist hier ein VOLLERSATZ, kein Teil-Update: `latitude`/`longitude`
    # sind Pflicht. Wer nur den Namen schickt, bekommt 422 — der Test haelt
    # das fest, damit ein Umbau auf PATCH-Semantik auffaellt.
    antwort = await client.put(
        f"/api/places/places/{test_place.id}",
        headers=auth_headers,
        json={**ORT, "name": "Neuer Name", "rating": 5},
    )
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["name"] == "Neuer Name"
    assert antwort.json()["rating"] == 5


@pytest.mark.asyncio
async def test_ort_loeschen(client: AsyncClient, auth_headers, test_place, db_session: AsyncSession):
    weg = await client.delete(f"/api/places/places/{test_place.id}", headers=auth_headers)
    assert weg.status_code == 204
    uebrig = (await db_session.execute(select(Place).where(Place.id == test_place.id))).scalar_one_or_none()
    assert uebrig is None


@pytest.mark.asyncio
async def test_besucht_markieren(client: AsyncClient, auth_headers, test_place):
    antwort = await client.put(f"/api/places/places/{test_place.id}/visited", headers=auth_headers)
    assert antwort.status_code == 200, antwort.text


@pytest.mark.asyncio
async def test_reihenfolge_setzen(client: AsyncClient, auth_headers, test_trip):
    ids = []
    for name in ("A", "B", "C"):
        angelegt = await client.post(
            f"/api/places/{test_trip.id}/places", headers=auth_headers, json={**ORT, "name": name}
        )
        ids.append(angelegt.json()["id"])
    umgedreht = list(reversed(ids))
    # Der Endpunkt nimmt eine BLANKE Liste, kein Objekt mit `place_ids`.
    antwort = await client.post(f"/api/places/{test_trip.id}/places/reorder", headers=auth_headers, json=umgedreht)
    assert antwort.status_code == 200, antwort.text
    liste = (await client.get(f"/api/places/{test_trip.id}/places", headers=auth_headers)).json()
    assert [o["id"] for o in liste] == umgedreht


# ── Zugriffsschutz (IDOR) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fremder_sieht_keine_orte(client: AsyncClient, other_auth_headers, test_trip):
    assert (await client.get(f"/api/places/{test_trip.id}/places", headers=other_auth_headers)).status_code == 403


@pytest.mark.asyncio
async def test_fremder_legt_keinen_ort_an(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.post(f"/api/places/{test_trip.id}/places", headers=other_auth_headers, json=ORT)
    assert antwort.status_code == 403


@pytest.mark.asyncio
async def test_fremder_aendert_keinen_ort(client: AsyncClient, other_auth_headers, test_place):
    antwort = await client.put(
        f"/api/places/places/{test_place.id}", headers=other_auth_headers, json={**ORT, "name": "Gekapert"}
    )
    assert antwort.status_code in (403, 404)


@pytest.mark.asyncio
async def test_fremder_loescht_keinen_ort(
    client: AsyncClient, other_auth_headers, test_place, db_session: AsyncSession
):
    antwort = await client.delete(f"/api/places/places/{test_place.id}", headers=other_auth_headers)
    assert antwort.status_code in (403, 404)
    # Positivkontrolle: der Ort ist auch wirklich noch da.
    uebrig = (await db_session.execute(select(Place).where(Place.id == test_place.id))).scalar_one_or_none()
    assert uebrig is not None


@pytest.mark.asyncio
async def test_ohne_anmeldung_kein_zugriff(client: AsyncClient, test_trip):
    assert (await client.get(f"/api/places/{test_trip.id}/places")).status_code == 401


@pytest.mark.asyncio
async def test_unbekannter_ort_ergibt_404(client: AsyncClient, auth_headers):
    assert (await client.put("/api/places/places/999999", headers=auth_headers, json=ORT)).status_code == 404


# ── Ortslisten ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_liste_anlegen_und_lesen(client: AsyncClient, auth_headers, test_trip):
    angelegt = await client.post(
        f"/api/places/{test_trip.id}/lists", headers=auth_headers, json={"title": "Restaurants", "icon": "🍽️"}
    )
    assert angelegt.status_code == 201, angelegt.text
    assert angelegt.json()["title"] == "Restaurants"

    listen = (await client.get(f"/api/places/{test_trip.id}/lists", headers=auth_headers)).json()
    assert [x["title"] for x in listen] == ["Restaurants"]


@pytest.mark.asyncio
async def test_liste_umbenennen(client: AsyncClient, auth_headers, test_trip):
    angelegt = (
        await client.post(f"/api/places/{test_trip.id}/lists", headers=auth_headers, json={"title": "Alt"})
    ).json()
    antwort = await client.put(
        f"/api/places/lists/{angelegt['id']}", headers=auth_headers, json={"title": "Neu", "color": "#F59E0B"}
    )
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["title"] == "Neu"
    assert antwort.json()["color"] == "#F59E0B"


@pytest.mark.asyncio
async def test_liste_einklappen_und_wieder_aufklappen(client: AsyncClient, auth_headers, test_trip):
    angelegt = (
        await client.post(f"/api/places/{test_trip.id}/lists", headers=auth_headers, json={"title": "Klapp"})
    ).json()
    assert angelegt["is_collapsed"] is False
    erst = await client.patch(f"/api/places/lists/{angelegt['id']}/toggle-collapse", headers=auth_headers)
    assert erst.status_code == 200, erst.text
    listen = (await client.get(f"/api/places/{test_trip.id}/lists", headers=auth_headers)).json()
    assert listen[0]["is_collapsed"] is True
    await client.patch(f"/api/places/lists/{angelegt['id']}/toggle-collapse", headers=auth_headers)
    listen = (await client.get(f"/api/places/{test_trip.id}/lists", headers=auth_headers)).json()
    assert listen[0]["is_collapsed"] is False


@pytest.mark.asyncio
async def test_liste_loeschen_behaelt_die_orte(client: AsyncClient, auth_headers, test_trip, db_session: AsyncSession):
    """Die Fremdschlüsselregel ist `SET NULL`, nicht `CASCADE`. Wer eine Liste
    löscht, will die Liste loswerden — nicht seine Orte."""
    liste = (await client.post(f"/api/places/{test_trip.id}/lists", headers=auth_headers, json={"title": "Weg"})).json()
    ort = (
        await client.post(
            f"/api/places/{test_trip.id}/places", headers=auth_headers, json={**ORT, "list_id": liste["id"]}
        )
    ).json()

    weg = await client.delete(f"/api/places/lists/{liste['id']}", headers=auth_headers)
    assert weg.status_code == 204

    db_session.expire_all()
    uebrig = (await db_session.execute(select(Place).where(Place.id == ort["id"]))).scalar_one_or_none()
    assert uebrig is not None, "Der Ort wurde mit der Liste gelöscht"
    # Zweite Hälfte derselben Zusicherung: der Ort muss auch WIRKLICH von der
    # Liste gelöst sein. Bleibt die tote list_id stehen, ist der Ort zwar da,
    # zeigt aber auf eine Liste, die es nicht mehr gibt.
    assert uebrig.list_id is None, f"Der Ort zeigt weiter auf die gelöschte Liste {uebrig.list_id}"


@pytest.mark.asyncio
async def test_fremder_sieht_keine_listen(client: AsyncClient, other_auth_headers, test_trip):
    assert (await client.get(f"/api/places/{test_trip.id}/lists", headers=other_auth_headers)).status_code == 403


@pytest.mark.asyncio
async def test_fremder_legt_keine_liste_an(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.post(
        f"/api/places/{test_trip.id}/lists", headers=other_auth_headers, json={"title": "Fremd"}
    )
    assert antwort.status_code == 403


@pytest.mark.asyncio
async def test_fremder_loescht_keine_liste(client: AsyncClient, auth_headers, other_auth_headers, test_trip):
    liste = (
        await client.post(f"/api/places/{test_trip.id}/lists", headers=auth_headers, json={"title": "Meine"})
    ).json()
    antwort = await client.delete(f"/api/places/lists/{liste['id']}", headers=other_auth_headers)
    assert antwort.status_code in (403, 404)


@pytest.mark.asyncio
async def test_put_ohne_koordinaten_wird_abgewiesen(client: AsyncClient, auth_headers, test_place):
    """Festgehaltenes Verhalten: `PUT /places/{id}` ersetzt vollständig. Ein
    Teil-Update schlägt fehl statt still die Koordinaten zu verlieren — das
    wäre die schlimmere Variante."""
    antwort = await client.put(
        f"/api/places/places/{test_place.id}", headers=auth_headers, json={"name": "Nur der Name"}
    )
    assert antwort.status_code == 422
