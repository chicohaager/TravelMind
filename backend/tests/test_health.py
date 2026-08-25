"""
Wächter für die Zustandsauskunft.

Sie ist die Grundlage der Überwachung: `deploy/waechter/waechter.sh` und der
Docker-Healthcheck entscheiden anhand dieser Antworten, ob TravelMind läuft.
Gedeckt war sie zu 43 % — ausgerechnet die Teilprüfungen (Datenbank, Platte,
Speicher, Upload-Verzeichnis) liefen ungeprüft.

Geprüft wird der INHALT, nicht der Statuscode: eine 200 mit
`"status":"unhealthy"` ist genau der Fall, den der Wächter erkennen muss.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ausfuehrliche_auskunft_meldet_gesund(client: AsyncClient):
    antwort = await client.get("/api/health")
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["status"] == "healthy"
    assert daten["version"]
    assert daten["timestamp"]


@pytest.mark.asyncio
async def test_auskunft_nennt_alle_teilpruefungen(client: AsyncClient):
    daten = (await client.get("/api/health")).json()
    for teil in ("database", "disk", "memory", "uploads"):
        assert teil in daten["components"], f"{teil} fehlt in der Auskunft"
        assert "status" in daten["components"][teil]


@pytest.mark.asyncio
async def test_datenbank_wird_wirklich_abgefragt(client: AsyncClient):
    """Positivkontrolle gegen eine fest verdrahtete Antwort: die Teilprüfung
    misst eine Antwortzeit, die es ohne echte Abfrage nicht gäbe."""
    daten = (await client.get("/api/health")).json()
    db = daten["components"]["database"]
    assert db["status"] == "healthy"
    assert db.get("latency_ms") is not None


@pytest.mark.asyncio
async def test_systemwerte_werden_gemeldet(client: AsyncClient):
    daten = (await client.get("/api/health")).json()
    system = daten["system"]
    assert system["cpu_percent"] >= 0
    assert system["memory_percent"] > 0
    assert system["disk_percent"] > 0


@pytest.mark.asyncio
async def test_lebendigkeit_antwortet_ohne_datenbank(client: AsyncClient):
    antwort = await client.get("/api/health/live")
    assert antwort.status_code == 200
    assert antwort.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_bereitschaft_antwortet(client: AsyncClient):
    antwort = await client.get("/api/health/ready")
    assert antwort.status_code == 200
    assert antwort.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_faehigkeiten_werden_gemeldet(client: AsyncClient):
    antwort = await client.get("/api/capabilities")
    assert antwort.status_code == 200
    assert isinstance(antwort.json(), dict)


@pytest.mark.asyncio
async def test_es_gibt_die_auskunft_auch_ohne_praefix(client: AsyncClient):
    """`/health` UND `/api/health` sind beide angemeldet — der Healthcheck des
    Containers benutzt den einen, nginx den anderen. Fällt einer weg, merkt es
    sonst niemand, bis die Überwachung falsch meldet."""
    ohne = await client.get("/health")
    assert ohne.status_code == 200
    assert ohne.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_kaputte_datenbank_faellt_auf(client: AsyncClient, monkeypatch):
    """Die Prüfung muss ROT werden können. Ohne diesen Fall wäre alles oben
    auch dann grün, wenn die Teilprüfung eine Konstante zurückgäbe."""
    import routes.health as health_modul

    async def kaputt(db):
        raise RuntimeError("Verbindung weg")

    monkeypatch.setattr(health_modul, "check_database", kaputt, raising=True)
    antwort = await client.get("/api/health")
    # Der Endpunkt darf NICHT abstürzen — sonst nimmt der Ausfall genau die
    # Auskunft mit, die sagen soll, was ausgefallen ist.
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["status"] == "unhealthy"
    assert daten["components"]["database"]["status"] == "unhealthy"
    assert "RuntimeError" in daten["components"]["database"]["message"]
    # Gegenkontrolle: die übrigen Teilprüfungen laufen weiter.
    assert daten["components"]["disk"]["status"] in ("healthy", "degraded")
