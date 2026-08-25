"""
Wächter für den Reiseführer-Parser (`services/guide_parser.py`, vorher 20 %).

Das Modul hat eine Eigenschaft, die es gefährlich macht: **jeder Fehlerpfad
gibt eine leere Liste zurück**, und eine leere Liste sieht aus wie „nichts
gefunden". Netz aus, Seite leer, KI antwortet Unsinn — die Oberfläche zeigt
dreimal dasselbe. Deshalb wird hier für jeden dieser Wege einzeln
festgehalten, WAS zurückkommt, damit ein Umbau auf eine ehrliche
Fehlermeldung sichtbar wird und nicht unbemerkt bleibt.

Kein Test geht ins Netz und keiner ruft Claude auf.
"""

import json

import httpx
import pytest
from services.guide_parser import GuideParserService


@pytest.fixture
def parser():
    return GuideParserService()


# ── Text aus HTML ───────────────────────────────────────────────────────────


def test_text_wird_aus_html_geholt(parser):
    html = "<html><body><h1>Lissabon</h1><p>Alfama ist schön.</p></body></html>"
    text = parser.extract_text_from_html(html)
    assert "Lissabon" in text
    assert "Alfama ist schön." in text


def test_skripte_navigation_und_fusszeile_fliegen_raus(parser):
    """Ohne das landet der Seitenrahmen im KI-Prompt und kostet dort Platz,
    den der eigentliche Inhalt braucht."""
    html = """<html><head><style>.x{color:red}</style></head><body>
      <nav>Startseite Kontakt Impressum</nav>
      <script>var werbung = 1;</script>
      <p>Torre de Belém am Tejo.</p>
      <footer>Alle Rechte vorbehalten</footer>
    </body></html>"""
    text = parser.extract_text_from_html(html)
    assert "Torre de Belém" in text
    for unerwuenscht in ("Startseite", "var werbung", "Alle Rechte vorbehalten", "color:red"):
        assert unerwuenscht not in text, f"{unerwuenscht!r} steht noch im Text"


def test_leeres_html_ergibt_leeren_text(parser):
    assert parser.extract_text_from_html("") == ""


# ── Quelle erkennen ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url,erwartet",
    [
        ("https://www.tripadvisor.com/Attractions-g189158", "tripadvisor"),
        ("https://www.TripAdvisor.de/x", "tripadvisor"),
        ("https://www.lonelyplanet.com/portugal/lisbon", "lonelyplanet"),
        ("https://www.timeout.com/lisbon", "timeout"),
        ("https://wanderlog.com/list/x", "wanderlog"),
        ("https://www.google.com/travel/things-to-do", "google_travel"),
        ("https://ein-reiseblog.example/lissabon", "generic"),
    ],
)
def test_quelle_wird_an_der_adresse_erkannt(parser, url, erwartet):
    assert parser.detect_guide_type(url) == erwartet


# ── Adressen erzeugen ───────────────────────────────────────────────────────


def test_bekanntes_ziel_bekommt_eine_direkte_adresse(parser):
    urls = parser.generate_guide_urls("Paris")
    assert urls[0]["source"] == "TripAdvisor"
    assert "Attractions-g187147" in urls[0]["url"]


def test_gross_klein_und_leerzeichen_stoeren_nicht(parser):
    assert parser.generate_guide_urls("  NEW YORK ")[0]["url"] == parser.generate_guide_urls("new york")[0]["url"]


def test_unbekanntes_ziel_faellt_auf_die_suche_zurueck(parser):
    urls = parser.generate_guide_urls("Kleinkleckersdorf")
    assert "/Search?q=" in urls[0]["url"]


def test_sonderzeichen_werden_kodiert(parser):
    """Ohne Kodierung entsteht eine kaputte Adresse — und die Suche liefert
    dann plausibel aussehenden Unsinn."""
    url = parser.generate_guide_urls("São Miguel")[0]["url"]
    assert " " not in url
    assert "S%C3%A3o" in url


# ── Doppelte entfernen ──────────────────────────────────────────────────────


def test_doppelte_namen_werden_zusammengefasst(parser):
    orte = [{"name": "Torre de Belém"}, {"name": "  torre de belém  "}, {"name": "Castelo"}]
    assert [o["name"] for o in parser.deduplicate_places(orte)] == ["Torre de Belém", "Castelo"]


def test_der_erste_eintrag_gewinnt(parser):
    orte = [{"name": "Castelo", "description": "erste"}, {"name": "castelo", "description": "zweite"}]
    assert parser.deduplicate_places(orte)[0]["description"] == "erste"


def test_leere_liste_bleibt_leer(parser):
    assert parser.deduplicate_places([]) == []


# ── Abrufen (ohne Netz) ─────────────────────────────────────────────────────


class _Antwort:
    def __init__(self, text="<html><body>Torre de Belém</body></html>", fehler=None):
        self.text = text
        self._fehler = fehler

    def raise_for_status(self):
        if self._fehler:
            raise self._fehler


class _Klient:
    def __init__(self, antwort=None, ausnahme=None):
        self._antwort = antwort
        self._ausnahme = ausnahme

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get(self, url, headers=None, follow_redirects=False):
        if self._ausnahme:
            raise self._ausnahme
        return self._antwort


def _netz(monkeypatch, antwort=None, ausnahme=None):
    import services.guide_parser as modul

    monkeypatch.setattr(modul.httpx, "AsyncClient", lambda *a, **k: _Klient(antwort, ausnahme))


@pytest.mark.asyncio
async def test_abruf_liefert_den_seiteninhalt(parser, monkeypatch):
    _netz(monkeypatch, _Antwort("<html>Inhalt</html>"))
    assert await parser.fetch_url_content("https://example.com") == "<html>Inhalt</html>"


@pytest.mark.asyncio
async def test_netzfehler_ergibt_None(parser, monkeypatch):
    _netz(monkeypatch, ausnahme=httpx.ConnectError("kein Netz"))
    assert await parser.fetch_url_content("https://example.com") is None


@pytest.mark.asyncio
async def test_fehlerstatus_ergibt_None(parser, monkeypatch):
    _netz(monkeypatch, _Antwort(fehler=httpx.HTTPStatusError("403", request=None, response=None)))
    assert await parser.fetch_url_content("https://example.com") is None


# ── Ganzer Weg (KI ersetzt) ─────────────────────────────────────────────────


ORTE = [
    {"name": "Torre de Belém", "category": "attraction", "description": "Turm", "address": None},
    {"name": "Time Out Market", "category": "restaurant", "description": "Markthalle", "address": None},
]


@pytest.mark.asyncio
async def test_ganzer_weg_liefert_die_orte(parser, monkeypatch):
    _netz(monkeypatch, _Antwort("<html><body>Ein Text über Lissabon</body></html>"))

    async def ki(text, destination):
        assert "Lissabon" in text
        return ORTE

    monkeypatch.setattr(parser, "extract_places_with_ai", ki)
    ergebnis = await parser.parse_guide_url("https://example.com", "Lissabon")
    assert ergebnis["success"] is True
    assert ergebnis["places_found"] == 2
    assert [o["name"] for o in ergebnis["places"]] == [o["name"] for o in ORTE]


@pytest.mark.asyncio
async def test_ohne_seite_meldet_der_weg_einen_fehler(parser, monkeypatch):
    """Festgehalten, weil es der einzige Weg ist, auf dem der Ausfall NICHT
    stumm bleibt."""
    _netz(monkeypatch, ausnahme=httpx.ConnectError("kein Netz"))
    ergebnis = await parser.parse_guide_url("https://example.com", "Lissabon")
    assert ergebnis["success"] is False
    assert ergebnis["places"] == []
    assert "fetch" in ergebnis["error"].lower()


@pytest.mark.asyncio
async def test_leere_seite_meldet_ebenfalls_einen_fehler(parser, monkeypatch):
    _netz(monkeypatch, _Antwort("<html><body></body></html>"))
    ergebnis = await parser.parse_guide_url("https://example.com", "Lissabon")
    assert ergebnis["success"] is False
    assert "extract" in ergebnis["error"].lower()


@pytest.mark.asyncio
async def test_eine_quelle_scheitert_ohne_den_lauf_abzubrechen(parser, monkeypatch):
    async def kaputt(url, destination):
        raise RuntimeError("Quelle unerreichbar")

    monkeypatch.setattr(parser, "parse_guide_url", kaputt)
    ergebnis = await parser.search_single_source("TripAdvisor", "https://example.com", "Lissabon")
    assert ergebnis["source"] == "TripAdvisor"
    assert ergebnis["success"] is False
    assert ergebnis["places"] == []


# ── Antwort der KI auswerten ────────────────────────────────────────────────


class _Inhalt:
    def __init__(self, text):
        self.text = text


class _Nachricht:
    def __init__(self, text):
        self.content = [_Inhalt(text)]


def _claude_antwortet(parser, monkeypatch, text):
    class _Nachrichten:
        def create(self, **kwargs):
            return _Nachricht(text)

    class _Klient2:
        messages = _Nachrichten()

    monkeypatch.setattr(parser, "claude_client", _Klient2())


@pytest.mark.asyncio
async def test_saubere_json_antwort_wird_gelesen(parser, monkeypatch):
    _claude_antwortet(parser, monkeypatch, json.dumps(ORTE))
    assert await parser.extract_places_with_ai("Text", "Lissabon") == ORTE


@pytest.mark.asyncio
async def test_json_zwischen_geplauder_wird_herausgeschnitten(parser, monkeypatch):
    """Sprachmodelle stellen ihrer Antwort gern einen Satz voran. Ohne das
    Herausschneiden wäre jede solche Antwort ein Totalausfall."""
    _claude_antwortet(parser, monkeypatch, "Gerne! Hier sind die Orte:\n" + json.dumps(ORTE) + "\nViel Spaß!")
    assert await parser.extract_places_with_ai("Text", "Lissabon") == ORTE


@pytest.mark.asyncio
async def test_antwort_ohne_json_ergibt_eine_leere_liste(parser, monkeypatch):
    _claude_antwortet(parser, monkeypatch, "Dazu kann ich leider nichts sagen.")
    assert await parser.extract_places_with_ai("Text", "Lissabon") == []


@pytest.mark.asyncio
async def test_kaputtes_json_ergibt_eine_leere_liste(parser, monkeypatch):
    _claude_antwortet(parser, monkeypatch, '[{"name": "Torre", ')
    assert await parser.extract_places_with_ai("Text", "Lissabon") == []


@pytest.mark.asyncio
async def test_zu_langer_text_wird_gekuerzt(parser, monkeypatch):
    """15 000 Zeichen ist die Grenze im Code. Wird sie nicht eingehalten,
    lehnt Claude die Anfrage ab — und das Ergebnis ist wieder eine leere
    Liste, die wie 'nichts gefunden' aussieht."""
    gesehen = {}

    class _Nachrichten:
        def create(self, **kwargs):
            gesehen["prompt"] = kwargs["messages"][0]["content"]
            return _Nachricht(json.dumps(ORTE))

    class _Klient2:
        messages = _Nachrichten()

    monkeypatch.setattr(parser, "claude_client", _Klient2())
    await parser.extract_places_with_ai("x" * 50000, "Lissabon")
    assert "x" * 15001 not in gesehen["prompt"]
    assert "x" * 15000 in gesehen["prompt"]
