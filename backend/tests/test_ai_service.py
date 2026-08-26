"""
Wächter für die KI-Anbindung (`services/ai_service.py`, vorher 25 %).

Der Dienst hat dieselbe gefährliche Eigenschaft wie der Reiseführer-Parser:
Antwortet das Modell nicht in der erwarteten Form, kommt eine **leere Liste**
oder ein leeres `destinations` zurück. Auf dem Bildschirm steht dann „keine
Vorschläge" — nicht zu unterscheiden von „das Modell hat nichts gefunden"
oder „der Schlüssel ist abgelaufen".

Zusätzlich wird die Antwortauswertung gegen die Formen geprüft, in denen
Sprachmodelle tatsächlich antworten: JSON mit Vorrede, JSON in einem
Markdown-Block, JSON mit Nachsatz. Genau daran scheitert eine naive
`json.loads`-Zeile.

Kein Test ruft einen fremden Dienst auf.
"""

import json

import pytest
from services.ai_service import (
    ClaudeProvider,
    GeminiProvider,
    GroqProvider,
    OpenAIProvider,
    UnifiedAIService,
    create_ai_service,
)


class _Antwortender:
    """Ersatz-Anbieter. Merkt sich den Prompt, damit geprüft werden kann,
    WONACH gefragt wurde."""

    def __init__(self, antwort: str):
        self.antwort = antwort
        self.letzter_prompt = None
        self.letztes_system = None
        self.letzte_tokens = None

    async def chat(self, prompt, system_prompt=None, max_tokens=2048):
        self.letzter_prompt = prompt
        self.letztes_system = system_prompt
        self.letzte_tokens = max_tokens
        return self.antwort


def _dienst(antwort):
    anbieter = _Antwortender(antwort)
    return UnifiedAIService(anbieter), anbieter


ZIELE = {
    "destinations": [
        {"name": "Lissabon", "country": "Portugal", "reason": "Licht", "activities": ["a", "b", "c"]},
    ]
}
TIPPS = [{"name": "Tasca do Chico", "category": "restaurants", "description": "Fado"}]


# ── Auswahl des Anbieters ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name,klasse",
    [
        ("claude", ClaudeProvider),
        ("CLAUDE", ClaudeProvider),
        ("openai", OpenAIProvider),
        ("gemini", GeminiProvider),
        ("groq", GroqProvider),
    ],
)
def test_anbieter_wird_am_namen_gewaehlt(name, klasse):
    dienst = create_ai_service(name, "ein-schluessel")
    assert isinstance(dienst.provider, klasse)


def test_unbekannter_anbieter_scheitert_LAUT():
    """Kein stiller Rückfall auf einen Standardanbieter: sonst zahlt jemand
    unbemerkt bei einem anderen Dienst."""
    with pytest.raises(ValueError) as fehler:
        create_ai_service("skynet", "ein-schluessel")
    assert "skynet" in str(fehler.value).lower()


# ── Antwortauswertung: die Formen, in denen Modelle wirklich antworten ──────


@pytest.mark.asyncio
async def test_sauberes_json_wird_gelesen():
    dienst, _ = _dienst(json.dumps(ZIELE))
    assert (await dienst.suggest_destinations(["Kultur"], 7))["destinations"][0]["name"] == "Lissabon"


@pytest.mark.asyncio
async def test_json_mit_vorrede_wird_gelesen():
    dienst, _ = _dienst("Gerne! Hier sind meine Vorschläge:\n" + json.dumps(ZIELE))
    assert (await dienst.suggest_destinations(["Kultur"], 7))["destinations"][0]["name"] == "Lissabon"


@pytest.mark.asyncio
async def test_json_im_markdown_block_wird_gelesen():
    dienst, _ = _dienst("```json\n" + json.dumps(ZIELE) + "\n```")
    assert (await dienst.suggest_destinations(["Kultur"], 7))["destinations"][0]["name"] == "Lissabon"


@pytest.mark.asyncio
async def test_antwort_ohne_json_liefert_den_rohtext_mit():
    """Wichtig: der Rohtext bleibt erhalten. Ohne ihn wäre nicht zu
    unterscheiden, ob das Modell nichts fand oder etwas anderes sagte."""
    dienst, _ = _dienst("Dazu kann ich nichts sagen.")
    ergebnis = await dienst.suggest_destinations(["Kultur"], 7)
    assert ergebnis["destinations"] == []
    assert ergebnis["raw_response"] == "Dazu kann ich nichts sagen."


@pytest.mark.asyncio
async def test_kaputtes_json_liefert_ebenfalls_den_rohtext():
    dienst, _ = _dienst('{"destinations": [{"name": "Lissabon"')
    ergebnis = await dienst.suggest_destinations(["Kultur"], 7)
    assert ergebnis["destinations"] == []
    assert "raw_response" in ergebnis


# ── Die Anfragen selbst ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_interessen_und_dauer_landen_in_der_anfrage():
    dienst, anbieter = _dienst(json.dumps(ZIELE))
    await dienst.suggest_destinations(["Kultur", "Essen"], 10, budget="mittel", season="Herbst")
    prompt = anbieter.letzter_prompt
    assert "Kultur, Essen" in prompt
    assert "10 Tage" in prompt
    assert "mittel" in prompt
    assert "Herbst" in prompt


@pytest.mark.asyncio
async def test_ohne_budget_steht_kein_leeres_budget_in_der_anfrage():
    dienst, anbieter = _dienst(json.dumps(ZIELE))
    await dienst.suggest_destinations(["Kultur"], 5)
    assert "Budget:" not in anbieter.letzter_prompt


@pytest.mark.asyncio
async def test_reiseplan_nennt_ziel_und_dauer():
    dienst, anbieter = _dienst(json.dumps({"itinerary": []}))
    await dienst.plan_trip("Lissabon", 5, ["Kultur"])
    assert "Lissabon" in anbieter.letzter_prompt
    assert "5" in anbieter.letzter_prompt


@pytest.mark.asyncio
async def test_beschreibung_kommt_als_text_zurueck():
    dienst, _ = _dienst("Lissabon liegt im Licht.")
    assert await dienst.describe_destination("Lissabon") == "Lissabon liegt im Licht."


@pytest.mark.asyncio
async def test_das_gespraech_bekommt_eine_systemanweisung():
    """Ohne sie antwortet das Modell mit Allgemeinplätzen — genau das, was
    die Anweisung im Code ausdrücklich verbietet."""
    dienst, anbieter = _dienst("Antwort")
    await dienst.chat("Wo esse ich in Lissabon?")
    assert anbieter.letztes_system is not None
    assert "KONKRET" in anbieter.letztes_system
    assert anbieter.letzter_prompt == "Wo esse ich in Lissabon?"


@pytest.mark.asyncio
async def test_geheimtipps_werden_gelesen():
    dienst, _ = _dienst(json.dumps(TIPPS))
    assert (await dienst.get_local_tips("Lissabon", "restaurants"))[0]["name"] == "Tasca do Chico"


@pytest.mark.asyncio
async def test_geheimtipps_mit_vorrede():
    dienst, _ = _dienst("Klar:\n" + json.dumps(TIPPS) + "\nViel Spaß!")
    assert len(await dienst.get_local_tips("Lissabon")) == 1


@pytest.mark.asyncio
async def test_geheimtipps_ohne_json_ergeben_eine_leere_liste():
    dienst, _ = _dienst("Kenne ich nicht.")
    assert await dienst.get_local_tips("Lissabon") == []


@pytest.mark.asyncio
async def test_kaputte_geheimtipps_ergeben_eine_leere_liste():
    dienst, _ = _dienst('[{"name": "Tasca"')
    assert await dienst.get_local_tips("Lissabon") == []


@pytest.mark.asyncio
async def test_die_kategorie_wird_ausgeschrieben():
    dienst, anbieter = _dienst(json.dumps(TIPPS))
    await dienst.get_local_tips("Lissabon", "nightlife")
    assert "Nachtleben" in anbieter.letzter_prompt


@pytest.mark.asyncio
async def test_unbekannte_kategorie_faellt_auf_alle_zurueck():
    dienst, anbieter = _dienst(json.dumps(TIPPS))
    await dienst.get_local_tips("Lissabon", "gibtesnicht")
    assert "alle" in anbieter.letzter_prompt


# ── Token-Budget: der Denk-Block isst den Text auf ───────────────────────────
#
# Am 2026-08-26 in der Produktion gemessen. Auf Claude begrenzt `max_tokens`
# DENKEN UND TEXT zusammen, und die aktuellen Modelle denken adaptiv, ohne
# dass man es einschaltet. Bei 2048 blieb für den Text nichts übrig:
#
#   {"fehler": "Claude lieferte keinen Textblock (Blockarten: ['thinking'])"}
#
# Dieselbe Ursache erzeugte in derselben Minute noch zwei ganz anders
# aussehende Fehler (JSONDecodeError, AttributeError) — deshalb prüfen die
# Tests unten nicht die Symptome, sondern das Budget und die Abbruchmeldung.


class _Block:
    def __init__(self, art, text=None):
        self.type = art
        if text is not None:
            self.text = text


class _Nutzung:
    def __init__(self, tokens):
        self.output_tokens = tokens


class _ClaudeAntwort:
    def __init__(self, bloecke, stop_reason="end_turn", tokens=100):
        self.content = bloecke
        self.stop_reason = stop_reason
        self.usage = _Nutzung(tokens)


class _MessagesDoppel:
    """Nimmt den Aufruf entgegen und merkt sich die Argumente."""

    def __init__(self, antwort):
        self.antwort = antwort
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.antwort


def _claude(antwort):
    anbieter = ClaudeProvider.__new__(ClaudeProvider)
    anbieter.model = "claude-sonnet-5"
    anbieter.model_id = "claude-sonnet-5"
    doppel = _MessagesDoppel(antwort)
    anbieter.client = type("Klient", (), {"messages": doppel})()
    return anbieter, doppel


@pytest.mark.asyncio
async def test_claude_bekommt_denk_reserve_obendrauf():
    """Der Aufrufer meint mit max_tokens den TEXT. Ohne Reserve geht das
    Budget ans Denken und der Textblock fehlt ganz."""
    from services.ai_service import CLAUDE_DENK_RESERVE

    anbieter, doppel = _claude(_ClaudeAntwort([_Block("text", '[{"name": "Zagreb"}]')]))
    await anbieter.chat("Empfiehl mir Orte", max_tokens=2048)
    assert doppel.kwargs["max_tokens"] == 2048 + CLAUDE_DENK_RESERVE


@pytest.mark.asyncio
async def test_die_denk_reserve_ist_groesser_als_null():
    """Sonst besteht der Test darüber auch bei CLAUDE_DENK_RESERVE = 0."""
    from services.ai_service import CLAUDE_DENK_RESERVE

    assert CLAUDE_DENK_RESERVE >= 4096


@pytest.mark.asyncio
async def test_abgeschnittene_claude_antwort_scheitert_LAUT():
    """Sonst wandert halber Text in den JSON-Parser, und dessen Meldung zeigt
    auf Anführungszeichen in Zeile 24 statt auf das Token-Limit."""
    anbieter, _ = _claude(_ClaudeAntwort([_Block("text", '[{"name": "Zag')], stop_reason="max_tokens", tokens=10240))
    with pytest.raises(RuntimeError) as fehler:
        await anbieter.chat("Empfiehl mir Orte", max_tokens=2048)
    meldung = str(fehler.value)
    assert "Token-Limit" in meldung
    assert "10240" in meldung  # die erzeugte Menge gehört in die Meldung


@pytest.mark.asyncio
async def test_eine_vollstaendige_antwort_geht_durch():
    """Gegenkontrolle: die Abbruchprüfung darf nicht alles sperren."""
    anbieter, _ = _claude(_ClaudeAntwort([_Block("thinking"), _Block("text", "fertig")]))
    assert await anbieter.chat("Frage", max_tokens=2048) == "fertig"


# ── Dieselbe Falle bei OpenAI und Groq ──────────────────────────────────────


class _Wahl:
    def __init__(self, finish_reason):
        self.finish_reason = finish_reason
        self.message = type("Nachricht", (), {"content": "halber Text"})()


class _ChatAntwort:
    def __init__(self, finish_reason):
        self.choices = [_Wahl(finish_reason)]


@pytest.mark.parametrize("anbietername", ["OpenAI", "Groq"])
def test_finish_reason_length_scheitert_LAUT(anbietername):
    from services.ai_service import _abbruch_pruefen

    with pytest.raises(RuntimeError) as fehler:
        _abbruch_pruefen(anbietername, _ChatAntwort("length"), 2048)
    assert anbietername in str(fehler.value)


def test_eine_normale_antwort_wird_nicht_gesperrt():
    """Gegenkontrolle — eine Prüfung, die immer anschlägt, prüft nichts."""
    from services.ai_service import _abbruch_pruefen

    _abbruch_pruefen("OpenAI", _ChatAntwort("stop"), 2048)
    _abbruch_pruefen("OpenAI", type("Leer", (), {"choices": []})(), 2048)


# Die Tests oben pruefen den HELFER. Dass ihn auch jemand AUFRUFT, ist eine
# andere Aussage — beim Gegentest am 2026-08-26 blieben sie gruen, nachdem der
# Aufruf in `GroqProvider.chat` geloescht war. Deshalb hier die Verdrahtung,
# ueber `chat()` und mit einem Doppel an der Stelle des echten Klienten.


class _CompletionsDoppel:
    def __init__(self, antwort):
        self.antwort = antwort

    def create(self, **kwargs):
        return self.antwort


def _mit_klient(klasse, antwort):
    anbieter = klasse.__new__(klasse)
    anbieter.model = "ein-modell"
    anbieter.model_id = "ein-modell"
    fertigstellungen = _CompletionsDoppel(antwort)
    anbieter.client = type("Klient", (), {"chat": type("C", (), {"completions": fertigstellungen})()})()
    return anbieter


@pytest.mark.asyncio
@pytest.mark.parametrize("klasse,name", [(OpenAIProvider, "OpenAI"), (GroqProvider, "Groq")])
async def test_die_abbruchpruefung_ist_auch_verdrahtet(klasse, name):
    anbieter = _mit_klient(klasse, _ChatAntwort("length"))
    with pytest.raises(RuntimeError) as fehler:
        await anbieter.chat("Frage", max_tokens=2048)
    assert name in str(fehler.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("klasse", [OpenAIProvider, GroqProvider])
async def test_eine_vollstaendige_antwort_kommt_durch(klasse):
    """Gegenkontrolle zur Verdrahtung."""
    anbieter = _mit_klient(klasse, _ChatAntwort("stop"))
    assert await anbieter.chat("Frage", max_tokens=2048) == "halber Text"
