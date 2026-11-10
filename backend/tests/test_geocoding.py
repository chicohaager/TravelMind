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
        position = await geocode_if_missing("Čigoč", 45.4154, 16.6309)
        assert (position.lat, position.lon) == (45.4154, 16.6309)
        # Über mitgebrachte Koordinaten ist NICHTS bekannt. `None` heißt hier
        # „ungeprüft"; ein `False` wäre eine Zusicherung ohne Prüfung.
        assert position.nur_ort is None

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
        for lat, lon in ((None, None), (0.0, 0.0)):
            position = await geocode_if_missing("Unauffindbarer Ort", lat, lon)
            assert (position.lat, position.lon) == (None, None)

    @pytest.mark.asyncio
    async def test_null_insel_wird_neu_gesucht(self, monkeypatch):
        # 0/0 gilt als "fehlt", nicht als vorhandene Position.
        async def findet(**_):
            return {"lat": 45.4154, "lon": 16.6309, "name": "Čigoč"}

        monkeypatch.setattr("utils.geocoding.geocode_place", findet)
        position = await geocode_if_missing("Čigoč", 0.0, 0.0)
        assert (position.lat, position.lon) == (45.4154, 16.6309)

    @pytest.mark.asyncio
    async def test_treffer_wird_uebernommen(self, monkeypatch):
        async def findet(**_):
            return {"lat": 45.3609, "lon": 16.8209, "name": "Lonjsko polje"}

        monkeypatch.setattr("utils.geocoding.geocode_place", findet)
        position = await geocode_if_missing("Lonjsko Polje", None, None)
        assert (position.lat, position.lon) == (45.3609, 16.8209)

    @pytest.mark.asyncio
    async def test_die_kennzeichnung_wird_durchgereicht(self, monkeypatch):
        """Ohne diesen Weg bliebe `nur_ort` im Geocoder stecken und käme nie
        in der Datenbank an — die Karte könnte es dann nicht zeigen."""

        async def findet(**_):
            return {
                "lat": 45.4952,
                "lon": 16.7293,
                "name": "Repušnica",
                "typ": "village",
                "nur_ort": True,
                "ortsangabe_widerlegt": False,
                "abweichung_km": None,
            }

        monkeypatch.setattr("utils.geocoding.geocode_place", findet)
        position = await geocode_if_missing("Aussichtspunkt Repušnica", None, None)
        assert position.nur_ort is True

    @pytest.mark.asyncio
    async def test_eine_widerlegte_ortsangabe_wird_durchgereicht(self, monkeypatch):
        async def findet(**_):
            return {
                "lat": 45.9819,
                "lon": 15.9566,
                "name": "Terme Jezerčica, Donja Stubica",
                "typ": "amenity",
                "nur_ort": False,
                "ortsangabe_widerlegt": True,
                "abweichung_km": 69.2,
            }

        monkeypatch.setattr("utils.geocoding.geocode_place", findet)
        position = await geocode_if_missing("Terme Jezerčica in Popovača", None, None)
        assert position.ortsangabe_widerlegt is True
        assert position.abweichung_km == 69.2


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


class TestFelderVertrag:
    """
    Die Testwelt darf keine Eigenschaft haben, die der echte Code nicht
    erzeugt.

    TestLandbevorzugung oben arbeitet mit konstruierten Kandidaten, die ein
    Feld `land` tragen. Am 2026-08-26 lieferte `_nominatim` dieses Feld
    NICHT — eine Ersetzung war still gescheitert, weil `black` die Zeile
    zuvor umformatiert hatte. Ergebnis: 18 Tests grün, während die
    Landbevorzugung in der Produktion nie greifen konnte. Der Ort blieb in
    Bosnien.

    Dieser Test prüft nicht das Verhalten, sondern den VERTRAG zwischen
    Abruf und Auswahl. Er braucht kein Netz.
    """

    def test_naechster_verlangt_genau_die_felder_die_der_abruf_liefert(self):
        import inspect

        from utils import geocoding

        # Welche Felder baut der Abruf auf? Aus der Quelle lesen, nicht raten.
        quelle = inspect.getsource(geocoding._nominatim)
        for feld in ('"lat"', '"lon"', '"name"', '"land"'):
            assert feld in quelle, f"_nominatim liefert {feld} nicht mehr"

        quelle_photon = inspect.getsource(geocoding._photon)
        for feld in ('"lat"', '"lon"', '"name"', '"land"'):
            assert feld in quelle_photon, f"_photon liefert {feld} nicht mehr"

    def test_auswahl_arbeitet_auf_diesen_feldern(self):
        from utils.geocoding import _naechster

        # Genau die Form, die _nominatim/_photon zurückgeben.
        kandidat = {"lat": 45.4, "lon": 16.6, "name": "Test", "land": "hr"}
        treffer = _naechster([kandidat], (45.6, 16.7), 150.0, land="hr")
        assert treffer is not None
        assert treffer["fremdes_land"] is False
        assert treffer["abstand_km"] is not None


class TestOrtsgenauStattObjektgenau:
    """
    Der Fall aus der Produktion, 2026-08-26.

    Auf der Karte stand ein Marker „Terme Jezerčica in Popovača" mitten in
    Popovača. Gemessen:

      * Nominatim findet unter 'Terme Jezerčica in Popovača' und
        'Terme Jezerčica, Popovača' NICHTS — der Ort existiert dort nicht.
      * Die letzte Variante der Kette war der blosse Ortsname 'Popovača'.
        Deren Koordinaten landeten als Position des Thermalbads in der
        Datenbank, 0,00 km vom Stadtmittelpunkt.
      * Das echte Terme Jezerčica liegt in Donja Stubica, **69,2 km** entfernt.

    Zwei Lücken haben das ermöglicht, und beide werden hier festgehalten:
    die Kette fragte nie nach dem KERN allein, und `_nominatim` warf die ART
    des Treffers weg — niemand konnte merken, dass eine Gemeinde gefunden
    wurde statt eines Thermalbads.

    An denselben 16 Orten gemessen: 9 Positionen stammten aus einem
    Siedlungstreffer. Kein Netz nötig, alle Daten sind Fixtures aus der
    echten Messung.
    """

    def test_der_kern_allein_ist_eine_eigene_variante(self):
        varianten = suchvarianten("Terme Jezerčica in Popovača")
        assert "Terme Jezerčica" in varianten, varianten

    def test_der_kern_kommt_VOR_dem_blossen_ortsnamen(self):
        """Die Reihenfolge ist der Punkt: die erste Variante mit Treffer
        gewinnt. Stünde 'Popovača' davor, änderte der Kern gar nichts."""
        varianten = suchvarianten("Terme Jezerčica in Popovača")
        assert varianten.index("Terme Jezerčica") < varianten.index("Popovača"), varianten

    def test_der_ortsname_bleibt_als_letzte_zuflucht(self):
        """Gegenkontrolle: der Kern darf den Ortsnamen nicht verdrängen.
        'Erdödy' allein findet ein Erdody in der SLOWAKEI, 346,8 km weit —
        das fängt die Entfernungsschranke ab, und dann muss der Ortsname noch
        da sein."""
        varianten = suchvarianten("Schloss Erdödy in Jastrebarsko")
        assert varianten[-1] == "Jastrebarsko", varianten

    def test_ein_gemeindetreffer_ueber_eine_abkuerzung_wird_markiert(self):
        from utils.geocoding import _ist_nur_ort

        treffer = {"lat": 45.571, "lon": 16.627, "name": "Grad Popovača", "land": "hr", "typ": "town"}
        assert _ist_nur_ort(treffer, "Terme Jezerčica in Popovača", "Popovača") is True

    def test_wer_nach_dem_ort_sucht_bekommt_keine_warnung(self):
        """Gegenkontrolle 1: eine Markierung, die immer anschlägt, sagt
        nichts. Wer 'Popovača' sucht und Popovača bekommt, hat gefunden,
        was er wollte."""
        from utils.geocoding import _ist_nur_ort

        treffer = {"lat": 45.571, "lon": 16.627, "name": "Grad Popovača", "land": "hr", "typ": "town"}
        assert _ist_nur_ort(treffer, "Popovača", "Popovača") is False

    def test_ein_objekttreffer_wird_nicht_markiert(self):
        """Gegenkontrolle 2: der echte Fund nach der Reparatur — typ=amenity,
        gemessen am 2026-08-26."""
        from utils.geocoding import _ist_nur_ort

        treffer = {"lat": 45.9819, "lon": 15.9566, "name": "Terme Jezerčica, Donja Stubica", "typ": "amenity"}
        assert _ist_nur_ort(treffer, "Terme Jezerčica in Popovača", "Terme Jezerčica") is False

    def test_ohne_typ_wird_nicht_markiert(self):
        """Ein fehlendes Feld darf keine Warnung erfinden — sonst wäre jeder
        Dienst ohne Typangabe pauschal verdächtig.

        Der gefundene Name trägt hier das Kennwort, damit wirklich nur die
        fehlende Typangabe geprüft wird und nicht nebenbei die Namensprüfung.
        Ohne diese Trennung maß der Test zwei Dinge gleichzeitig — und wurde
        rot, als die zweite Regel dazukam."""
        from utils.geocoding import _ist_nur_ort

        treffer = {"lat": 1, "lon": 1, "name": "Jezerčica, Donja Stubica"}
        assert _ist_nur_ort(treffer, "Jezerčica in Popovača", "Jezerčica") is False

    def test_ein_treffer_ohne_gemeinsames_kennwort_wird_markiert(self):
        """Der zweite Weg. Am 2026-08-26 gemessen: die Suche nach dem
        „Franziskanerkloster und Museum Moslavina in Kutina" landete auf einem
        FLUSS namens Kutina — keine Gemeinde, also von der Typregel nicht
        erfasst, und trotzdem falsch."""
        from utils.geocoding import _ist_nur_ort

        treffer = {"lat": 45.5, "lon": 16.8, "name": "Kutina, Grad Kutina", "typ": "river"}
        assert _ist_nur_ort(treffer, "Franziskanerkloster und Museum Moslavina in Kutina", "Kutina") is True

    def test_der_behauptete_ort_zaehlt_nicht_als_kennwort(self):
        """Gegenkontrolle zur Zeile darüber — und der Grund, warum der erste
        Entwurf genau falsch herum lief: stand „kutina" in den Kennwörtern,
        trug der Rückfalltreffer „Kutina" es immer, und der Fehlgriff blieb
        unmarkiert."""
        from utils.geocoding import _kennwoerter

        assert "kutina" in _kennwoerter("Franziskanerkloster und Museum Moslavina in Kutina")
        # …und wird in `_ist_nur_ort` abgezogen, siehe Test darüber.

    def test_alle_kennwoerter_muessen_vorkommen_nicht_nur_eines(self):
        """„Mil burger & Milčinkica Sisak" trägt „sisak" und ist trotzdem
        keine Festung. Ein `any` statt `all` hätte das durchgelassen."""
        from utils.geocoding import _ist_nur_ort

        treffer = {"lat": 45.48, "lon": 16.37, "name": "Mil burger & Milčinkica Sisak", "typ": "pastry"}
        assert _ist_nur_ort(treffer, "Festung Sisak Stari Grad", "Sisak Stari Grad") is True

    def test_der_abruf_reicht_die_trefferart_durch(self):
        """Ohne dieses Feld kann `_ist_nur_ort` nichts entscheiden — und
        genau deshalb blieb der Fehler monatelang unsichtbar."""
        import inspect

        from utils import geocoding

        for funktion in (geocoding._nominatim, geocoding._photon):
            assert '"typ"' in inspect.getsource(funktion), f"{funktion.__name__} liefert die Trefferart nicht mehr"


class TestOrtsangabeWiderlegen:
    """
    Die Ortszuordnung des Modells ist PRÜFBAR, sobald die Sache selbst
    gefunden ist.

    Am 2026-08-26 in der Produktion: „Terme Jezerčica in Popovača". Das Bad
    gibt es — in Donja Stubica, **69,2 km** entfernt. Die Behauptung war die
    ganze Zeit widerlegbar, es hat nur niemand gerechnet.

    Diese Klasse ist entstanden, weil eine Sabotage grün blieb: das Abschalten
    der Schranke (`if abstand > WIDERSPRUCH_KM` → `if False`) ließ alle 30
    Tests durchlaufen. Ein Mechanismus ohne roten Test ist eine Zusicherung
    ohne Prüfung.
    """

    @staticmethod
    def _antwort(lat, lon):
        async def _nominatim(query, limit=5):
            return [{"lat": lat, "lon": lon, "name": query, "land": "hr", "typ": "town"}]

        return _nominatim

    @pytest.mark.asyncio
    async def test_der_echte_fall_wird_widerlegt(self, monkeypatch):
        from utils import geocoding

        # Popovača — der behauptete Ort.
        monkeypatch.setattr(geocoding, "_nominatim", self._antwort(45.5710472, 16.6271435))
        # Terme Jezerčica — wo die Sache wirklich liegt.
        gefunden = {"lat": 45.981931, "lon": 15.9565892, "name": "Terme Jezerčica, Donja Stubica"}

        widerlegt, abstand = await geocoding._ortsangabe_pruefen(gefunden, "Terme Jezerčica in Popovača", "Popovača")
        assert widerlegt is True
        assert 68 < abstand < 71, abstand  # gemessen: 69,2 km

    @pytest.mark.asyncio
    async def test_eine_stimmige_zuordnung_wird_nicht_widerlegt(self, monkeypatch):
        """Gegenkontrolle: eine Prüfung, die immer anschlägt, prüft nichts."""
        from utils import geocoding

        monkeypatch.setattr(geocoding, "_nominatim", self._antwort(45.4831, 16.7756))  # Kutina
        gefunden = {"lat": 45.4850, "lon": 16.7790, "name": "Kloster in Kutina"}

        widerlegt, abstand = await geocoding._ortsangabe_pruefen(gefunden, "Kloster in Kutina", "Kutina")
        assert widerlegt is False
        assert abstand is not None and abstand < 1

    @pytest.mark.asyncio
    async def test_ohne_ortsangabe_gibt_es_nichts_zu_widerlegen(self):
        from utils import geocoding

        assert await geocoding._ortsangabe_pruefen({"lat": 45.0, "lon": 16.0}, "Irgendwas", None) == (False, None)

    @pytest.mark.asyncio
    async def test_ein_unauffindbarer_ort_erzeugt_keinen_verdacht(self, monkeypatch):
        """Wer den behaupteten Ort nicht findet, hat nichts gemessen — und
        darf deshalb auch nichts behaupten."""
        from utils import geocoding

        async def findet_nichts(query, limit=5):
            return []

        monkeypatch.setattr(geocoding, "_nominatim", findet_nichts)
        assert await geocoding._ortsangabe_pruefen({"lat": 45.0, "lon": 16.0}, "X in Y", "Y") == (False, None)

    def test_die_ortsangabe_wird_auch_aus_dem_namen_gelesen(self):
        """Für den Altbestand: dort steht die Gemeinde noch IM Namen, es gibt
        kein eigenes Feld."""
        from utils.geocoding import _behaupteter_ort_aus_namen

        assert _behaupteter_ort_aus_namen("Terme Jezerčica in Popovača") == "Popovača"
        assert _behaupteter_ort_aus_namen("Kupa Fluss Aussichtspunkt bei Sisak") == "Sisak"
        assert _behaupteter_ort_aus_namen("Restaurant Purger") is None

    def test_die_schranke_ist_nicht_null(self):
        """Ohne diese Zeile wäre alles oben auch bei WIDERSPRUCH_KM = 0 grün —
        dann würde jede Zuordnung als widerlegt gelten."""
        from utils.geocoding import WIDERSPRUCH_KM

        assert 5 <= WIDERSPRUCH_KM <= 50
