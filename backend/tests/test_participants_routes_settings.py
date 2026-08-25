"""
Wächter für drei Bereiche, die zusammen 143 ungedeckte Zeilen hatten:
Teilnehmer (51 %), gespeicherte Routen (55 %) und die Nutzereinstellungen
(60 %).

Die Einstellungen sind der heikelste Teil: dort landet der API-Schlüssel eines
fremden Anbieters. Geprüft wird deshalb nicht nur, dass das Speichern
funktioniert, sondern dass der Schlüssel **nie wieder aus der API
herauskommt** und **verschlüsselt** in der Datenbank steht.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from models.place import Place
from models.route import Route
from models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ── Teilnehmer ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_neue_reise_hat_keine_teilnehmer(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.get(f"/api/trips/{test_trip.id}/participants", headers=auth_headers)
    assert antwort.status_code == 200
    assert antwort.json() == []


@pytest.mark.asyncio
async def test_teilnehmer_anlegen_und_wiederfinden(client: AsyncClient, auth_headers, test_trip):
    angelegt = await client.post(
        f"/api/trips/{test_trip.id}/participants",
        headers=auth_headers,
        json={"name": "Max Mustermann", "email": "max@example.com", "role": "Freund"},
    )
    assert angelegt.status_code == 201, angelegt.text
    assert angelegt.json()["name"] == "Max Mustermann"

    liste = (await client.get(f"/api/trips/{test_trip.id}/participants", headers=auth_headers)).json()
    assert [t["name"] for t in liste] == ["Max Mustermann"]


@pytest.mark.asyncio
async def test_teilnehmer_aendern(client: AsyncClient, auth_headers, test_trip):
    angelegt = (
        await client.post(f"/api/trips/{test_trip.id}/participants", headers=auth_headers, json={"name": "Alt"})
    ).json()
    geaendert = await client.put(
        f"/api/trips/participants/{angelegt['id']}", headers=auth_headers, json={"name": "Neu", "role": "Familie"}
    )
    assert geaendert.status_code == 200, geaendert.text
    assert geaendert.json()["name"] == "Neu"
    assert geaendert.json()["role"] == "Familie"


@pytest.mark.asyncio
async def test_teilnehmer_entfernen(client: AsyncClient, auth_headers, test_trip):
    angelegt = (
        await client.post(f"/api/trips/{test_trip.id}/participants", headers=auth_headers, json={"name": "Weg"})
    ).json()
    weg = await client.delete(f"/api/trips/participants/{angelegt['id']}", headers=auth_headers)
    assert weg.status_code == 204
    assert (await client.get(f"/api/trips/{test_trip.id}/participants", headers=auth_headers)).json() == []


@pytest.mark.asyncio
async def test_fremder_sieht_keine_teilnehmer(client: AsyncClient, other_auth_headers, test_trip):
    assert (await client.get(f"/api/trips/{test_trip.id}/participants", headers=other_auth_headers)).status_code == 403


@pytest.mark.asyncio
async def test_fremder_legt_keinen_teilnehmer_an(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.post(
        f"/api/trips/{test_trip.id}/participants", headers=other_auth_headers, json={"name": "Eindringling"}
    )
    assert antwort.status_code == 403


@pytest.mark.asyncio
async def test_fremder_aendert_keinen_teilnehmer(client: AsyncClient, auth_headers, other_auth_headers, test_trip):
    angelegt = (
        await client.post(f"/api/trips/{test_trip.id}/participants", headers=auth_headers, json={"name": "Meiner"})
    ).json()
    antwort = await client.put(
        f"/api/trips/participants/{angelegt['id']}", headers=other_auth_headers, json={"name": "Gekapert"}
    )
    assert antwort.status_code in (403, 404)


@pytest.mark.asyncio
async def test_unbekannter_teilnehmer_ergibt_404(client: AsyncClient, auth_headers):
    assert (
        await client.put("/api/trips/participants/999999", headers=auth_headers, json={"name": "X"})
    ).status_code == 404


@pytest.mark.asyncio
async def test_teilnehmer_ohne_anmeldung(client: AsyncClient, test_trip):
    assert (await client.get(f"/api/trips/{test_trip.id}/participants")).status_code == 401


# ── Gespeicherte Routen ─────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def zwei_orte(db_session: AsyncSession, test_trip):
    orte = [
        Place(name="Start", latitude=38.71, longitude=-9.14, trip_id=test_trip.id),
        Place(name="Ziel", latitude=38.69, longitude=-9.21, trip_id=test_trip.id),
    ]
    for o in orte:
        db_session.add(o)
    await db_session.commit()
    for o in orte:
        await db_session.refresh(o)
    return orte


@pytest.mark.asyncio
async def test_route_anlegen(client: AsyncClient, auth_headers, test_trip, zwei_orte):
    antwort = await client.post(
        "/api/routes/",
        headers=auth_headers,
        json={
            "name": "Tag 1",
            "trip_id": test_trip.id,
            "place_ids": [o.id for o in zwei_orte],
            "transport_mode": "walk",
        },
    )
    assert antwort.status_code == 201, antwort.text
    daten = antwort.json()
    assert daten["name"] == "Tag 1"
    assert daten["place_ids"] == [o.id for o in zwei_orte]


@pytest.mark.asyncio
async def test_routen_einer_reise_auflisten(client: AsyncClient, auth_headers, test_trip, zwei_orte):
    await client.post("/api/routes/", headers=auth_headers, json={"name": "A", "trip_id": test_trip.id})
    await client.post("/api/routes/", headers=auth_headers, json={"name": "B", "trip_id": test_trip.id})
    liste = (await client.get(f"/api/routes/trip/{test_trip.id}", headers=auth_headers)).json()
    assert sorted(r["name"] for r in liste) == ["A", "B"]


@pytest.mark.asyncio
async def test_einzelne_route_lesen(client: AsyncClient, auth_headers, test_trip):
    angelegt = (
        await client.post("/api/routes/", headers=auth_headers, json={"name": "Einzel", "trip_id": test_trip.id})
    ).json()
    antwort = await client.get(f"/api/routes/{angelegt['id']}", headers=auth_headers)
    assert antwort.status_code == 200
    assert antwort.json()["name"] == "Einzel"


@pytest.mark.asyncio
async def test_route_aendern(client: AsyncClient, auth_headers, test_trip):
    angelegt = (
        await client.post("/api/routes/", headers=auth_headers, json={"name": "Alt", "trip_id": test_trip.id})
    ).json()
    antwort = await client.put(
        f"/api/routes/{angelegt['id']}", headers=auth_headers, json={"name": "Neu", "color": "#FF0000"}
    )
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["name"] == "Neu"
    assert antwort.json()["color"] == "#FF0000"


@pytest.mark.asyncio
async def test_route_loeschen(client: AsyncClient, auth_headers, test_trip, db_session: AsyncSession):
    angelegt = (
        await client.post("/api/routes/", headers=auth_headers, json={"name": "Weg", "trip_id": test_trip.id})
    ).json()
    weg = await client.delete(f"/api/routes/{angelegt['id']}", headers=auth_headers)
    assert weg.status_code == 204
    uebrig = (await db_session.execute(select(Route).where(Route.id == angelegt["id"]))).scalar_one_or_none()
    assert uebrig is None


@pytest.mark.asyncio
async def test_route_in_fremder_reise_wird_abgewiesen(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.post(
        "/api/routes/", headers=other_auth_headers, json={"name": "Fremd", "trip_id": test_trip.id}
    )
    assert antwort.status_code in (403, 404)


@pytest.mark.asyncio
async def test_fremde_route_ist_nicht_lesbar(client: AsyncClient, auth_headers, other_auth_headers, test_trip):
    angelegt = (
        await client.post("/api/routes/", headers=auth_headers, json={"name": "Meine", "trip_id": test_trip.id})
    ).json()
    antwort = await client.get(f"/api/routes/{angelegt['id']}", headers=other_auth_headers)
    assert antwort.status_code in (403, 404)


@pytest.mark.asyncio
async def test_unbekannte_route_ergibt_404(client: AsyncClient, auth_headers):
    assert (await client.get("/api/routes/999999", headers=auth_headers)).status_code == 404


# ── Nutzereinstellungen ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_einstellungen_lesen(client: AsyncClient, auth_headers, test_user):
    antwort = await client.get("/api/user/settings", headers=auth_headers)
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["username"] == test_user.username
    assert daten["ai_settings"]["has_api_key"] is False


@pytest.mark.asyncio
async def test_ki_einstellungen_ohne_schluessel(client: AsyncClient, auth_headers):
    daten = (await client.get("/api/user/settings/ai", headers=auth_headers)).json()
    assert daten["has_api_key"] is False


@pytest.mark.asyncio
async def test_schluessel_speichern_meldet_nur_das_VORHANDENSEIN(client: AsyncClient, auth_headers):
    antwort = await client.put(
        "/api/user/settings/ai", headers=auth_headers, json={"ai_provider": "groq", "api_key": "gsk_geheim_1234567"}
    )
    assert antwort.status_code == 200, antwort.text
    daten = antwort.json()
    assert daten["has_api_key"] is True
    assert "api_key" not in daten
    assert "gsk_geheim_1234567" not in antwort.text


@pytest.mark.asyncio
async def test_schluessel_steht_verschluesselt_in_der_datenbank(
    client: AsyncClient, auth_headers, db_session: AsyncSession, test_user
):
    """Die eigentliche Zusicherung. `has_api_key: true` sagt nur, dass ein Feld
    gefüllt ist — nicht, dass der Inhalt geschützt ist."""
    geheim = "gsk_dieser_wert_darf_nicht_im_klartext_liegen"
    await client.put("/api/user/settings/ai", headers=auth_headers, json={"ai_provider": "groq", "api_key": geheim})

    nutzer = (await db_session.execute(select(User).where(User.id == test_user.id))).scalar_one()
    assert nutzer.encrypted_api_key
    assert geheim not in nutzer.encrypted_api_key
    assert nutzer.encryption_salt

    from utils.encryption import encryption_service

    assert encryption_service.decrypt(nutzer.encrypted_api_key, nutzer.encryption_salt) == geheim


@pytest.mark.asyncio
async def test_schluessel_taucht_in_keiner_auskunft_auf(client: AsyncClient, auth_headers):
    geheim = "gsk_nirgends_sichtbar_9876"
    await client.put("/api/user/settings/ai", headers=auth_headers, json={"ai_provider": "groq", "api_key": geheim})
    for pfad in ("/api/user/settings", "/api/user/settings/ai", "/api/users/profile"):
        antwort = await client.get(pfad, headers=auth_headers)
        assert geheim not in antwort.text, f"{pfad} gibt den Schlüssel heraus"


@pytest.mark.asyncio
async def test_unbekannter_anbieter_wird_abgewiesen(client: AsyncClient, auth_headers):
    antwort = await client.put(
        "/api/user/settings/ai", headers=auth_headers, json={"ai_provider": "skynet", "api_key": "1234567890"}
    )
    assert antwort.status_code == 400


@pytest.mark.asyncio
async def test_zu_kurzer_schluessel_wird_abgewiesen(client: AsyncClient, auth_headers):
    antwort = await client.put(
        "/api/user/settings/ai", headers=auth_headers, json={"ai_provider": "groq", "api_key": "kurz"}
    )
    assert antwort.status_code == 422


@pytest.mark.asyncio
async def test_schluessel_loeschen(client: AsyncClient, auth_headers, db_session: AsyncSession, test_user):
    await client.put(
        "/api/user/settings/ai", headers=auth_headers, json={"ai_provider": "groq", "api_key": "gsk_wegdamit_123"}
    )
    weg = await client.delete("/api/user/settings/ai", headers=auth_headers)
    assert weg.status_code == 200
    assert (await client.get("/api/user/settings/ai", headers=auth_headers)).json()["has_api_key"] is False
    nutzer = (await db_session.execute(select(User).where(User.id == test_user.id))).scalar_one()
    assert not nutzer.encrypted_api_key


@pytest.mark.asyncio
async def test_einstellungen_ohne_anmeldung(client: AsyncClient):
    assert (await client.get("/api/user/settings")).status_code == 401
