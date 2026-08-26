"""
Wächter für die Kostenaufteilung (`routes/budget.py`, vorher 45 % gedeckt).

Beim Geld ist eine falsche Zahl gefährlicher als ein Fehler: sie sieht aus wie
ein Ergebnis. Geprüft wird deshalb nicht, dass eine Summe zurückkommt, sondern
dass sie **auf den Cent aufgeht** — insbesondere bei Beträgen, die sich nicht
glatt teilen lassen (100 € auf 3 Personen), und dass die Salden **auf null
saldieren**. Genau daran scheitert eine naive Rundung.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from models.expense import Expense
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def drei_teilnehmer(client: AsyncClient, auth_headers, test_trip):
    ids = []
    for name in ("Anna", "Bert", "Cem"):
        angelegt = await client.post(
            f"/api/trips/{test_trip.id}/participants", headers=auth_headers, json={"name": name}
        )
        assert angelegt.status_code == 201, angelegt.text
        ids.append(angelegt.json()["id"])
    return ids


# ── Ausgaben ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_neue_reise_hat_keine_ausgaben(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.get(f"/api/budget/{test_trip.id}/expenses", headers=auth_headers)
    assert antwort.status_code == 200
    assert antwort.json() == []


@pytest.mark.asyncio
async def test_ausgabe_anlegen(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.post(
        f"/api/budget/{test_trip.id}/expenses",
        headers=auth_headers,
        json={"title": "Abendessen", "amount": 42.5, "category": "food", "date": "2026-09-02"},
    )
    assert antwort.status_code == 201, antwort.text
    assert antwort.json()["title"] == "Abendessen"


@pytest.mark.asyncio
async def test_ausgabe_ohne_teilnehmer_ist_erlaubt(client: AsyncClient, auth_headers, test_trip):
    """Alleinreisende haben keine Teilnehmer — `paid_by` ist deshalb optional."""
    antwort = await client.post(
        f"/api/budget/{test_trip.id}/expenses",
        headers=auth_headers,
        json={"title": "Bahnticket", "amount": 19.9, "date": "2026-09-01"},
    )
    assert antwort.status_code == 201, antwort.text
    liste = (await client.get(f"/api/budget/{test_trip.id}/expenses", headers=auth_headers)).json()
    assert liste[0]["paid_by_name"] == "Unbekannt"


@pytest.mark.asyncio
async def test_ausgabe_aendern(client: AsyncClient, auth_headers, test_trip):
    angelegt = (
        await client.post(
            f"/api/budget/{test_trip.id}/expenses",
            headers=auth_headers,
            json={"title": "Alt", "amount": 10.0, "date": "2026-09-01"},
        )
    ).json()
    antwort = await client.put(
        f"/api/budget/expenses/{angelegt['id']}", headers=auth_headers, json={"title": "Neu", "amount": 20.0}
    )
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["amount"] == 20.0


@pytest.mark.asyncio
async def test_ausgabe_loeschen(client: AsyncClient, auth_headers, test_trip, db_session: AsyncSession):
    angelegt = (
        await client.post(
            f"/api/budget/{test_trip.id}/expenses",
            headers=auth_headers,
            json={"title": "Weg", "amount": 5.0, "date": "2026-09-01"},
        )
    ).json()
    weg = await client.delete(f"/api/budget/expenses/{angelegt['id']}", headers=auth_headers)
    assert weg.status_code == 204
    uebrig = (await db_session.execute(select(Expense).where(Expense.id == angelegt["id"]))).scalar_one_or_none()
    assert uebrig is None


@pytest.mark.asyncio
async def test_seitenweises_abrufen(client: AsyncClient, auth_headers, test_trip):
    for i in range(5):
        await client.post(
            f"/api/budget/{test_trip.id}/expenses",
            headers=auth_headers,
            json={"title": f"Posten {i}", "amount": 1.0 + i, "date": "2026-09-01"},
        )
    seite = (await client.get(f"/api/budget/{test_trip.id}/expenses?skip=2&limit=2", headers=auth_headers)).json()
    assert len(seite) == 2


# ── Gleiche Aufteilung ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_glatte_aufteilung(client: AsyncClient, auth_headers, test_trip, drei_teilnehmer):
    antwort = await client.post(
        f"/api/budget/{test_trip.id}/expenses/split-equally"
        f"?title=Taxi&amount=90&category=transport&paid_by={drei_teilnehmer[0]}",
        headers=auth_headers,
    )
    assert antwort.status_code == 201, antwort.text
    splits = antwort.json()["splits"]
    assert [s["amount"] for s in splits] == [30.0, 30.0, 30.0]


@pytest.mark.asyncio
async def test_unteilbarer_betrag_geht_auf_den_cent_auf(client: AsyncClient, auth_headers, test_trip, drei_teilnehmer):
    """100 / 3 = 33,333… Eine naive Rundung ergibt 3 × 33,33 = 99,99 — ein
    fehlender Cent, der in jeder Abrechnung als Ungleichgewicht auftaucht."""
    antwort = await client.post(
        f"/api/budget/{test_trip.id}/expenses/split-equally"
        f"?title=Hotel&amount=100&category=accommodation&paid_by={drei_teilnehmer[0]}",
        headers=auth_headers,
    )
    assert antwort.status_code == 201, antwort.text
    betraege = [s["amount"] for s in antwort.json()["splits"]]
    assert sum(betraege) == pytest.approx(100.0, abs=0.001), betraege
    assert betraege == [33.33, 33.33, 33.34], betraege


@pytest.mark.asyncio
async def test_aufteilung_ohne_teilnehmer_wird_abgewiesen(client: AsyncClient, auth_headers, test_trip):
    antwort = await client.post(
        f"/api/budget/{test_trip.id}/expenses/split-equally?title=X&amount=10&category=other&paid_by=1",
        headers=auth_headers,
    )
    assert antwort.status_code == 400


@pytest.mark.asyncio
async def test_unbekannter_zahler_wird_abgewiesen(client: AsyncClient, auth_headers, test_trip, drei_teilnehmer):
    antwort = await client.post(
        f"/api/budget/{test_trip.id}/expenses/split-equally?title=X&amount=10&category=other&paid_by=999999",
        headers=auth_headers,
    )
    assert antwort.status_code == 404


# ── Zusammenfassung ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_leere_zusammenfassung(client: AsyncClient, auth_headers, test_trip):
    daten = (await client.get(f"/api/budget/{test_trip.id}/budget-summary", headers=auth_headers)).json()
    assert daten["total_expenses"] == 0
    assert daten["currency"] == "EUR"


@pytest.mark.asyncio
async def test_zusammenfassung_summiert_nach_kategorie(client: AsyncClient, auth_headers, test_trip):
    for titel, betrag, kategorie in [("Essen 1", 20.0, "food"), ("Essen 2", 12.5, "food"), ("Bahn", 7.5, "transport")]:
        await client.post(
            f"/api/budget/{test_trip.id}/expenses",
            headers=auth_headers,
            json={"title": titel, "amount": betrag, "category": kategorie, "date": "2026-09-01"},
        )
    daten = (await client.get(f"/api/budget/{test_trip.id}/budget-summary", headers=auth_headers)).json()
    assert daten["total_expenses"] == pytest.approx(40.0)
    assert daten["by_category"]["food"] == pytest.approx(32.5)
    assert daten["by_category"]["transport"] == pytest.approx(7.5)


@pytest.mark.asyncio
async def test_salden_gehen_auf_null_auf(client: AsyncClient, auth_headers, test_trip, drei_teilnehmer):
    """Die entscheidende Eigenschaft einer Abrechnung: was einer zu viel
    gezahlt hat, schulden die anderen — die Summe aller Salden ist 0. Genau
    das bricht, wenn der Rundungsrest verschwindet."""
    anna, bert, cem = drei_teilnehmer
    await client.post(
        f"/api/budget/{test_trip.id}/expenses/split-equally"
        f"?title=Hotel&amount=100&category=accommodation&paid_by={anna}",
        headers=auth_headers,
    )
    await client.post(
        f"/api/budget/{test_trip.id}/expenses/split-equally"
        f"?title=Mietwagen&amount=55.55&category=transport&paid_by={bert}",
        headers=auth_headers,
    )
    daten = (await client.get(f"/api/budget/{test_trip.id}/budget-summary", headers=auth_headers)).json()
    salden = [p["balance"] for p in daten["by_participant"].values()]
    assert sum(salden) == pytest.approx(0.0, abs=0.005), daten["by_participant"]
    # Positivkontrolle: es darf nicht deshalb aufgehen, weil alles null ist.
    assert any(abs(s) > 1 for s in salden), salden
    assert daten["total_expenses"] == pytest.approx(155.55)
    # Wer nichts gezahlt hat, schuldet seinen Anteil an BEIDEN Posten.
    assert daten["by_participant"][str(cem)]["paid"] == pytest.approx(0.0)
    assert daten["by_participant"][str(cem)]["owes"] > 0


# ── Zugriffsschutz ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fremder_sieht_keine_ausgaben(client: AsyncClient, other_auth_headers, test_trip):
    assert (await client.get(f"/api/budget/{test_trip.id}/expenses", headers=other_auth_headers)).status_code == 403


@pytest.mark.asyncio
async def test_fremder_legt_keine_ausgabe_an(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.post(
        f"/api/budget/{test_trip.id}/expenses",
        headers=other_auth_headers,
        json={"title": "Fremd", "amount": 1.0, "date": "2026-09-01"},
    )
    assert antwort.status_code == 403


@pytest.mark.asyncio
async def test_fremder_sieht_keine_zusammenfassung(client: AsyncClient, other_auth_headers, test_trip):
    antwort = await client.get(f"/api/budget/{test_trip.id}/budget-summary", headers=other_auth_headers)
    assert antwort.status_code == 403


@pytest.mark.asyncio
async def test_ohne_anmeldung_kein_budget(client: AsyncClient, test_trip):
    assert (await client.get(f"/api/budget/{test_trip.id}/expenses")).status_code == 401
