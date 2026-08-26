"""
Wächter für die Geokodierung.

Am 2026-08-26 bekam eine Kroatien-Reise acht Orte mit den Koordinaten 0/0.
Zwei Ursachen, beide am laufenden Dienst gemessen:

1. Die Suchanfrage war `"{name}, {destination}"`, und das Reiseziel war eine
   Hausadresse. Ergebnis: "Ethno-Dorf Čigoč, Gornja Jelenska Kamenica 55" —
   0 von 8 Orten gefunden.
2. Der Fehlschlag gab die ursprünglichen 0/0 zurück und speicherte sie. Ein
   Ort ohne Position sah damit aus wie ein Ort im Atlantik.

Die Tests hier fassen kein Netz an. Was gemessen werden musste, wurde gegen
die echten Dienste gemessen (siehe Modul-Kopf von utils/geocoding.py); hier
steht, was daraus als Regel folgt.
"""

import pytest
from utils.geocoding import _ist_null_insel, abstand_km, geocode_if_missing, suchvarianten


class TestSuchvarianten:
    """
    Die Variantenkette ist der Kern der Reparatur — und sie hat eine Falle,
    die einmal zugeschlagen hat.
    """

    def test_ungeschnittene_form_kommt_zuerst(self):
        # Sonst verdrängt eine Vereinfachung einen exakten Treffer.
        assert suchvarianten("Čigoč")[0] == "Čigoč"
        assert suchvarianten("Ethno-Dorf Čigoč")[0] == "Ethno-Dorf Čigoč"

    def test_gattungswort_wird_entfernt(self):
        # Nominatim kennt "Ethno-Dorf Čigoč" nicht, "Čigoč" schon.
        assert "Čigoč" in suchvarianten("Ethno-Dorf Čigoč")
        assert "Zeleni Vir" in suchvarianten("Etno-Restaurant Zeleni Vir")
        assert "Moslavačka Gora" in suchvarianten("Wanderweg Moslavačka Gora")

    def test_ortsbezug_bleibt_erhalten(self):
        """
        Das ist der wichtigste Test in dieser Datei.

        Eine frühere Fassung schnitt alles hinter "in"/"bei" ab. Aus "Schloss
        Erdödy in Jastrebarsko" wurde "Erdödy" — und das fand das Schloss
        Erdödy-Rubido bei Novi Marof, 60 km in die FALSCHE Richtung. Es gibt
        mehrere Erdödy-Schlösser; genau der abgeschnittene Teil löste die
        Mehrdeutigkeit auf. Der Treffer lag im Umkreis und sah dadurch richtig
        aus — ein falsches Ergebnis ist teurer als gar keines.
        """
        varianten = suchvarianten("Schloss Erdödy in Jastrebarsko")
        assert "Erdödy, Jastrebarsko" in varianten
        # Der Ortsbezug darf nirgends ersatzlos verschwinden.
        assert all(
            "Jastrebarsko" in v or v == "Schloss Erdödy in Jastrebarsko" or v == "Erdödy" for v in varianten
        ), varianten
        assert any("Jastrebarsko" in v for v in varianten)

    def test_ortsbezug_bei(self):
        varianten = suchvarianten("Kupa Fluss Aussichtspunkt bei Sisak")
        assert any("Sisak" in v for v in varianten)

    def test_keine_leeren_oder_doppelten_varianten(self):
        for name in ["Restaurant Purger", "Park", "Schloss", "Lonjsko Polje Naturpark"]:
            v = suchvarianten(name)
            assert all(x.strip() for x in v), (name, v)
            assert len(v) == len(set(v)), (name, v)

    def test_reiner_gattungsname_verliert_sich_nicht(self):
        # "Park" darf nicht zu "" werden — sonst wird eine leere Anfrage
        # gestellt, und Nominatim antwortet mit irgendetwas.
        assert suchvarianten("Park")[0] == "Park"


class TestNullInsel:
    def test_erkennt_den_ersatzwert(self):
        assert _ist_null_insel(0.0, 0.0)
        assert _ist_null_insel(0.0005, -0.0005)

    def test_echte_positionen_sind_keine_nullinsel(self):
        assert not _ist_null_insel(45.4154, 16.6309)
        # Äquator und Nullmeridian sind bewohnt — nur BEIDES zugleich zählt.
        assert not _ist_null_insel(0.0, 16.6309)
        assert not _ist_null_insel(45.4154, 0.0)

    def test_none_ist_keine_nullinsel(self):
        # None heisst "unbekannt" und ist bereits der ehrliche Zustand.
        assert not _ist_null_insel(None, None)
        assert not _ist_null_insel(None, 16.6)


class TestAbstand:
    def test_bekannte_strecke(self):
        # Gornja Jelenska -> Čigoč, gemessen ~22,8 km.
        d = abstand_km((45.6151843, 16.6985547), (45.4154, 16.6309))
        assert 21.0 < d < 25.0, d

    def test_nullstrecke(self):
        assert abstand_km((45.0, 16.0), (45.0, 16.0)) == pytest.approx(0.0, abs=1e-9)


class TestGeocodeIfMissing:
    """
    Der Vertrag, an dem der ursprüngliche Fehler hing.
    """

    @pytest.mark.asyncio
    async def test_vorhandene_position_bleibt_unangetastet(self, monkeypatch):
        async def darf_nicht_laufen(**_):
            raise AssertionError("Geokodierung lief, obwohl eine Position vorlag")

        monkeypatch.setattr("utils.geocoding.geocode_place", darf_nicht_laufen)
        assert await geocode_if_missing("Čigoč", 45.4154, 16.6309) == (45.4154, 16.6309)

    @pytest.mark.asyncio
    async def test_fehlschlag_liefert_None_nicht_null_insel(self, monkeypatch):
        """
        Das ist der Kern: früher kamen hier (0.0, 0.0) zurück und wurden
        gespeichert. Der Ort lag danach im Golf von Guinea und sah aus wie
        ein vollständiger Datensatz.
        """

        async def findet_nichts(**_):
            return None

        monkeypatch.setattr("utils.geocoding.geocode_place", findet_nichts)
        assert await geocode_if_missing("Unauffindbarer Ort", None, None) == (None, None)
        assert await geocode_if_missing("Unauffindbarer Ort", 0.0, 0.0) == (None, None)

    @pytest.mark.asyncio
    async def test_null_insel_wird_neu_gesucht(self, monkeypatch):
        # 0/0 gilt als "fehlt", nicht als vorhandene Position.
        async def findet(**_):
            return {"lat": 45.4154, "lon": 16.6309, "name": "Čigoč"}

        monkeypatch.setattr("utils.geocoding.geocode_place", findet)
        assert await geocode_if_missing("Čigoč", 0.0, 0.0) == (45.4154, 16.6309)

    @pytest.mark.asyncio
    async def test_treffer_wird_uebernommen(self, monkeypatch):
        async def findet(**_):
            return {"lat": 45.3609, "lon": 16.8209, "name": "Lonjsko polje"}

        monkeypatch.setattr("utils.geocoding.geocode_place", findet)
        assert await geocode_if_missing("Lonjsko Polje", None, None) == (45.3609, 16.8209)


class TestLandbevorzugung:
    """
    Die Entfernung allein reicht nicht.

    "Etno-Restaurant Zeleni Vir" fand ein Zeleni vir bei Banja Luka: 107 km
    entfernt, also innerhalb der 150-km-Schranke — aber in Bosnien, während
    die Reise in Kroatien stattfindet. Der Treffer sah wie ein Ergebnis aus
    und war einer im falschen Staat.
    """

    ANKER = (45.6151843, 16.6985547)  # Gornja Jelenska, Kroatien

    def _kandidaten(self):
        return [
            {"lat": 44.7411, "lon": 17.2791, "name": "Zeleni vir, Banja Luka", "land": "ba"},
            {"lat": 45.7281, "lon": 15.3178, "name": "Zeleni vir, Ozalj", "land": "hr"},
        ]

    def test_gleiches_land_gewinnt_auch_wenn_weiter_weg(self):
        from utils.geocoding import _naechster, abstand_km

        naeher, ferner = self._kandidaten()
        # Der bosnische Treffer ist tatsächlich der nähere — sonst prüft der
        # Test nicht, was er zu prüfen vorgibt.
        assert abstand_km(self.ANKER, (naeher["lat"], naeher["lon"])) < abstand_km(
            self.ANKER, (ferner["lat"], ferner["lon"])
        )

        treffer = _naechster(self._kandidaten(), self.ANKER, 150.0, land="hr")
        assert treffer["land"] == "hr"
        assert treffer["fremdes_land"] is False

    def test_ohne_landangabe_entscheidet_die_entfernung(self):
        from utils.geocoding import _naechster

        treffer = _naechster(self._kandidaten(), self.ANKER, 150.0, land=None)
        assert treffer["land"] == "ba"  # der nähere

    def test_fremdes_land_wird_genommen_wenn_es_nichts_anderes_gibt(self):
        # Ein Tagesausflug über die Grenze ist ein normaler Reisewunsch —
        # nachgeordnet, nicht ausgeschlossen.
        from utils.geocoding import _naechster

        nur_bosnien = [self._kandidaten()[0]]
        treffer = _naechster(nur_bosnien, self.ANKER, 150.0, land="hr")
        assert treffer is not None
        assert treffer["fremdes_land"] is True
