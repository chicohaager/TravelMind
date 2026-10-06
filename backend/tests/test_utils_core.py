"""
Wächter für drei Bausteine, die überall benutzt und nirgends geprüft waren:
Paginierung (0 % gedeckt), Verschlüsselung der API-Schlüssel (40 %) und der
Einstellungs-Zugriff (32 %).

Die Verschlüsselung ist der wichtigste Teil: sie hält fremde API-Schlüssel im
Klartext von der Datenbank fern, und ihr Fehlerpfad gibt bei einem falschen
Salz einen LEEREN String zurück statt zu werfen. Ein leerer Rückgabewert sieht
wie ein leeres Feld aus — deshalb ist genau dieser Pfad hier festgenagelt.
"""

import pytest
from models.settings import Settings
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from utils.encryption import EncryptionService, encryption_service
from utils.pagination import PaginationParams, paginate_response
from utils.settings_manager import (
    can_register_new_user,
    get_max_users,
    get_setting,
    get_user_count,
    is_registration_open,
    set_setting,
)

# ── Paginierung ─────────────────────────────────────────────────────────────


def test_standardwerte():
    p = PaginationParams(skip=0, limit=50)
    assert (p.skip, p.limit) == (0, 50)


def test_limit_wird_bei_100_gekappt():
    """Die Obergrenze steht zweimal im Code — als Query-Bedingung und als
    min(). Query-Bedingungen greifen nur über HTTP; das min() ist die Hälfte,
    die auch bei direktem Aufruf trägt."""
    assert PaginationParams(skip=0, limit=5000).limit == 100


def test_antwort_meldet_weitere_seiten():
    a = paginate_response(items=[1, 2, 3], total=10, skip=0, limit=3)
    assert a == {"items": [1, 2, 3], "total": 10, "skip": 0, "limit": 3, "has_more": True}


def test_letzte_seite_meldet_keine_weiteren():
    a = paginate_response(items=[9, 10], total=10, skip=8, limit=3)
    assert a["has_more"] is False


def test_genau_aufgehende_seite_meldet_keine_weiteren():
    """Die Grenze, an der ein <= statt < falsch wäre."""
    a = paginate_response(items=[4, 5, 6], total=6, skip=3, limit=3)
    assert a["has_more"] is False


def test_leere_ergebnismenge():
    a = paginate_response(items=[], total=0, skip=0, limit=50)
    assert a["has_more"] is False and a["total"] == 0


# ── Verschlüsselung ─────────────────────────────────────────────────────────


def test_hin_und_zurueck():
    salz = encryption_service.generate_salt()
    geheim = "sk-ein-fremder-api-schluessel"
    verschluesselt = encryption_service.encrypt(geheim, salz)
    assert verschluesselt != geheim
    assert encryption_service.decrypt(verschluesselt, salz) == geheim


def test_klartext_steht_nicht_im_geheimtext():
    """Die eigentliche Zusicherung: eine Prüfung auf `!= geheim` allein wäre
    schon von einer Umkehrung des Strings erfüllt."""
    salz = encryption_service.generate_salt()
    geheim = "AbrakadabraSimsalabim"
    assert geheim not in encryption_service.encrypt(geheim, salz)


def test_zwei_salze_ergeben_zwei_geheimtexte():
    a, b = encryption_service.generate_salt(), encryption_service.generate_salt()
    assert a != b
    geheim = "derselbe-schluessel"
    assert encryption_service.encrypt(geheim, a) != encryption_service.encrypt(geheim, b)


def test_falsches_salz_ergibt_leeren_string_statt_ausnahme():
    """Dokumentiert das TATSÄCHLICHE Verhalten. Es ist ein stiller Fehlschlag
    und als solcher hier festgehalten: wer ihn ändert, muss diesen Test
    ändern und sieht dabei, was er ändert."""
    richtig = encryption_service.generate_salt()
    falsch = encryption_service.generate_salt()
    verschluesselt = encryption_service.encrypt("geheim", richtig)
    assert encryption_service.decrypt(verschluesselt, falsch) == ""


def test_anderes_SECRET_KEY_kann_nicht_entschluesseln(monkeypatch):
    salz = encryption_service.generate_salt()
    verschluesselt = encryption_service.encrypt("geheim", salz)
    monkeypatch.setenv("SECRET_KEY", "ein-voellig-anderes-geheimnis")
    fremd = EncryptionService()
    assert fremd.decrypt(verschluesselt, salz) == ""


def test_leerer_klartext_bleibt_leer():
    assert encryption_service.encrypt("", encryption_service.generate_salt()) == ""


def test_leerer_geheimtext_bleibt_leer():
    assert encryption_service.decrypt("", encryption_service.generate_salt()) == ""


def test_ohne_salz_wird_nicht_verschluesselt():
    with pytest.raises(ValueError):
        encryption_service.encrypt("geheim", "")


def test_ohne_salz_wird_nicht_entschluesselt():
    assert encryption_service.decrypt("irgendwas", "") == ""


# ── Einstellungen ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unbekannter_schluessel_liefert_default(db_session: AsyncSession):
    assert await get_setting(db_session, "gibt-es-nicht", default="fallback") == "fallback"


@pytest.mark.asyncio
async def test_setzen_und_lesen(db_session: AsyncSession):
    await set_setting(db_session, "titel", "TravelMind")
    assert await get_setting(db_session, "titel") == "TravelMind"


@pytest.mark.asyncio
async def test_ueberschreiben_legt_keinen_zweiten_eintrag_an(db_session: AsyncSession):
    await set_setting(db_session, "takt", "1", value_type="integer")
    await set_setting(db_session, "takt", "2", value_type="integer", description="geändert")
    assert await get_setting(db_session, "takt") == 2
    from sqlalchemy import func, select

    anzahl = (await db_session.execute(select(func.count(Settings.id)).where(Settings.key == "takt"))).scalar()
    assert anzahl == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "roh,erwartet",
    [("true", True), ("True", True), ("1", True), ("yes", True), ("false", False), ("nein", False), ("", False)],
)
async def test_boolesche_werte(db_session: AsyncSession, roh, erwartet):
    await set_setting(db_session, "schalter", roh, value_type="boolean")
    assert await get_setting(db_session, "schalter") is erwartet


@pytest.mark.asyncio
async def test_json_wert(db_session: AsyncSession):
    await set_setting(db_session, "liste", '{"a": [1, 2]}', value_type="json")
    assert await get_setting(db_session, "liste") == {"a": [1, 2]}


@pytest.mark.asyncio
async def test_registrierung_ist_ohne_eintrag_offen(db_session: AsyncSession):
    assert await is_registration_open(db_session) is True
    erlaubt, grund = await can_register_new_user(db_session)
    assert erlaubt is True and grund == "OK"


@pytest.mark.asyncio
async def test_geschlossene_registrierung_wird_begruendet(db_session: AsyncSession):
    await set_setting(db_session, "registration_open", "false", value_type="boolean")
    erlaubt, grund = await can_register_new_user(db_session)
    assert erlaubt is False
    assert "geschlossen" in grund


@pytest.mark.asyncio
async def test_nutzerobergrenze_greift(db_session: AsyncSession, test_user: User):
    assert await get_user_count(db_session) == 1
    await set_setting(db_session, "max_users", "1", value_type="integer")
    assert await get_max_users(db_session) == 1
    erlaubt, grund = await can_register_new_user(db_session)
    assert erlaubt is False
    assert "1" in grund


@pytest.mark.asyncio
async def test_obergrenze_null_bedeutet_unbegrenzt(db_session: AsyncSession, test_user: User):
    await set_setting(db_session, "max_users", "0", value_type="integer")
    erlaubt, _ = await can_register_new_user(db_session)
    assert erlaubt is True
