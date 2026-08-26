"""
Wächter für Teilen und Einladen (`routes/trips.py`, vorher 46 % gedeckt).

Zwei Wege führen aus einer Reise heraus, und beide sind Wege, auf denen Daten
das eigene Konto verlassen:

1. **Öffentlich stellen** — ein Kennzeichen im Link, jeder mit dem Link liest
   mit. Geprüft wird, dass der Link ohne Freigabe NICHT trägt, dass er beim
   Aus- und Wiedereinschalten gleich bleibt (sonst brechen verschickte Links),
   und dass `regenerate` alte Links wirklich entwertet.
2. **Einladen** — ein anderes Konto bekommt Zugriff. Geprüft wird der ganze
   Weg: einladen, annehmen, ablehnen — und dass eine offene Einladung noch
   KEINEN Zugriff gibt.
"""

import pytest
from httpx import AsyncClient

# ── Öffentlich stellen ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reise_ist_zunaechst_nicht_oeffentlich(client: AsyncClient, auth_headers, test_trip):
    daten = (await client.get(f"/api/trips/{test_trip.id}", headers=auth_headers)).json()
    assert daten["is_public"] is False


@pytest.mark.asyncio
async def test_veroeffentlichen_erzeugt_einen_link(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.patch(f"/api/trips/{test_trip.id}/publish", headers=auth_headers, json={"is_public": True})
    assert antwort.status_code == 200, antwort.text
    daten = antwort.json()
    assert daten["is_public"] is True
    assert daten["share_token"]
    assert daten["share_path"] == f"/share/{daten['share_token']}"


@pytest.mark.asyncio
async def test_der_link_traegt_ohne_anmeldung(client: AsyncClient, auth_headers, test_trip):
    token = (
        await client.patch(f"/api/trips/{test_trip.id}/publish", headers=auth_headers, json={"is_public": True})
    ).json()["share_token"]
    oeffentlich = await client.get(f"/api/public/diary/{token}")
    assert oeffentlich.status_code == 200, oeffentlich.text


@pytest.mark.asyncio
async def test_ein_erfundener_link_traegt_nicht(client: AsyncClient):
    """Positivkontrolle zum Test darüber: der öffentliche Endpunkt darf nicht
    einfach jedem antworten."""
    assert (await client.get("/api/public/diary/frei-erfunden-1234567890")).status_code == 404


@pytest.mark.asyncio
async def test_zurueckziehen_entwertet_den_link(client: AsyncClient, auth_headers, test_trip):
    token = (
        await client.patch(f"/api/trips/{test_trip.id}/publish", headers=auth_headers, json={"is_public": True})
    ).json()["share_token"]
    assert (await client.get(f"/api/public/diary/{token}")).status_code == 200

    await client.patch(f"/api/trips/{test_trip.id}/publish", headers=auth_headers, json={"is_public": False})
    assert (await client.get(f"/api/public/diary/{token}")).status_code == 404


@pytest.mark.asyncio
async def test_der_link_bleibt_ueber_aus_und_an_gleich(client: AsyncClient, auth_headers, test_trip):
    """Sonst brechen alle bereits verschickten Links, sobald jemand einmal
    kurz abschaltet."""
    erst = (
        await client.patch(f"/api/trips/{test_trip.id}/publish", headers=auth_headers, json={"is_public": True})
    ).json()["share_token"]
    await client.patch(f"/api/trips/{test_trip.id}/publish", headers=auth_headers, json={"is_public": False})
    wieder = (
        await client.patch(f"/api/trips/{test_trip.id}/publish", headers=auth_headers, json={"is_public": True})
    ).json()["share_token"]
    assert erst == wieder


@pytest.mark.asyncio
async def test_neu_erzeugen_entwertet_den_alten_link(client: AsyncClient, auth_headers, test_trip):
    alt = (
        await client.patch(f"/api/trips/{test_trip.id}/publish", headers=auth_headers, json={"is_public": True})
    ).json()["share_token"]
    neu = (
        await client.patch(
            f"/api/trips/{test_trip.id}/publish",
            headers=auth_headers,
            json={"is_public": True, "regenerate": True},
        )
    ).json()["share_token"]
    assert neu != alt
    assert (await client.get(f"/api/public/diary/{alt}")).status_code == 404
    assert (await client.get(f"/api/public/diary/{neu}")).status_code == 200


@pytest.mark.asyncio
async def test_fremder_veroeffentlicht_nicht(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.patch(
        f"/api/trips/{test_trip.id}/publish", headers=other_auth_headers, json={"is_public": True}
    )
    assert antwort.status_code == 403


# ── Einladen ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_einladen_legt_eine_offene_einladung_an(client: AsyncClient, auth_headers, test_trip, other_user):
    antwort = await client.post(
        f"/api/trips/{test_trip.id}/share",
        headers=auth_headers,
        json={"username_or_email": "otheruser", "permission": "viewer"},
    )
    assert antwort.status_code == 201, antwort.text
    assert antwort.json()["invitation_status"] == "pending"
    assert antwort.json()["user_id"] == other_user.id


@pytest.mark.asyncio
async def test_einladen_geht_auch_ueber_die_adresse(client: AsyncClient, auth_headers, test_trip, other_user):
    antwort = await client.post(
        f"/api/trips/{test_trip.id}/share",
        headers=auth_headers,
        json={"username_or_email": "other@example.com"},
    )
    assert antwort.status_code == 201, antwort.text


@pytest.mark.asyncio
async def test_unbekanntes_konto_kann_nicht_eingeladen_werden(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.post(
        f"/api/trips/{test_trip.id}/share", headers=auth_headers, json={"username_or_email": "gibtesnicht"}
    )
    assert antwort.status_code == 404


@pytest.mark.asyncio
async def test_offene_einladung_gibt_noch_KEINEN_zugriff(
    client: AsyncClient, auth_headers, other_auth_headers, test_trip, other_user
):
    """Der wichtigste Test dieser Datei."""
    await client.post(f"/api/trips/{test_trip.id}/share", headers=auth_headers, json={"username_or_email": "otheruser"})
    antwort = await client.get(f"/api/trips/{test_trip.id}", headers=other_auth_headers)
    assert antwort.status_code == 403, antwort.text


@pytest.mark.asyncio
async def test_offene_einladung_wird_dem_eingeladenen_angezeigt(
    client: AsyncClient, auth_headers, other_auth_headers, test_trip, other_user
):
    await client.post(f"/api/trips/{test_trip.id}/share", headers=auth_headers, json={"username_or_email": "otheruser"})
    offen = (await client.get("/api/trips/invitations/pending", headers=other_auth_headers)).json()
    assert len(offen) == 1
    assert offen[0]["trip_id"] == test_trip.id


@pytest.mark.asyncio
async def test_annehmen_oeffnet_den_zugriff(
    client: AsyncClient, auth_headers, other_auth_headers, test_trip, other_user
):
    await client.post(f"/api/trips/{test_trip.id}/share", headers=auth_headers, json={"username_or_email": "otheruser"})
    angenommen = await client.post(f"/api/trips/{test_trip.id}/share/accept", headers=other_auth_headers)
    assert angenommen.status_code == 200, angenommen.text

    antwort = await client.get(f"/api/trips/{test_trip.id}", headers=other_auth_headers)
    assert antwort.status_code == 200, antwort.text


@pytest.mark.asyncio
async def test_zweimal_annehmen_wird_abgewiesen(
    client: AsyncClient, auth_headers, other_auth_headers, test_trip, other_user
):
    await client.post(f"/api/trips/{test_trip.id}/share", headers=auth_headers, json={"username_or_email": "otheruser"})
    await client.post(f"/api/trips/{test_trip.id}/share/accept", headers=other_auth_headers)
    nochmal = await client.post(f"/api/trips/{test_trip.id}/share/accept", headers=other_auth_headers)
    assert nochmal.status_code == 400


@pytest.mark.asyncio
async def test_annehmen_ohne_einladung_ergibt_404(client: AsyncClient, other_auth_headers, test_trip):
    assert (await client.post(f"/api/trips/{test_trip.id}/share/accept", headers=other_auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_ablehnen_gibt_keinen_zugriff(
    client: AsyncClient, auth_headers, other_auth_headers, test_trip, other_user
):
    await client.post(f"/api/trips/{test_trip.id}/share", headers=auth_headers, json={"username_or_email": "otheruser"})
    abgelehnt = await client.post(f"/api/trips/{test_trip.id}/share/decline", headers=other_auth_headers)
    assert abgelehnt.status_code == 200, abgelehnt.text
    assert (await client.get(f"/api/trips/{test_trip.id}", headers=other_auth_headers)).status_code == 403


@pytest.mark.asyncio
async def test_fremder_laedt_niemanden_ein(client: AsyncClient, other_auth_headers, test_trip, admin_user):
    antwort = await client.post(
        f"/api/trips/{test_trip.id}/share", headers=other_auth_headers, json={"username_or_email": "adminuser"}
    )
    assert antwort.status_code == 403


@pytest.mark.asyncio
async def test_besitzer_entfernt_einen_teilnehmer_wieder(
    client: AsyncClient, auth_headers, other_auth_headers, test_trip, other_user
):
    angelegt = (
        await client.post(
            f"/api/trips/{test_trip.id}/share", headers=auth_headers, json={"username_or_email": "otheruser"}
        )
    ).json()
    await client.post(f"/api/trips/{test_trip.id}/share/accept", headers=other_auth_headers)
    assert (await client.get(f"/api/trips/{test_trip.id}", headers=other_auth_headers)).status_code == 200

    weg = await client.delete(f"/api/trips/{test_trip.id}/participants/{angelegt['id']}", headers=auth_headers)
    assert weg.status_code == 204, weg.text
    assert (await client.get(f"/api/trips/{test_trip.id}", headers=other_auth_headers)).status_code == 403


# ── Übersicht ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_zusammenfassung_zaehlt_orte_und_eintraege(client: AsyncClient, auth_headers, test_trip, test_place):
    await client.post(
        f"/api/diary/{test_trip.id}",
        headers=auth_headers,
        json={"title": "Tag 1", "content": "Text", "entry_date": "2026-09-01T10:00:00"},
    )
    daten = (await client.get(f"/api/trips/{test_trip.id}/summary", headers=auth_headers)).json()
    assert daten["total_places"] == 1
    assert daten["total_diary_entries"] == 1


@pytest.mark.asyncio
async def test_fremde_zusammenfassung_ist_gesperrt(client: AsyncClient, other_auth_headers, test_trip):
    assert (await client.get(f"/api/trips/{test_trip.id}/summary", headers=other_auth_headers)).status_code == 403
