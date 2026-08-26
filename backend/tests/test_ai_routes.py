"""
Wächter für die KI-Endpunkte (`routes/ai.py`, vorher 41 %).

Der wichtigste Teil ist der Weg VOR dem Modell: ohne konfigurierten Anbieter
muss der Endpunkt einen eigenen, erkennbaren Status liefern (428), damit die
Oberfläche zu den Einstellungen führen kann statt „keine Vorschläge"
anzuzeigen. Und der API-Schlüssel darf unter keinen Umständen in einer
Antwort auftauchen — auch nicht in einer Fehlermeldung.

`_parse_ai_json` wird direkt geprüft: es ist die Stelle, an der die Antworten
echter Sprachmodelle scheitern (Code-Zäune, Vorreden, ein einzelner
Klammerrest im Fließtext).

Kein Test ruft ein Modell auf.
"""

import json

import pytest
import pytest_asyncio
from httpx import AsyncClient
from routes.ai import _nur_objekte, _parse_ai_json

# ── Antwortauswertung ───────────────────────────────────────────────────────


def test_sauberes_objekt():
    assert _parse_ai_json('{"a": 1}') == {"a": 1}


def test_code_zaun_mit_sprachangabe():
    assert _parse_ai_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_code_zaun_ohne_sprachangabe():
    assert _parse_ai_json("```\n[1, 2]\n```") == [1, 2]


def test_vorrede_vor_dem_objekt():
    assert _parse_ai_json('Gerne! {"a": 1}') == {"a": 1}


def test_nachsatz_hinter_dem_array():
    assert _parse_ai_json("[1, 2]\nViel Spaß!") == [1, 2]


def test_eine_einzelne_klammer_in_der_vorrede_zerlegt_nichts():
    """Genau dafür trennt der Code Array- und Objektsuche: sonst würde vom
    ersten '[' bis zur letzten '}' geschnitten — quer über zwei verschiedene
    Klammerarten."""
    assert _parse_ai_json('Hinweis [wichtig]: hier das Ergebnis\n{"a": 1}') == {"a": 1}


def test_ohne_json_wird_LAUT_gescheitert():
    """Kein leerer Rückfall: der Aufrufer soll den Unterschied zwischen
    'nichts gefunden' und 'Antwort unlesbar' sehen können."""
    with pytest.raises(json.JSONDecodeError):
        _parse_ai_json("Dazu kann ich nichts sagen.")


def test_leere_antwort_scheitert_ebenfalls_laut():
    with pytest.raises(json.JSONDecodeError):
        _parse_ai_json("")


def test_None_scheitert_ebenfalls_laut():
    with pytest.raises(json.JSONDecodeError):
        _parse_ai_json(None)


# ── Ohne konfigurierte KI ───────────────────────────────────────────────────

KI_PFADE = [
    ("/api/ai/suggest", {"interests": ["Kultur"], "duration": 7}),
    ("/api/ai/plan", {"destination": "Lissabon", "duration": 5, "interests": ["Kultur"]}),
    ("/api/ai/describe", {"destination": "Lissabon"}),
    ("/api/ai/chat", {"message": "Wo esse ich?"}),
    ("/api/ai/local-tips", {"destination": "Lissabon"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("pfad,nutzlast", KI_PFADE)
async def test_ohne_konfiguration_kommt_428(client: AsyncClient, auth_headers, pfad, nutzlast):
    antwort = await client.post(pfad, headers=auth_headers, json=nutzlast)
    assert antwort.status_code == 428, f"{pfad}: {antwort.status_code} {antwort.text[:200]}"
    assert antwort.json()["detail"]["error"] == "AI_NOT_CONFIGURED"


@pytest.mark.asyncio
@pytest.mark.parametrize("pfad,nutzlast", KI_PFADE)
async def test_ohne_anmeldung_kommt_401(client: AsyncClient, pfad, nutzlast):
    assert (await client.post(pfad, json=nutzlast)).status_code == 401


@pytest.mark.asyncio
async def test_status_meldet_unkonfiguriert(client: AsyncClient, auth_headers):
    daten = (await client.get("/api/ai/status", headers=auth_headers)).json()
    assert daten["configured"] is False
    # `provider` steht hier schon auf "GROQ": das Modell hat einen
    # Vorgabewert. Entscheidend ist `configured`, daran haengt die
    # Oberflaeche — festgehalten, damit die Unterscheidung nicht verrutscht.
    assert daten["provider"] == "GROQ"


# ── Mit konfigurierter KI ───────────────────────────────────────────────────


@pytest_asyncio.fixture
async def ki_eingerichtet(client: AsyncClient, auth_headers):
    """Richtet einen Anbieter samt Schlüssel ein — über die echte API, damit
    der Schlüssel denselben Weg nimmt wie im Betrieb."""
    geheim = "gsk_dieser_schluessel_darf_nirgends_auftauchen"
    antwort = await client.put(
        "/api/user/settings/ai", headers=auth_headers, json={"ai_provider": "groq", "api_key": geheim}
    )
    assert antwort.status_code == 200, antwort.text
    return geheim


@pytest.mark.asyncio
async def test_status_meldet_konfiguriert(client: AsyncClient, auth_headers, ki_eingerichtet):
    daten = (await client.get("/api/ai/status", headers=auth_headers)).json()
    assert daten["configured"] is True
    assert daten["provider"] == "GROQ"
    # Und der Schlüssel selbst darf nicht dabei sein.
    assert ki_eingerichtet not in json.dumps(daten)


@pytest.mark.asyncio
async def test_vorschlaege_werden_durchgereicht(client: AsyncClient, auth_headers, ki_eingerichtet, monkeypatch):
    import routes.ai as ai_modul

    class _Dienst:
        async def suggest_destinations(self, **kwargs):
            assert kwargs["interests"] == ["Kultur"]
            assert kwargs["duration"] == 7
            return {"destinations": [{"name": "Lissabon"}]}

    monkeypatch.setattr(ai_modul, "get_user_ai_service", lambda user: _Dienst())
    antwort = await client.post("/api/ai/suggest", headers=auth_headers, json={"interests": ["Kultur"], "duration": 7})
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["destinations"][0]["name"] == "Lissabon"


@pytest.mark.asyncio
async def test_ein_fehler_des_modells_verraet_den_schluessel_NICHT(
    client: AsyncClient, auth_headers, ki_eingerichtet, monkeypatch
):
    """Die Fehlermeldung des Endpunkts hängt `str(e)` an. Wirft eine
    Anbieter-Bibliothek den Schlüssel in ihre Meldung, stünde er in der
    Antwort — dieser Test hält fest, dass das auffiele."""
    import routes.ai as ai_modul

    class _Dienst:
        async def describe_destination(self, destination):
            raise RuntimeError(f"invalid api key: {ki_eingerichtet}")

    monkeypatch.setattr(ai_modul, "get_user_ai_service", lambda user: _Dienst())
    antwort = await client.post("/api/ai/describe", headers=auth_headers, json={"destination": "Lissabon"})
    assert antwort.status_code == 500
    assert ki_eingerichtet not in antwort.text, "Der API-Schlüssel steht in der Fehlermeldung"


@pytest.mark.asyncio
async def test_unmoegliche_dauer_wird_abgewiesen(client: AsyncClient, auth_headers):
    for dauer in (0, 61):
        antwort = await client.post(
            "/api/ai/suggest", headers=auth_headers, json={"interests": ["Kultur"], "duration": dauer}
        )
        assert antwort.status_code == 422, dauer


# ── Formprüfung: abgeschnittene Antworten dürfen nicht plausibel aussehen ────
#
# Am 2026-08-26 in der Produktion gemessen (Backend-Protokoll, Benutzer 2):
# `/personalized-recommendations` starb an
# `AttributeError: 'str' object has no attribute 'get'`. Ursache war kein
# Zugriffsfehler, sondern ein abgeschnittenes Array: ohne schliessende `]`
# griff der Notfall-Zweig auf `{…}` zu, lieferte ein OBJEKT, und das Iterieren
# darüber gab Schlüssel (str) statt Empfehlungen. Ein Formfehler, der sich als
# Programmierfehler verkleidet.


def test_abgeschnittenes_array_wird_nicht_als_objekt_ausgegeben():
    """Genau der Fall aus der Produktion — vorher kam hier ein dict heraus."""
    abgeschnitten = '[\n  {"name": "Plitvice", "category": "park"},\n  {"name": "Zagreb", "cat'
    with pytest.raises(ValueError):
        _parse_ai_json(abgeschnitten, erwartet=list)


def test_ohne_erwartung_bleibt_der_alte_notfall_zweig():
    """Positivkontrolle zur Zeile darüber: die Ablehnung kommt von `erwartet`,
    nicht davon, dass der Text unparsbar wäre."""
    abgeschnitten = '[\n  {"name": "Plitvice", "category": "park"},\n  {"name": "Zagreb", "cat'
    assert isinstance(_parse_ai_json(abgeschnitten), dict)


def test_objekt_wo_eine_liste_erwartet_wird_wird_abgelehnt():
    with pytest.raises(ValueError):
        _parse_ai_json('{"recommendations": []}', erwartet=list)


def test_liste_wo_ein_objekt_erwartet_wird_wird_abgelehnt():
    with pytest.raises(ValueError):
        _parse_ai_json("[1, 2]", erwartet=dict)


def test_die_erwartete_form_geht_weiterhin_durch():
    assert _parse_ai_json('```json\n[{"name": "Zagreb"}]\n```', erwartet=list) == [{"name": "Zagreb"}]
    assert _parse_ai_json('{"a": 1}', erwartet=dict) == {"a": 1}


def test_eintraege_die_keine_objekte_sind_werden_abgelehnt():
    """`.get` auf einer Zeichenkette ist ein Absturz mit irreführender Meldung."""
    with pytest.raises(ValueError) as fehler:
        _nur_objekte(["Plitvice", {"name": "Zagreb"}], "recommendations")
    assert "recommendations" in str(fehler.value)


def test_eine_liste_aus_objekten_geht_unveraendert_durch():
    eintraege = [{"name": "Zagreb"}]
    assert _nur_objekte(eintraege, "recommendations") is eintraege
