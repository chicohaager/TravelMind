"""
Tests der Passwortregeln.

Alle Fälle kommen ohne Netz aus: die Abfrage an Have I Been Pwned wird
eingespeist. Das ist kein Selbstzweck — ein Test, der vom Netz abhängt, wird
sporadisch rot und irgendwann übersprungen.

Die drei Betriebsarten des Leak-Abgleichs werden EINZELN geprüft, samt der
Frage, was passiert, wenn die Gegenstelle nicht erreichbar ist. Genau dort
sitzt die gefährliche Stelle: ein Rückfall, der stillschweigend durchlässt,
sieht aus wie eine bestandene Prüfung.
"""

import hashlib

import pytest
from utils import password_policy as pp


def _antwort_mit(passwort: str, anzahl: int) -> str:
    """Eine HIBP-Antwort bauen, die genau dieses Passwort enthält."""
    voll = hashlib.sha1(passwort.encode()).hexdigest().upper()  # nosec B324
    suffix = voll[5:]
    # Die echte Antwort enthält immer viele Fremdzeilen — die auch.
    return f"0000000000000000000000000000000000A:3\r\n{suffix}:{anzahl}\r\nFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFB:7"


def _antwort_ohne(passwort: str) -> str:
    """Eine Antwort, in der dieses Passwort NICHT vorkommt."""
    voll = hashlib.sha1(passwort.encode()).hexdigest().upper()  # nosec B324
    fremd = ("A" * 35) if voll[5:] != "A" * 35 else ("B" * 35)
    return f"{fremd}:12"


async def _abfrage_erfolg(text: str):
    async def _abfrage(_praefix: str) -> str:
        return text

    return _abfrage


class TestLaenge:
    @pytest.mark.asyncio
    async def test_zu_kurz_wird_abgelehnt(self):
        ergebnis = await pp.passwort_pruefen("kurz", leak_abgleich="off")
        assert ergebnis.gueltig is False
        assert str(pp.MINDESTLAENGE) in ergebnis.grund

    @pytest.mark.asyncio
    async def test_genau_die_mindestlaenge_wird_angenommen(self):
        """Grenzfall — die Prüfung darf nicht einen zu viel verlangen."""
        ergebnis = await pp.passwort_pruefen("x" * pp.MINDESTLAENGE, leak_abgleich="off")
        assert ergebnis.gueltig is True

    @pytest.mark.asyncio
    async def test_absurd_lang_wird_abgelehnt(self):
        ergebnis = await pp.passwort_pruefen("x" * (pp.HOECHSTLAENGE + 1), leak_abgleich="off")
        assert ergebnis.gueltig is False

    @pytest.mark.asyncio
    async def test_keine_komplexitaetsregel(self):
        """
        Ausdrücklich: ein langes Passwort aus lauter Kleinbuchstaben ist gültig.
        NIST SP 800-63B rät von Komplexitätsregeln ab — sie erzeugen Muster
        wie "Passwort1!". Dieser Test hält die Entscheidung fest.
        """
        ergebnis = await pp.passwort_pruefen("pferdebatteriehefter", leak_abgleich="off")
        assert ergebnis.gueltig is True


class TestLeakAbgleich:
    @pytest.mark.asyncio
    async def test_geleaktes_passwort_wird_abgelehnt(self):
        passwort = "geleaktespasswort"
        ergebnis = await pp.passwort_pruefen(
            passwort,
            abfrage=await _abfrage_erfolg(_antwort_mit(passwort, 24230577)),
            leak_abgleich="best-effort",
        )
        assert ergebnis.gueltig is False
        assert ergebnis.leak_treffer == 24230577
        assert "Datenlecks" in ergebnis.grund

    @pytest.mark.asyncio
    async def test_unbekanntes_passwort_wird_angenommen(self):
        passwort = "diesespasswortkenntniemand"
        ergebnis = await pp.passwort_pruefen(
            passwort,
            abfrage=await _abfrage_erfolg(_antwort_ohne(passwort)),
            leak_abgleich="best-effort",
        )
        assert ergebnis.gueltig is True
        assert ergebnis.leak_treffer == 0

    @pytest.mark.asyncio
    async def test_nur_das_praefix_verlaesst_den_server(self):
        """
        k-Anonymität: gesendet werden fünf Zeichen des SHA-1-Hashes. Weder das
        Passwort noch der vollständige Hash dürfen die Abfrage erreichen.
        """
        passwort = "einbestimmtespasswort"
        gesehen = {}

        async def _abfrage(praefix: str) -> str:
            gesehen["praefix"] = praefix
            return _antwort_ohne(passwort)

        await pp.leak_treffer_zaehlen(passwort, abfrage=_abfrage)

        voll = hashlib.sha1(passwort.encode()).hexdigest().upper()  # nosec B324
        assert gesehen["praefix"] == voll[:5]
        assert len(gesehen["praefix"]) == 5
        assert passwort not in gesehen["praefix"]
        assert voll not in gesehen["praefix"]


class TestGegenstelleNichtErreichbar:
    """
    Die gefährliche Stelle: Was passiert, wenn HIBP nicht antwortet?
    Ein stiller Durchlass sähe aus wie eine bestandene Prüfung.
    """

    @staticmethod
    async def _abfrage_faellt_aus(_praefix: str) -> str:
        raise ConnectionError("kein Netz")

    @pytest.mark.asyncio
    async def test_zaehlung_liefert_none_nicht_null(self):
        """
        None heisst "nicht feststellbar", 0 heisst "nachweislich nicht betroffen".
        Diese beiden zu verwechseln waere genau der Fehler, den ein Fallback
        unsichtbar macht.
        """
        treffer = await pp.leak_treffer_zaehlen("egal", abfrage=self._abfrage_faellt_aus)
        assert treffer is None
        assert treffer != 0

    @pytest.mark.asyncio
    async def test_best_effort_laesst_durch(self):
        ergebnis = await pp.passwort_pruefen(
            "einlangesgutespasswort",
            abfrage=self._abfrage_faellt_aus,
            leak_abgleich="best-effort",
        )
        assert ergebnis.gueltig is True
        assert ergebnis.leak_treffer is None  # ausdrücklich: nicht geprüft

    @pytest.mark.asyncio
    async def test_required_lehnt_ab(self):
        ergebnis = await pp.passwort_pruefen(
            "einlangesgutespasswort",
            abfrage=self._abfrage_faellt_aus,
            leak_abgleich="required",
        )
        assert ergebnis.gueltig is False
        assert "nicht" in ergebnis.grund.lower()

    @pytest.mark.asyncio
    async def test_off_fragt_gar_nicht_erst(self):
        gerufen = {"n": 0}

        async def _abfrage(_praefix: str) -> str:
            gerufen["n"] += 1
            return ""

        ergebnis = await pp.passwort_pruefen("einlangesgutespasswort", abfrage=_abfrage, leak_abgleich="off")
        assert ergebnis.gueltig is True
        assert gerufen["n"] == 0, "bei 'off' darf keine Abfrage stattfinden"


class TestEndpunkteWendenDieRegelAn:
    """
    Die Regel greift an DREI Stellen: Registrierung, Passwortwechsel und
    Zuruecksetzen. Weil der Leak-Abgleich in der Suite abgeschaltet ist
    (siehe conftest), wird hier die Pruefung selbst ersetzt — sonst wuerde
    nichts belegen, dass die Endpunkte sie ueberhaupt aufrufen.

    Genau diese Luecke reisst ein abgeschalteter Schalter: die Regel ist da,
    der Endpunkt ruft sie vielleicht nie.
    """

    @pytest.mark.asyncio
    async def test_registrierung_lehnt_ein_geleaktes_passwort_ab(self, client, monkeypatch):
        from routes import auth as auth_route

        async def _immer_abgelehnt(_passwort, **_kwargs):
            return pp.Pruefergebnis(False, "Dieses Passwort taucht in bekannten Datenlecks auf.")

        monkeypatch.setattr(auth_route, "passwort_pruefen", _immer_abgelehnt)

        antwort = await client.post(
            "/api/auth/register",
            json={
                "username": "leakuser",
                "email": "leak@example.com",
                "password": "einlangesgutespasswort",  # pragma: allowlist secret
            },
        )
        assert antwort.status_code == 400
        assert "Datenlecks" in antwort.json()["detail"]

    @pytest.mark.asyncio
    async def test_registrierung_geht_durch_wenn_die_regel_zustimmt(self, client, monkeypatch):
        """Gegenkontrolle — ohne sie wuerde auch ein generell kaputter Endpunkt gruen aussehen."""
        from routes import auth as auth_route

        async def _immer_angenommen(_passwort, **_kwargs):
            return pp.Pruefergebnis(True, leak_treffer=0)

        monkeypatch.setattr(auth_route, "passwort_pruefen", _immer_angenommen)

        antwort = await client.post(
            "/api/auth/register",
            json={
                "username": "gutuser",
                "email": "gut@example.com",
                "password": "einlangesgutespasswort",  # pragma: allowlist secret
            },
        )
        assert antwort.status_code == 201

    def test_alle_drei_wege_rufen_die_pruefung_auf(self):
        """
        Registrierung, Wechsel und Zuruecksetzen — wird an einem der drei
        Wege vergessen, ist er die offene Tuer.
        """
        from pathlib import Path

        wurzel = Path(__file__).resolve().parent.parent
        for datei in ["routes/auth.py", "routes/users.py", "routes/password_reset.py"]:
            text = (wurzel / datei).read_text(encoding="utf-8")
            assert "passwort_pruefen(" in text, f"{datei} setzt ein Passwort ohne Pruefung"
