"""
Wächter gegen SDK-Signaturen, die sich unter dem Code wegbewegen.

Am 2026-08-25 in der laufenden Produktion gefunden: `ClaudeProvider` übergab
`temperature` an `Messages.create()`. Der installierte anthropic-SDK 1.0.0
nimmt das nicht mehr an und wirft

    TypeError: Messages.create() got an unexpected keyword argument 'temperature'

Damit scheiterte **jede** Claude-Anfrage. Die Zeile stammt laut `git log -S`
aus dem Initial-Commit vom 2025-11-01 — der SDK ist weitergezogen, der Code
nicht. Aufgefallen ist es erst, als der Fehlerpfad anfing zu protokollieren;
davor bekam der Nutzer „AI service error" und niemand sah, WAS fehlschlug.

Deshalb prüft diese Suite die Argumente gegen die **installierte** Signatur,
nicht gegen eine Liste im Kopf. Ein Bibliothekssprung fällt dann hier auf und
nicht beim Nutzer auf Reisen.
"""

import inspect

import pytest


def _erlaubte_argumente(funktion):
    """Die Namen, die eine Funktion tatsächlich annimmt.

    `**kwargs` in der Signatur bedeutet: alles ist erlaubt — dann kann diese
    Prüfung nichts aussagen und sagt das auch (None).
    """
    sig = inspect.signature(funktion)
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return None
    return set(sig.parameters)


def test_der_pruefer_selbst_funktioniert():
    """Positivkontrolle: ohne sie wäre alles unten auch dann grün, wenn
    `_erlaubte_argumente` immer None zurückgäbe."""

    def beispiel(a, b=1):
        pass

    assert _erlaubte_argumente(beispiel) == {"a", "b"}

    def offen(**kwargs):
        pass

    assert _erlaubte_argumente(offen) is None


def test_claude_uebergibt_nur_was_der_sdk_annimmt():
    from anthropic import Anthropic

    erlaubt = _erlaubte_argumente(Anthropic(api_key="x" * 20).messages.create)
    if erlaubt is None:
        pytest.skip("anthropic-SDK nimmt **kwargs — nicht prüfbar")

    # Genau die Schlüssel, die ClaudeProvider.chat() aufbaut.
    uebergeben = {"model", "max_tokens", "messages", "system"}
    fehlend = uebergeben - erlaubt
    assert not fehlend, f"anthropic nimmt diese Argumente nicht (mehr) an: {sorted(fehlend)}"


def test_claude_uebergibt_KEIN_temperature():
    """Die zweite, unabhängige Formulierung: nicht „passt es", sondern „ist
    der bekannte Übeltäter weg". Fällt auch dann auf, wenn jemand den Test
    darüber lockert."""
    from pathlib import Path

    quelle = Path(__file__).parent.parent / "services" / "ai_service.py"
    text = quelle.read_text(encoding="utf-8")
    claude_block = text.split("class ClaudeProvider")[1].split("class OpenAIProvider")[0]
    # Kommentare zählen nicht — der Grund darf die Zeichenkette nennen.
    ohne_kommentare = "\n".join(z for z in claude_block.splitlines() if not z.strip().startswith("#"))
    assert '"temperature"' not in ohne_kommentare, "temperature wird wieder an Claude übergeben"


@pytest.mark.parametrize(
    "modul,pfad,uebergeben",
    [
        ("openai", "chat.completions.create", {"model", "messages", "max_completion_tokens", "temperature"}),
        ("groq", "chat.completions.create", {"model", "messages", "max_tokens", "temperature"}),
    ],
)
def test_die_uebrigen_anbieter_passen_zu_ihrem_sdk(modul, pfad, uebergeben):
    import importlib

    m = importlib.import_module(modul)
    klient = m.OpenAI(api_key="x" * 20) if modul == "openai" else m.Groq(api_key="x" * 20)
    ziel = klient
    for teil in pfad.split("."):
        ziel = getattr(ziel, teil)

    erlaubt = _erlaubte_argumente(ziel)
    if erlaubt is None:
        pytest.skip(f"{modul} nimmt **kwargs — nicht prüfbar")
    fehlend = uebergeben - erlaubt
    assert not fehlend, f"{modul} nimmt diese Argumente nicht (mehr) an: {sorted(fehlend)}"


def test_jeder_anbieter_hat_die_gemeinsame_schnittstelle():
    """Alle vier müssen `chat(prompt, system_prompt, max_tokens, temperature)`
    anbieten — der UnifiedAIService ruft sie einheitlich auf."""
    from services.ai_service import ClaudeProvider, GeminiProvider, GroqProvider, OpenAIProvider

    for klasse in (ClaudeProvider, OpenAIProvider, GeminiProvider, GroqProvider):
        sig = inspect.signature(klasse.chat)
        assert {"prompt", "system_prompt", "max_tokens", "temperature"} <= set(sig.parameters), klasse.__name__
