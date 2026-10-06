"""
Wächter für Passwort-Zurücksetzen (`routes/password_reset.py`, vorher 37 %)
und Datenauskunft/-löschung (`routes/data_export.py`, vorher 36 %).

Das Zurücksetzen ist der zweite Weg in ein Konto hinein und damit
sicherheitsrelevant: es muss dieselbe Antwort geben, egal ob es die Adresse
gibt (sonst wird der Endpunkt zum Adressverzeichnis), es darf keinen
gebrauchten oder gefälschten Schlüssel akzeptieren, und ein neu gesetztes
Passwort muss WIRKEN — beide Richtungen.

Kein Test verschickt Post: `send_reset_email` wird ersetzt.
"""

import pytest
from httpx import AsyncClient
from models.user import User
from routes import password_reset as pr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

NEUES_PASSWORT = "ein-neues-und-ziemlich-eigenes-passwort"


@pytest.fixture(autouse=True)
def keine_post(monkeypatch):
    verschickt = []

    async def merken(email, token, username):
        verschickt.append({"email": email, "token": token, "username": username})

    monkeypatch.setattr(pr, "send_reset_email", merken)
    return verschickt


# ── Anforderung ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_anforderung_fuer_ein_bekanntes_konto(client: AsyncClient, test_user):
    antwort = await client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["email_sent"] is True


@pytest.mark.asyncio
async def test_unbekannte_adresse_bekommt_DIESELBE_antwort(client: AsyncClient, test_user):
    """Sonst ist der Endpunkt ein Adressverzeichnis: wer verschiedene
    Antworten bekommt, kann durchprobieren, wer hier ein Konto hat."""
    bekannt = await client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
    unbekannt = await client.post("/api/auth/forgot-password", json={"email": "niemand@example.com"})
    assert bekannt.status_code == unbekannt.status_code == 200
    assert bekannt.json() == unbekannt.json()


@pytest.mark.asyncio
async def test_nur_fuer_ein_bekanntes_konto_geht_wirklich_post_raus(client: AsyncClient, test_user, keine_post):
    """Die Gegenkontrolle zum Test darüber: die Antwort ist gleich, die
    HANDLUNG darf es nicht sein."""
    await client.post("/api/auth/forgot-password", json={"email": "niemand@example.com"})
    assert keine_post == []
    await client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
    assert len(keine_post) == 1
    assert keine_post[0]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_unsinnige_adresse_wird_abgewiesen(client: AsyncClient):
    antwort = await client.post("/api/auth/forgot-password", json={"email": "keine-adresse"})
    assert antwort.status_code == 422


# ── Schlüssel prüfen ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_frischer_schluessel_ist_gueltig(client: AsyncClient, test_user, keine_post):
    await client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
    token = keine_post[0]["token"]
    daten = (await client.get(f"/api/auth/verify-reset-token?token={token}")).json()
    assert daten["valid"] is True
    assert daten["expires_in_minutes"] > 0
    # Die Adresse darf nur angedeutet werden.
    assert daten["email"].endswith("***")
    assert "test@example.com" not in daten["email"]


@pytest.mark.asyncio
async def test_erfundener_schluessel_ist_ungueltig(client: AsyncClient):
    daten = (await client.get("/api/auth/verify-reset-token?token=voellig.frei.erfunden")).json()
    assert daten["valid"] is False


# ── Zurücksetzen ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_zuruecksetzen_und_das_neue_passwort_wirkt(client: AsyncClient, test_user, keine_post):
    await client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
    token = keine_post[0]["token"]

    gesetzt = await client.post("/api/auth/reset-password", json={"token": token, "new_password": NEUES_PASSWORT})
    assert gesetzt.status_code == 200, gesetzt.text

    neu = await client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": NEUES_PASSWORT},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert neu.status_code == 200, neu.text


@pytest.mark.asyncio
async def test_das_alte_passwort_gilt_danach_nicht_mehr(client: AsyncClient, test_user, keine_post):
    """Die zweite Hälfte: ein Zurücksetzen, das das alte Passwort stehen
    lässt, hat nichts zurückgesetzt."""
    await client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
    await client.post(
        "/api/auth/reset-password", json={"token": keine_post[0]["token"], "new_password": NEUES_PASSWORT}
    )
    alt = await client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert alt.status_code in (400, 401)


@pytest.mark.asyncio
async def test_derselbe_schluessel_wirkt_kein_zweites_mal(client: AsyncClient, test_user, keine_post):
    await client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
    token = keine_post[0]["token"]
    erst = await client.post("/api/auth/reset-password", json={"token": token, "new_password": NEUES_PASSWORT})
    assert erst.status_code == 200
    nochmal = await client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": NEUES_PASSWORT + "-anders"}
    )
    assert nochmal.status_code in (400, 401), nochmal.text


@pytest.mark.asyncio
async def test_erfundener_schluessel_setzt_nichts_zurueck(client: AsyncClient, test_user, db_session: AsyncSession):
    vorher = (await db_session.execute(select(User.hashed_password).where(User.id == test_user.id))).scalar_one()
    antwort = await client.post(
        "/api/auth/reset-password", json={"token": "voellig.frei.erfunden", "new_password": NEUES_PASSWORT}
    )
    assert antwort.status_code in (400, 401)
    nachher = (await db_session.execute(select(User.hashed_password).where(User.id == test_user.id))).scalar_one()
    assert vorher == nachher


@pytest.mark.asyncio
async def test_zu_kurzes_neues_passwort_wird_abgewiesen(client: AsyncClient, test_user, keine_post):
    await client.post("/api/auth/forgot-password", json={"email": "test@example.com"})
    antwort = await client.post(
        "/api/auth/reset-password", json={"token": keine_post[0]["token"], "new_password": "kurz"}
    )
    assert antwort.status_code == 422


# ── Datenauskunft (DSGVO) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auskunft_ueber_den_umfang(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.get("/api/users/export/info", headers=auth_headers)
    assert antwort.status_code == 200, antwort.text
    daten = antwort.json()
    assert "json" in daten["available_formats"]
    assert any("Trips (1)" in e for e in daten["includes"]), daten["includes"]


@pytest.mark.asyncio
async def test_datenmitnahme_als_json(client: AsyncClient, auth_headers, test_trip, test_place):
    antwort = await client.get("/api/users/export/download?format=json", headers=auth_headers)
    assert antwort.status_code == 200, antwort.text[:300]
    daten = antwort.json()
    # Der INHALT, nicht der Statuscode: eine Mitnahme ohne die eigenen Daten
    # erfüllt Artikel 20 nicht, sieht aber genauso aus.
    assert daten["user_profile"]["username"] == "testuser"
    assert [t["title"] for t in daten["trips"]] == [test_trip.title]


@pytest.mark.asyncio
async def test_datenmitnahme_gibt_KEINEN_passworthash_heraus(client: AsyncClient, auth_headers, test_user):
    antwort = await client.get("/api/users/export/download?format=json", headers=auth_headers)
    assert test_user.hashed_password not in antwort.text
    assert "hashed_password" not in antwort.text


@pytest.mark.asyncio
async def test_datenmitnahme_als_zip(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.get("/api/users/export/download?format=zip", headers=auth_headers)
    assert antwort.status_code == 200, antwort.text[:300]
    # Ein ZIP beginnt mit PK\x03\x04.
    assert antwort.content[:4] == b"PK\x03\x04", antwort.content[:20]


@pytest.mark.asyncio
async def test_jeder_sieht_nur_seine_eigenen_daten(client: AsyncClient, other_auth_headers, test_trip):
    daten = (await client.get("/api/users/export/download?format=json", headers=other_auth_headers)).json()
    assert daten["user_profile"]["username"] == "otheruser"
    assert daten["trips"] == []


@pytest.mark.asyncio
async def test_loeschantrag_wird_protokolliert(client: AsyncClient, auth_headers, test_trip, db_session):
    from models.audit_log import AuditLog
    from sqlalchemy import select as sql_select

    antwort = await client.delete("/api/users/account/data", headers=auth_headers)
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["status"] == "pending"
    eintraege = (await db_session.execute(sql_select(AuditLog))).scalars().all()
    assert eintraege, "Der Löschantrag wurde nicht protokolliert"


@pytest.mark.asyncio
async def test_datenauskunft_ohne_anmeldung(client: AsyncClient):
    assert (await client.get("/api/users/export/info")).status_code == 401
    assert (await client.get("/api/users/export/download")).status_code == 401
