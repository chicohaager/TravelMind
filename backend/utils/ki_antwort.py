"""Die eine Stelle, an der die Antwort eines Sprachmodells zu Daten wird.

Vorher lag dieselbe Aufgabe an vier Stellen: einmal als `_parse_ai_json` in
`routes/ai.py` und dreimal als handgeschriebene `find("{") … json.loads`-Kette
in `services/ai_service.py`. Die drei letzteren hatten dabei eine Eigenschaft,
die schlimmer ist als ein Absturz: sie gaben bei einer unlesbaren Antwort eine
LEERE Liste zurueck. Auf dem Bildschirm stand dann „keine Vorschlaege" — nicht
zu unterscheiden von „das Modell hat nichts gefunden", von „der Schluessel ist
abgelaufen" und von „die Antwort war abgeschnitten".

Hier wird stattdessen laut gescheitert. Die Einzelheiten (Vorgang, Laenge,
Anfang des Rohtexts) stehen in der Ausnahme und landen ueber `_ki_fehler` im
Server-Protokoll, wo sie hingehoeren — nicht in der HTTP-Antwort.
"""

import json
import re

# So viel Rohtext wandert in die Fehlermeldung. Genug, um zu sehen, WAS das
# Modell gesagt hat (Entschuldigung? Code-Zaun? mittendrin abgeschnitten?),
# und wenig genug, dass das Protokoll lesbar bleibt.
ROHTEXT_IM_FEHLER = 300


def parse_ai_json(response: str, erwartet: type = None, vorgang: str = "KI-Antwort"):
    """Parse a JSON object/array from an AI response.

    Models (Claude, GPT, …) frequently wrap JSON in ```json code fences or add
    a short preamble, so a bare json.loads() fails with "Expecting value: line 1
    column 1". Strip fences, then fall back to extracting the outermost {...} or
    [...]. Raises json.JSONDecodeError if nothing parseable is found.

    `erwartet` nennt die Form, die der Prompt angefordert hat (`list` oder
    `dict`). Sie ist keine Feinheit: der Notfall-Zweig probiert beide Klammer-
    arten, und bei einem ABGESCHNITTENEN Array gibt es kein `]` mehr — dann
    greift die `{…}`-Variante und liefert ein Objekt, das aussieht wie ein
    Ergebnis. Am 2026-08-26 in der Produktion gemessen: der Aufrufer iterierte
    darueber, bekam Schluessel statt Objekte und starb an
    `'str' object has no attribute 'get'` — eine Meldung, die nichts mehr mit
    der Ursache (Token-Limit) zu tun hat. Mit `erwartet=list` wird der falsche
    Zweig gar nicht erst probiert.

    `vorgang` benennt den Aufrufer, damit im Protokoll steht, WELCHE Anfrage
    unlesbar war.
    """
    text = (response or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    klammern = {list: (("[", "]"),), dict: (("{", "}"),)}.get(erwartet, (("[", "]"), ("{", "}")))

    try:
        geparst = json.loads(text)
    except json.JSONDecodeError:
        # Try array and object extraction independently so a stray bracket in a
        # preamble can't make us slice across mismatched delimiters.
        geparst = _keine_form = object()
        for open_ch, close_ch in klammern:
            start, end = text.find(open_ch), text.rfind(close_ch)
            if start != -1 and end > start:
                try:
                    geparst = json.loads(text[start : end + 1])
                    break
                except json.JSONDecodeError:
                    continue
        if geparst is _keine_form:
            raise ValueError(
                f"{vorgang}: kein lesbares JSON in der Antwort "
                f"({len(text)} Zeichen, Anfang: {text[:ROHTEXT_IM_FEHLER]!r})"
            ) from None

    if erwartet is not None and not isinstance(geparst, erwartet):
        raise ValueError(
            f"{vorgang}: falsche Form — erwartet {erwartet.__name__}, "
            f"bekommen {type(geparst).__name__} (Anfang: {text[:ROHTEXT_IM_FEHLER]!r})"
        )
    return geparst


def nur_objekte(elemente: list, feld: str) -> list:
    """Sicherstellen, dass eine Liste aus Objekten besteht, bevor `.get` darauf laeuft.

    Ohne diesen Schritt entscheidet die KI, ob der Endpunkt mit einem
    AttributeError abstuerzt — und die Meldung nennt dann den Zugriff, nicht
    die Antwort, die ihn verursacht hat.
    """
    falsch = [type(e).__name__ for e in elemente if not isinstance(e, dict)]
    if falsch:
        raise ValueError(
            f"KI-Antwort ({feld}): {len(falsch)} von {len(elemente)} Eintraegen sind keine Objekte ({falsch[:3]})"
        )
    return elemente
