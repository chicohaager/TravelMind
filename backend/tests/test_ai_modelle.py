"""
Wächter für die Modell-IDs.

Eine Modell-ID ist ein GEMESSENER WERT, kein Vertrag: der Hersteller nimmt sie
aus dem Angebot, wann er will. Am 2026-08-25 gegen die Herstellerdokumentation
geprüft — alle vier im Code waren veraltet, und die von Groq (dem kostenlosen
STANDARDANBIETER) stand überhaupt nicht mehr in der Liste. Jede KI-Anfrage
eines Nutzers ohne eigene Konfiguration wäre fehlgeschlagen.

Was dieser Wächter kann und was nicht, ausdrücklich:

* Er hält fest, dass die IDs **aus der Umgebung** kommen — damit die nächste
  Abkündigung ohne neues Image zu reparieren ist.
* Er hält die heute geprüften Standardwerte fest, damit ein Rückfall auf eine
  alte ID auffällt.
* Er kann NICHT prüfen, ob eine ID beim Hersteller noch existiert. Das geht
  nur mit einem echten Schlüssel gegen den echten Dienst — und ein Test, der
  vom Netz abhängt, wird sporadisch rot und irgendwann übersprungen.
"""

import pytest
import services.ai_service as modul
from services.ai_service import modell_id
from services.guide_parser import GuideParserService  # noqa: F401  (Import belegt, dass die Datei laedt)

# Kein importlib.reload hier: es tauscht die Klassenobjekte aus und liess am
# 2026-08-25 fuenf Tests in test_ai_service.py fallen (isinstance gegen die
# ALTEN Klassen). Die IDs werden zur Laufzeit aufgeloest — ein Neuladen ist
# dafuer nicht noetig.


ABGEKUENDIGT = {
    "claude-sonnet-4-6",
    "gpt-5.4",
    "gemini-3.5-flash",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
}


def test_die_heute_geprueften_standardwerte():
    assert modul.STANDARD_MODELLE == {
        "CLAUDE_MODEL": "claude-sonnet-5",
        "OPENAI_MODEL": "gpt-5.6-terra",
        "GEMINI_MODEL": "gemini-3.7-flash",
        "GROQ_MODEL": "llama-3.3-70b-versatile",
    }


def test_keine_abgekuendigte_id_mehr_im_code():
    """Zweite, unabhängige Formulierung derselben Sache: nicht 'ist der neue
    Wert da', sondern 'ist der alte weg'. Ein Rückfall auf eine ID aus der
    Liste oben fällt damit auf, auch wenn jemand den Test darüber anpasst."""
    gesetzt = set(modul.STANDARD_MODELLE.values())
    assert not (gesetzt & ABGEKUENDIGT), gesetzt & ABGEKUENDIGT


@pytest.mark.parametrize(
    "variable,anbieter",
    [
        ("CLAUDE_MODEL", "claude"),
        ("OPENAI_MODEL", "openai"),
        ("GEMINI_MODEL", "gemini"),
        ("GROQ_MODEL", "groq"),
    ],
)
def test_die_umgebung_schlaegt_den_standardwert(monkeypatch, variable, anbieter):
    """Der eigentliche Zweck: die nächste Abkündigung soll ohne neues Image zu
    reparieren sein."""
    monkeypatch.setenv(variable, "ein-neues-modell-von-morgen")
    assert modell_id(variable) == "ein-neues-modell-von-morgen"
    assert modul.create_ai_service(anbieter, "x" * 20).provider.model_id == "ein-neues-modell-von-morgen"


@pytest.mark.parametrize("variable", sorted(["CLAUDE_MODEL", "OPENAI_MODEL", "GEMINI_MODEL", "GROQ_MODEL"]))
def test_ohne_umgebung_gilt_der_standardwert(monkeypatch, variable):
    """Gegenkontrolle: sonst wäre der Test darüber auch erfüllt, wenn die
    Umgebung IMMER gewönne — und eine leere Variable ergäbe eine leere ID."""
    monkeypatch.delenv(variable, raising=False)
    assert modell_id(variable) == modul.STANDARD_MODELLE[variable]
    monkeypatch.setenv(variable, "")
    assert modell_id(variable) == modul.STANDARD_MODELLE[variable], "leere Variable darf nicht gewinnen"


def test_der_reisefuehrer_parser_benutzt_dieselbe_quelle(monkeypatch):
    """Er rief `os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")` mit EIGENEM
    Standardwert auf — zwei Stellen, die auseinanderlaufen können. Jetzt
    fragen beide dieselbe Funktion."""
    import services.guide_parser as gp

    quelltext = open(gp.__file__, encoding="utf-8").read()
    assert 'modell_id("CLAUDE_MODEL")' in quelltext
    assert "claude-sonnet-4-6" not in quelltext


def test_jeder_anbieter_bekommt_ohne_angabe_seinen_standardwert():
    erwartet = {
        "claude": modell_id("CLAUDE_MODEL"),
        "openai": modell_id("OPENAI_MODEL"),
        "gemini": modell_id("GEMINI_MODEL"),
        "groq": modell_id("GROQ_MODEL"),
    }
    for name, id_ in erwartet.items():
        assert modul.create_ai_service(name, "x" * 20).provider.model_id == id_, name


def test_eine_ausdrueckliche_angabe_schlaegt_alles():
    assert modul.ClaudeProvider("x" * 20, model="claude-haiku-4-5").model_id == "claude-haiku-4-5"
