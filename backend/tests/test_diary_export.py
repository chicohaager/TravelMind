"""
Wächter für das Reisetagebuch (`routes/diary.py`, vorher 30 % gedeckt — die
größte einzelne Lücke im Backend).

Zwei Schwerpunkte:

1. **Zugriff.** Die Änderungs- und Löschendpunkte adressieren einen Eintrag
   über SEINE ID (`PUT /api/diary/{entry_id}`), nicht über die Reise. Ohne
   Prüfung ist das fremde Tagebücher zum Mitlesen und Ändern.
2. **Export.** Markdown und PDF sind die einzige Möglichkeit, die Texte aus
   der Anwendung herauszubekommen. Ein leerer oder halber Export fällt
   niemandem auf, solange er eine Datei erzeugt — deshalb wird hier der
   INHALT geprüft.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from models.diary import DiaryEntry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

EINTRAG = {
    "title": "Tag 1 in Lissabon",
    "content": "# Ankunft\n\nEin wundervoller Tag in der Alfama.",
    "entry_date": "2026-09-01T10:00:00",
    "location_name": "Alfama",
    "mood": "happy",
    "rating": 5,
    "tags": ["food", "sunset"],
}


@pytest_asyncio.fixture
async def eintrag(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.post(f"/api/diary/{test_trip.id}", headers=auth_headers, json=EINTRAG)
    assert antwort.status_code == 201, antwort.text
    return antwort.json()


# ── Grundfunktionen ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_neue_reise_hat_kein_tagebuch(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.get(f"/api/diary/{test_trip.id}", headers=auth_headers)
    assert antwort.status_code == 200
    assert antwort.json() == []


@pytest.mark.asyncio
async def test_eintrag_anlegen_und_wiederfinden(client: AsyncClient, auth_headers, test_trip, eintrag):
    liste = (await client.get(f"/api/diary/{test_trip.id}", headers=auth_headers)).json()
    assert [e["title"] for e in liste] == [EINTRAG["title"]]
    assert liste[0]["mood"] == "happy"
    assert liste[0]["rating"] == 5
    assert liste[0]["tags"] == ["food", "sunset"]


@pytest.mark.asyncio
async def test_eintrag_aendern(client: AsyncClient, auth_headers, eintrag):
    antwort = await client.put(
        f"/api/diary/{eintrag['id']}", headers=auth_headers, json={"title": "Geändert", "content": "Neuer Text"}
    )
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["title"] == "Geändert"


@pytest.mark.asyncio
async def test_eintrag_loeschen(client: AsyncClient, auth_headers, eintrag, db_session: AsyncSession):
    weg = await client.delete(f"/api/diary/{eintrag['id']}", headers=auth_headers)
    assert weg.status_code == 204
    uebrig = (await db_session.execute(select(DiaryEntry).where(DiaryEntry.id == eintrag["id"]))).scalar_one_or_none()
    assert uebrig is None


@pytest.mark.asyncio
async def test_unmoegliche_bewertung_wird_abgewiesen(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.post(f"/api/diary/{test_trip.id}", headers=auth_headers, json={**EINTRAG, "rating": 6})
    assert antwort.status_code == 422


@pytest.mark.asyncio
async def test_unbekannter_eintrag_ergibt_404(client: AsyncClient, auth_headers):
    assert (
        await client.put("/api/diary/999999", headers=auth_headers, json={"title": "X", "content": "Y"})
    ).status_code == 404


# ── Zugriffsschutz (IDOR) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fremder_liest_kein_tagebuch(client: AsyncClient, other_auth_headers, test_trip, eintrag):
    assert (await client.get(f"/api/diary/{test_trip.id}", headers=other_auth_headers)).status_code == 403


@pytest.mark.asyncio
async def test_fremder_schreibt_keinen_eintrag(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.post(f"/api/diary/{test_trip.id}", headers=other_auth_headers, json=EINTRAG)
    assert antwort.status_code == 403


@pytest.mark.asyncio
async def test_fremder_aendert_keinen_eintrag(client: AsyncClient, other_auth_headers, eintrag):
    antwort = await client.put(
        f"/api/diary/{eintrag['id']}", headers=other_auth_headers, json={"title": "Gekapert", "content": "x"}
    )
    assert antwort.status_code in (403, 404)


@pytest.mark.asyncio
async def test_fremder_loescht_keinen_eintrag(client: AsyncClient, other_auth_headers, eintrag, db_session):
    antwort = await client.delete(f"/api/diary/{eintrag['id']}", headers=other_auth_headers)
    assert antwort.status_code in (403, 404)
    uebrig = (await db_session.execute(select(DiaryEntry).where(DiaryEntry.id == eintrag["id"]))).scalar_one_or_none()
    assert uebrig is not None


@pytest.mark.asyncio
async def test_ohne_anmeldung_kein_tagebuch(client: AsyncClient, test_trip):
    assert (await client.get(f"/api/diary/{test_trip.id}")).status_code == 401


# ── Export ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_markdown_export_enthaelt_den_text(client: AsyncClient, auth_headers, test_trip, eintrag):
    antwort = await client.get(f"/api/diary/{test_trip.id}/export/markdown", headers=auth_headers)
    assert antwort.status_code == 200, antwort.text
    text = antwort.text
    # Der Inhalt, nicht nur der Statuscode:
    assert test_trip.title in text
    assert test_trip.destination in text
    assert EINTRAG["title"] in text
    assert "Alfama" in text
    assert "01.09.2026" in text
    assert "⭐⭐⭐⭐⭐" in text


@pytest.mark.asyncio
async def test_markdown_export_ohne_eintraege_ergibt_404(client: AsyncClient, auth_headers, test_trip):
    """Ein leerer Export ist eine Datei, die aussieht wie ein Ergebnis.
    Besser laut scheitern."""
    antwort = await client.get(f"/api/diary/{test_trip.id}/export/markdown", headers=auth_headers)
    assert antwort.status_code == 404


@pytest.mark.asyncio
async def test_markdown_export_bringt_alle_eintraege(client: AsyncClient, auth_headers, test_trip):
    for i, titel in enumerate(("Erster Tag", "Zweiter Tag", "Dritter Tag")):
        await client.post(
            f"/api/diary/{test_trip.id}",
            headers=auth_headers,
            json={**EINTRAG, "title": titel, "entry_date": f"2026-09-0{i + 1}T10:00:00"},
        )
    text = (await client.get(f"/api/diary/{test_trip.id}/export/markdown", headers=auth_headers)).text
    for titel in ("Erster Tag", "Zweiter Tag", "Dritter Tag"):
        assert titel in text, f"{titel} fehlt im Export"
    # Reihenfolge nach Datum, nicht nach Anlagezeitpunkt.
    assert text.index("Erster Tag") < text.index("Zweiter Tag") < text.index("Dritter Tag")


@pytest.mark.asyncio
async def test_pdf_export_liefert_ein_pdf(client: AsyncClient, auth_headers, test_trip, eintrag):
    antwort = await client.get(f"/api/diary/{test_trip.id}/export/pdf", headers=auth_headers)
    assert antwort.status_code == 200, antwort.text[:300]
    # Eine PDF-Datei beginnt mit %PDF- — ein Statuscode allein sagt nichts
    # darueber, ob der Inhalt eine ist.
    assert antwort.content[:5] == b"%PDF-", antwort.content[:40]
    assert len(antwort.content) > 800


@pytest.mark.asyncio
async def test_fremder_exportiert_nicht(client: AsyncClient, other_auth_headers, test_trip, eintrag):
    assert (
        await client.get(f"/api/diary/{test_trip.id}/export/markdown", headers=other_auth_headers)
    ).status_code == 403
