"""
Wächter für die Geokodierung (`utils/geocoding.py`, vorher 22 % gedeckt).

Die Fehlerpfade sind hier die eigentliche Gefahr: fällt Nominatim aus, gibt
`geocode_location` `None` zurück, und `geocode_if_missing` reicht dann die
URSPRÜNGLICHEN Koordinaten durch — also (0,0), den Punkt im Golf von Guinea.
Ein Ort landet dort auf der Karte, ohne dass irgendetwas nach einem Fehler
aussieht. Genau dieses Verhalten wird hier festgenagelt, damit es niemand
versehentlich ändert und niemand es versehentlich für einen Erfolg hält.

Kein Test hier geht ins Netz: `httpx.AsyncClient` wird ersetzt. Ein Test, der
von einem fremden Dienst abhängt, wird sporadisch rot und irgendwann
übersprungen.
"""

import httpx
import pytest
from utils import geocoding


class _Antwort:
    def __init__(self, nutzlast, fehler=None):
        self._nutzlast = nutzlast
        self._fehler = fehler

    def raise_for_status(self):
        if self._fehler:
            raise self._fehler

    def json(self):
        return self._nutzlast


class _Klient:
    """Ersatz für httpx.AsyncClient. Merkt sich die letzte Anfrage, damit die
    Tests prüfen können, WONACH gesucht wurde — nicht nur, dass gesucht wurde."""

    letzte_params = None

    def __init__(self, antwort=None, ausnahme=None):
        self._antwort = antwort
        self._ausnahme = ausnahme

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get(self, url, params=None, headers=None):
        type(self).letzte_params = params
        if self._ausnahme:
            raise self._ausnahme
        return self._antwort


@pytest.fixture(autouse=True)
def ohne_wartezeit(monkeypatch):
    """Nominatim erlaubt eine Anfrage je Sekunde; der Code hält das ein. In
    Tests ist das eine Sekunde Leerlauf je Treffer."""

    async def sofort(_):
        return None

    monkeypatch.setattr(geocoding.asyncio, "sleep", sofort)


def _klient_liefert(monkeypatch, nutzlast=None, ausnahme=None):
    antwort = _Antwort(nutzlast if nutzlast is not None else [])
    monkeypatch.setattr(geocoding.httpx, "AsyncClient", lambda *a, **k: _Klient(antwort=antwort, ausnahme=ausnahme))


TREFFER = [{"lat": "38.7139", "lon": "-9.1334", "display_name": "Castelo de São Jorge, Lissabon"}]


@pytest.mark.asyncio
async def test_treffer_wird_als_zahlenpaar_geliefert(monkeypatch):
    _klient_liefert(monkeypatch, TREFFER)
    assert await geocoding.geocode_location("Castelo") == (38.7139, -9.1334)


@pytest.mark.asyncio
async def test_ohne_treffer_kommt_None(monkeypatch):
    _klient_liefert(monkeypatch, [])
    assert await geocoding.geocode_location("Gibt es nicht") is None


@pytest.mark.asyncio
async def test_das_reiseziel_wird_an_die_suche_angehaengt(monkeypatch):
    _klient_liefert(monkeypatch, TREFFER)
    await geocoding.geocode_location("Castelo", destination="Lissabon")
    assert _Klient.letzte_params["q"] == "Castelo, Lissabon"


@pytest.mark.asyncio
async def test_eine_vollstaendige_adresse_schlaegt_den_namen(monkeypatch):
    _klient_liefert(monkeypatch, TREFFER)
    await geocoding.geocode_location("Castelo", address="R. de Santa Cruz, Lissabon", destination="Porto")
    assert _Klient.letzte_params["q"] == "R. de Santa Cruz, Lissabon"


@pytest.mark.asyncio
async def test_netzfehler_ergibt_None_statt_einer_ausnahme(monkeypatch):
    _klient_liefert(monkeypatch, ausnahme=httpx.ConnectError("kein Netz"))
    assert await geocoding.geocode_location("Castelo") is None


@pytest.mark.asyncio
async def test_unerwarteter_fehler_ergibt_ebenfalls_None(monkeypatch):
    _klient_liefert(monkeypatch, ausnahme=ValueError("kaputte Antwort"))
    assert await geocoding.geocode_location("Castelo") is None


@pytest.mark.asyncio
async def test_vorhandene_koordinaten_werden_nicht_angefasst(monkeypatch):
    def darf_nicht_aufgerufen_werden(*a, **k):
        raise AssertionError("Es wurde geokodiert, obwohl Koordinaten vorlagen")

    monkeypatch.setattr(geocoding.httpx, "AsyncClient", darf_nicht_aufgerufen_werden)
    assert await geocoding.geocode_if_missing("Castelo", 38.7, -9.1) == (38.7, -9.1)


@pytest.mark.asyncio
async def test_nullkoordinaten_werden_nachgeschlagen(monkeypatch):
    _klient_liefert(monkeypatch, TREFFER)
    assert await geocoding.geocode_if_missing("Castelo", 0.0, 0.0) == (38.7139, -9.1334)


@pytest.mark.asyncio
async def test_fehlgeschlagene_suche_laesst_die_NULLKOORDINATEN_stehen(monkeypatch):
    """Festgehaltenes Verhalten, kein Lob: der Ort landet damit bei (0,0) im
    Golf von Guinea, und nichts an der Antwort sieht nach einem Fehler aus.
    Wer das ändert, ändert diesen Test und sieht dabei, was er ändert."""
    _klient_liefert(monkeypatch, [])
    assert await geocoding.geocode_if_missing("Gibt es nicht", 0.0, 0.0) == (0.0, 0.0)


@pytest.mark.asyncio
async def test_stapel_geokodiert_nur_die_fehlenden(monkeypatch):
    _klient_liefert(monkeypatch, TREFFER)
    orte = [
        {"name": "Mit Koordinaten", "latitude": 41.15, "longitude": -8.61},
        {"name": "Ohne Koordinaten", "latitude": 0.0, "longitude": 0.0},
    ]
    ergebnis = await geocoding.batch_geocode_places(orte, destination="Lissabon")
    assert ergebnis[0]["latitude"] == 41.15
    assert ergebnis[1]["latitude"] == 38.7139
    # Die Eingabe darf nicht verändert werden.
    assert orte[1]["latitude"] == 0.0
