"""
Wächter für die IDOR-Sperre.

`utils/access_control.verify_trip_access` ist die Stelle, an der entschieden
wird, wer eine fremde Reise sehen oder ändern darf. Sie war zu 34 % von Tests
gedeckt — genau die Verzweigungen, die eine Zugriffsverletzung verhindern,
liefen ungeprüft mit.

Jeder Test hier prüft eine ANDERE Verzweigung, und für jede erlaubende gibt es
die verbietende daneben: ein Wächter, der nur eine Richtung kennt, kann nicht
rot werden.
"""

import pytest
from fastapi import HTTPException
from models.participant import InvitationStatus, Participant, PermissionLevel
from models.trip import Trip
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from utils.access_control import verify_diary_entry_access, verify_trip_access


async def _reise_anlegen(db: AsyncSession, besitzer_id: int, titel: str = "Reise") -> Trip:
    trip = Trip(title=titel, destination="Lissabon", owner_id=besitzer_id)
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


async def _zweiter_nutzer(db: AsyncSession, name: str = "fremder") -> User:
    user = User(
        username=name,
        email=f"{name}@example.com",
        hashed_password=User.hash_password("irrelevant-fuer-diesen-test"),
        full_name=name,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _teilnehmer(
    db: AsyncSession,
    trip: Trip,
    user: User,
    status: str = InvitationStatus.ACCEPTED.value,
    permission: str = PermissionLevel.VIEWER.value,
) -> Participant:
    p = Participant(
        trip_id=trip.id,
        user_id=user.id,
        name=user.username,
        permission=permission,
        invitation_status=status,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest.mark.asyncio
async def test_besitzer_darf(db_session: AsyncSession, test_user: User):
    trip = await _reise_anlegen(db_session, test_user.id)
    assert (await verify_trip_access(trip.id, test_user, db_session)).id == trip.id


@pytest.mark.asyncio
async def test_besitzer_darf_auch_bearbeiten(db_session: AsyncSession, test_user: User):
    trip = await _reise_anlegen(db_session, test_user.id)
    assert (await verify_trip_access(trip.id, test_user, db_session, require_edit=True)).id == trip.id


@pytest.mark.asyncio
async def test_fremder_wird_abgewiesen(db_session: AsyncSession, test_user: User):
    trip = await _reise_anlegen(db_session, test_user.id)
    fremder = await _zweiter_nutzer(db_session)
    with pytest.raises(HTTPException) as fehler:
        await verify_trip_access(trip.id, fremder, db_session)
    assert fehler.value.status_code == 403


@pytest.mark.asyncio
async def test_nicht_vorhandene_reise_ergibt_404(db_session: AsyncSession, test_user: User):
    with pytest.raises(HTTPException) as fehler:
        await verify_trip_access(999999, test_user, db_session)
    assert fehler.value.status_code == 404


@pytest.mark.asyncio
async def test_angenommener_teilnehmer_darf_lesen(db_session: AsyncSession, test_user: User):
    trip = await _reise_anlegen(db_session, test_user.id)
    gast = await _zweiter_nutzer(db_session, "gast")
    await _teilnehmer(db_session, trip, gast)
    assert (await verify_trip_access(trip.id, gast, db_session)).id == trip.id


@pytest.mark.asyncio
async def test_offene_einladung_reicht_NICHT(db_session: AsyncSession, test_user: User):
    """Der Unterschied zwischen eingeladen und angenommen ist der ganze Punkt."""
    trip = await _reise_anlegen(db_session, test_user.id)
    gast = await _zweiter_nutzer(db_session, "eingeladen")
    await _teilnehmer(db_session, trip, gast, status=InvitationStatus.PENDING.value)
    with pytest.raises(HTTPException) as fehler:
        await verify_trip_access(trip.id, gast, db_session)
    assert fehler.value.status_code == 403


@pytest.mark.asyncio
async def test_abgelehnte_einladung_reicht_NICHT(db_session: AsyncSession, test_user: User):
    trip = await _reise_anlegen(db_session, test_user.id)
    gast = await _zweiter_nutzer(db_session, "abgelehnt")
    await _teilnehmer(db_session, trip, gast, status=InvitationStatus.DECLINED.value)
    with pytest.raises(HTTPException) as fehler:
        await verify_trip_access(trip.id, gast, db_session)
    assert fehler.value.status_code == 403


@pytest.mark.asyncio
async def test_leser_darf_nicht_bearbeiten(db_session: AsyncSession, test_user: User):
    trip = await _reise_anlegen(db_session, test_user.id)
    gast = await _zweiter_nutzer(db_session, "leser")
    await _teilnehmer(db_session, trip, gast, permission=PermissionLevel.VIEWER.value)
    # lesen: ja
    assert (await verify_trip_access(trip.id, gast, db_session)).id == trip.id
    # bearbeiten: nein
    with pytest.raises(HTTPException) as fehler:
        await verify_trip_access(trip.id, gast, db_session, require_edit=True)
    assert fehler.value.status_code == 403


@pytest.mark.asyncio
async def test_bearbeiter_darf_bearbeiten(db_session: AsyncSession, test_user: User):
    trip = await _reise_anlegen(db_session, test_user.id)
    gast = await _zweiter_nutzer(db_session, "bearbeiter")
    await _teilnehmer(db_session, trip, gast, permission=PermissionLevel.EDITOR.value)
    assert (await verify_trip_access(trip.id, gast, db_session, require_edit=True)).id == trip.id


@pytest.mark.asyncio
async def test_teilnehmer_einer_ANDEREN_reise_darf_nicht(db_session: AsyncSession, test_user: User):
    """Positivkontrolle gegen einen zu weit gefassten Abgleich: die
    Teilnahme muss an DIESER Reise hängen, nicht an irgendeiner."""
    reise_a = await _reise_anlegen(db_session, test_user.id, "A")
    reise_b = await _reise_anlegen(db_session, test_user.id, "B")
    gast = await _zweiter_nutzer(db_session, "nurbeiA")
    await _teilnehmer(db_session, reise_a, gast)
    assert (await verify_trip_access(reise_a.id, gast, db_session)).id == reise_a.id
    with pytest.raises(HTTPException) as fehler:
        await verify_trip_access(reise_b.id, gast, db_session)
    assert fehler.value.status_code == 403


class _Eintrag:
    """Minimaler Ersatz für DiaryEntry — verify_diary_entry_access liest nur
    diese drei Felder, und ein echtes Modell würde den Test an Spalten binden,
    über die er nichts aussagt."""

    def __init__(self, entry_id: int, trip_id: int, author_id: int):
        self.id = entry_id
        self.trip_id = trip_id
        self.author_id = author_id


@pytest.mark.asyncio
async def test_autor_darf_seinen_eintrag_bearbeiten(db_session: AsyncSession, test_user: User):
    trip = await _reise_anlegen(db_session, test_user.id)
    eintrag = _Eintrag(1, trip.id, test_user.id)
    assert await verify_diary_entry_access(eintrag, test_user, db_session, require_author=True) is True


@pytest.mark.asyncio
async def test_fremder_darf_eintrag_NICHT_bearbeiten(db_session: AsyncSession, test_user: User):
    trip = await _reise_anlegen(db_session, test_user.id)
    fremder = await _zweiter_nutzer(db_session, "nichtautor")
    eintrag = _Eintrag(1, trip.id, test_user.id)
    with pytest.raises(HTTPException) as fehler:
        await verify_diary_entry_access(eintrag, fremder, db_session, require_author=True)
    assert fehler.value.status_code == 403


@pytest.mark.asyncio
async def test_mitreisender_darf_fremden_eintrag_LESEN(db_session: AsyncSession, test_user: User):
    """Ohne require_author entscheidet der Zugriff auf die REISE."""
    trip = await _reise_anlegen(db_session, test_user.id)
    gast = await _zweiter_nutzer(db_session, "mitleser")
    await _teilnehmer(db_session, trip, gast)
    eintrag = _Eintrag(1, trip.id, test_user.id)
    assert await verify_diary_entry_access(eintrag, gast, db_session) is True


@pytest.mark.asyncio
async def test_unbeteiligter_darf_eintrag_nicht_lesen(db_session: AsyncSession, test_user: User):
    trip = await _reise_anlegen(db_session, test_user.id)
    fremder = await _zweiter_nutzer(db_session, "unbeteiligt")
    eintrag = _Eintrag(1, trip.id, test_user.id)
    with pytest.raises(HTTPException) as fehler:
        await verify_diary_entry_access(eintrag, fremder, db_session)
    assert fehler.value.status_code == 403
