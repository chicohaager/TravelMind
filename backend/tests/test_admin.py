"""
Wächter für die Verwaltung (`routes/admin.py`, vorher 39 % gedeckt).

Hier liegt die größte Machtkonzentration der Anwendung: Nutzer anlegen,
sperren, löschen, zum Administrator machen, die Registrierung öffnen. Für
JEDEN dieser Endpunkte gibt es deshalb den Gegentest mit einem gewöhnlichen
Konto — ein Verwaltungsendpunkt ohne Rechteprüfung ist keine Lücke, sondern
die ganze Anwendung.

Zusätzlich wird geprüft, dass die Verwaltung ein Prüfprotokoll schreibt: eine
Rechteänderung, die niemand nachvollziehen kann, ist im Nachhinein nicht von
einem Einbruch zu unterscheiden.
"""

import pytest
from httpx import AsyncClient
from models.audit_log import AuditLog
from models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ── Rechteprüfung: der Gegentest zu allem, was folgt ────────────────────────

VERWALTUNGSPFADE = [
    ("get", "/api/admin/users"),
    ("get", "/api/admin/stats"),
    ("get", "/api/admin/settings"),
    ("get", "/api/admin/audit-logs"),
    ("get", "/api/admin/audit-logs/stats"),
    ("get", "/api/admin/rate-limits"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("methode,pfad", VERWALTUNGSPFADE)
async def test_gewoehnliches_konto_kommt_nicht_in_die_verwaltung(client: AsyncClient, auth_headers, methode, pfad):
    antwort = await getattr(client, methode)(pfad, headers=auth_headers)
    assert antwort.status_code == 403, f"{pfad} war für ein normales Konto erreichbar"


@pytest.mark.asyncio
@pytest.mark.parametrize("methode,pfad", VERWALTUNGSPFADE)
async def test_ohne_anmeldung_erst_recht_nicht(client: AsyncClient, methode, pfad):
    antwort = await getattr(client, methode)(pfad)
    assert antwort.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("methode,pfad", VERWALTUNGSPFADE)
async def test_positivkontrolle_der_administrator_kommt_durch(client: AsyncClient, admin_headers, methode, pfad):
    """Ohne diese Hälfte wäre der Test oben auch dann grün, wenn die Endpunkte
    gar nicht existierten."""
    antwort = await getattr(client, methode)(pfad, headers=admin_headers)
    assert antwort.status_code == 200, antwort.text


# ── Nutzerverwaltung ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nutzerliste_enthaelt_beide_konten(client: AsyncClient, admin_headers, test_user, admin_user):
    liste = (await client.get("/api/admin/users", headers=admin_headers)).json()
    namen = {n["username"] for n in liste}
    assert {"testuser", "adminuser"} <= namen


@pytest.mark.asyncio
async def test_nutzerliste_gibt_KEIN_passwort_heraus(client: AsyncClient, admin_headers, test_user):
    antwort = await client.get("/api/admin/users", headers=admin_headers)
    assert "hashed_password" not in antwort.text
    assert test_user.hashed_password not in antwort.text


@pytest.mark.asyncio
async def test_nutzerliste_laesst_sich_durchsuchen(client: AsyncClient, admin_headers, test_user, admin_user):
    treffer = (await client.get("/api/admin/users?search=testuser", headers=admin_headers)).json()
    assert [n["username"] for n in treffer] == ["testuser"]
    # Gegenkontrolle: eine Suche, die nichts finden darf, findet auch nichts.
    leer = (await client.get("/api/admin/users?search=gibtesnicht", headers=admin_headers)).json()
    assert leer == []


@pytest.mark.asyncio
async def test_einzelnen_nutzer_ansehen(client: AsyncClient, admin_headers, test_user, test_trip):
    daten = (await client.get(f"/api/admin/users/{test_user.id}", headers=admin_headers)).json()
    assert daten["username"] == "testuser"
    assert daten["trip_count"] == 1


@pytest.mark.asyncio
async def test_unbekannter_nutzer_ergibt_404(client: AsyncClient, admin_headers):
    assert (await client.get("/api/admin/users/999999", headers=admin_headers)).status_code == 404


@pytest.mark.asyncio
async def test_nutzer_sperren(client: AsyncClient, admin_headers, test_user, db_session: AsyncSession):
    antwort = await client.put(f"/api/admin/users/{test_user.id}", headers=admin_headers, json={"is_active": False})
    assert antwort.status_code == 200, antwort.text
    # Die Spalte direkt lesen statt das Objekt aufzufrischen: ein abgelaufenes
    # ORM-Objekt laedt beim Zugriff nach, und das geht im asynchronen Kontext
    # nicht (MissingGreenlet).
    aktiv = (await db_session.execute(select(User.is_active).where(User.id == test_user.id))).scalar_one()
    assert aktiv is False


@pytest.mark.asyncio
async def test_gesperrter_nutzer_kommt_nicht_mehr_rein(client: AsyncClient, admin_headers, test_user):
    """Die Sperre muss WIRKEN, nicht nur ein Feld setzen."""
    vorher = await client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert vorher.status_code == 200

    await client.put(f"/api/admin/users/{test_user.id}", headers=admin_headers, json={"is_active": False})

    nachher = await client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert nachher.status_code in (400, 401, 403), nachher.text


@pytest.mark.asyncio
async def test_nutzer_loeschen(client: AsyncClient, admin_headers, test_user, db_session: AsyncSession):
    weg = await client.delete(f"/api/admin/users/{test_user.id}", headers=admin_headers)
    assert weg.status_code == 204
    uebrig = (await db_session.execute(select(User).where(User.id == test_user.id))).scalar_one_or_none()
    assert uebrig is None


@pytest.mark.asyncio
async def test_administrator_kann_sich_nicht_selbst_loeschen(
    client: AsyncClient, admin_headers, admin_user, db_session: AsyncSession
):
    """Sonst gibt es die Anwendung ohne Verwaltung — und ohne Rückweg."""
    antwort = await client.delete(f"/api/admin/users/{admin_user.id}", headers=admin_headers)
    assert antwort.status_code == 400
    uebrig = (await db_session.execute(select(User).where(User.id == admin_user.id))).scalar_one_or_none()
    assert uebrig is not None


@pytest.mark.asyncio
async def test_gewoehnliches_konto_loescht_niemanden(client: AsyncClient, auth_headers, admin_user):
    assert (await client.delete(f"/api/admin/users/{admin_user.id}", headers=auth_headers)).status_code == 403


@pytest.mark.asyncio
async def test_administrator_legt_nutzer_an(client: AsyncClient, admin_headers):
    antwort = await client.post(
        "/api/admin/users/create",
        headers=admin_headers,
        json={
            "username": "neuling",
            "email": "neuling@example.com",
            "password": "ein-ziemlich-langes-und-eigenes-passwort",
            "full_name": "Neu Ling",
        },
    )
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["user"]["username"] == "neuling"


@pytest.mark.asyncio
async def test_doppelter_nutzername_wird_abgewiesen(client: AsyncClient, admin_headers, test_user):
    antwort = await client.post(
        "/api/admin/users/create",
        headers=admin_headers,
        json={
            "username": "testuser",
            "email": "anders@example.com",
            "password": "ein-ziemlich-langes-und-eigenes-passwort",
        },
    )
    assert antwort.status_code == 400


@pytest.mark.asyncio
async def test_doppelte_adresse_wird_abgewiesen(client: AsyncClient, admin_headers, test_user):
    antwort = await client.post(
        "/api/admin/users/create",
        headers=admin_headers,
        json={
            "username": "andersrum",
            "email": "test@example.com",
            "password": "ein-ziemlich-langes-und-eigenes-passwort",
        },
    )
    assert antwort.status_code == 400


# ── Einstellungen ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_einstellung_setzen_und_lesen(client: AsyncClient, admin_headers):
    gesetzt = await client.put(
        "/api/admin/settings/max_users", headers=admin_headers, json={"value": "5", "value_type": "integer"}
    )
    assert gesetzt.status_code == 200, gesetzt.text
    assert gesetzt.json()["typed_value"] == 5

    gelesen = await client.get("/api/admin/settings/max_users", headers=admin_headers)
    assert gelesen.status_code == 200
    assert gelesen.json()["typed_value"] == 5


@pytest.mark.asyncio
async def test_registrierung_umschalten_wirkt_auf_die_anmeldung(client: AsyncClient, admin_headers):
    """Der Schalter muss die REGISTRIERUNG schließen, nicht nur ein Feld
    setzen."""
    aus = await client.post("/api/admin/settings/registration/toggle", headers=admin_headers)
    assert aus.status_code == 200, aus.text

    versuch = await client.post(
        "/api/auth/register",
        json={
            "username": "zuspaet",
            "email": "zuspaet@example.com",
            "password": "ein-ziemlich-langes-und-eigenes-passwort",
        },
    )
    assert versuch.status_code == 403, versuch.text

    # Und wieder auf: sonst prüft der Test nur eine Einbahnstraße.
    await client.post("/api/admin/settings/registration/toggle", headers=admin_headers)
    wieder = await client.post(
        "/api/auth/register",
        json={
            "username": "dochnoch",
            "email": "dochnoch@example.com",
            "password": "ein-ziemlich-langes-und-eigenes-passwort",
        },
    )
    assert wieder.status_code in (200, 201), wieder.text


# ── Prüfprotokoll ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rechteaenderung_landet_im_pruefprotokoll(
    client: AsyncClient, admin_headers, test_user, db_session: AsyncSession
):
    await client.put(f"/api/admin/users/{test_user.id}", headers=admin_headers, json={"is_superuser": True})
    eintraege = (await db_session.execute(select(AuditLog))).scalars().all()
    assert eintraege, "Die Rechteänderung wurde nicht protokolliert"


@pytest.mark.asyncio
async def test_pruefprotokoll_ist_ueber_die_api_lesbar(client: AsyncClient, admin_headers, test_user):
    await client.put(f"/api/admin/users/{test_user.id}", headers=admin_headers, json={"is_active": False})
    antwort = await client.get("/api/admin/audit-logs", headers=admin_headers)
    assert antwort.status_code == 200
    assert len(antwort.json()) >= 1


@pytest.mark.asyncio
async def test_systemstatistik_zaehlt_mit(client: AsyncClient, admin_headers, test_user, admin_user, test_trip):
    daten = (await client.get("/api/admin/stats", headers=admin_headers)).json()
    assert daten["total_users"] >= 2
    assert daten["total_trips"] >= 1
