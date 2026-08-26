"""
Geokodierung über OpenStreetMap (Nominatim, mit Photon als Rückfall).

Umgebaut am 2026-08-26, nachdem eine Kroatien-Reise acht Orte mit den
Koordinaten 0/0 bekam. Die Karte zeigte daraufhin die Null-Insel im Golf von
Guinea — einfarbig blauer Ozean bei Zoomstufe 18, alle acht Marker exakt
übereinander. Das sah nach "die Kacheln laden nicht" aus; tatsächlich luden
alle Kacheln mit HTTP 200 und zeigten korrekt offenes Meer.

Zwei Fehler steckten darin, beide am laufenden Dienst gemessen:

1. **Die Suchanfrage.** Gebaut wurde `"{name}, {destination}"`. Ist das
   Reiseziel eine Hausadresse ("Gornja Jelenska Kamenica 55"), entsteht
   daraus "Ethno-Dorf Čigoč, Gornja Jelenska Kamenica 55" — ein Dorf 23 km
   entfernt an einer fremden Hausnummer. Gemessen: 0 von 8 Orten gefunden.

2. **Der Fehlschlag war still.** Bei `geocoding_no_results` wurden die
   ursprünglichen 0/0 zurückgegeben und gespeichert. Ein Ort ohne Position
   sah damit aus wie ein Ort im Atlantik — der Fehler war nicht harmlos
   gemacht, sondern unsichtbar.

Was jetzt passiert:

* Der Name wird in **Varianten** zerlegt, von spezifisch nach allgemein.
  KI-erzeugte Namen tragen deutsche Gattungswörter, die kein Geocoder kennt
  ("Ethno-Dorf Čigoč", "Lonjsko Polje Naturpark").
* Ein Ortsbezug hinter "in/bei/an" wird zum **Ortszusatz**, nicht gelöscht.
  Eine frühere Fassung schnitt ihn ab: "Schloss Erdödy in Jastrebarsko" wurde
  zu "Erdödy" und fand das Schloss Erdödy-Rubido 60 km in die falsche
  Richtung. Es gibt mehrere Erdödy-Schlösser; genau der abgeschnittene Teil
  löste die Mehrdeutigkeit auf. Der Treffer lag im Umkreis und sah dadurch
  richtig aus.
* Ein **Anker** aus dem Reiseziel begrenzt die Suche. Ohne ihn liefert Photon
  zu "Ethno-Dorf Čigoč" ein Etno-Dorf in Bosnien und zu "Altstadt Sisak" ein
  "Sisart" in Polen — ein Treffer am falschen Ort ist schlimmer als keiner.
* Findet nichts, wird **None** zurückgegeben. Nie 0/0.

Gemessen an denselben acht Orten: vorher 0/8, nachher 7/8 über Nominatim,
8/8 mit Photon-Rückfall. Die Trefferzahl ist dabei nicht das Qualitätsmaß —
"Altstadt Sisak" liefert einen Burgerladen in Sisak und "Schloss Erdödy" eine
Pizzeria 500 m neben dem Schloss. Die Koordinate taugt für eine Reisekarte,
die Zuordnung ist eine Näherung. Deshalb trägt jedes Ergebnis mit, WIE es
gefunden wurde (`quelle`, `abstand_km`), und ein unsicherer Treffer ist im
Zweifel besser sichtbar als still.
"""

import asyncio
import math
import re
import unicodedata
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import httpx
import structlog

logger = structlog.get_logger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"
USER_AGENT = "TravelMind/1.0 (self-hosted travel planning app)"
RATE_LIMIT_DELAY = 1.0  # Nominatim erlaubt eine Anfrage je Sekunde

# Wie weit ein Treffer vom Reiseziel entfernt sein darf. 150 km deckt einen
# Tagesausflug ab; darüber hinaus ist ein Namenstreffer eher Zufall als Ort.
MAX_ABSTAND_KM = 150.0

# Trefferarten, die eine SIEDLUNG bezeichnen und nicht die gesuchte Sache.
# Landet die Suche hier, ist die Position ortsgenau, nicht objektgenau: der
# Mittelpunkt von Popovača ist keine Antwort auf "wo liegt Terme Jezerčica".
# Ab dieser Entfernung gilt eine Ortsangabe des Modells als WIDERLEGT.
# 25 km ist grosszuegig: eine Gemeinde kann ausgedehnt sein, und "bei X" darf
# ein Stueck ausserhalb liegen. Am 2026-08-26 gemessen lag der Fehlgriff bei
# 69,2 km ("Terme Jezerčica in Popovača" -> Donja Stubica), der zulaessige
# Fall bei unter 5 km.
WIDERSPRUCH_KM = 25.0

GEMEINDE_TYPEN = {
    "administrative",
    "borough",
    "city",
    "city_district",
    "county",
    "hamlet",
    "municipality",
    "postcode",
    "state",
    "neighbourhood",
    "quarter",
    "suburb",
    "town",
    "village",
}

# Gattungswörter, die ein Geocoder nicht als Namensbestandteil kennt. Bei
# KI-erzeugten Namen stehen sie fast immer vorn.
_GATTUNG = re.compile(r"""(?ix) ^\s*(?:
      ethno?-?dorf | etno-?dorf | ethno?-?restaurant | etno-?restaurant |
      restaurant | gasthaus | taverne | konoba | wanderweg | rundweg | pfad |
      naturpark | nationalpark | regionalpark | park | altstadt | schloss |
      burg | festung | museum | kirche | kathedrale | kloster | markt |
      aussichtspunkt | strand | bucht | wasserfall | brücke | turm | denkmal
    )\b[\s-]*""")
# Dasselbe am Ende ("Lonjsko Polje Naturpark").
_ANHANG = re.compile(r"(?i)\s+(?:naturpark|nationalpark|park|museum|restaurant|festung|schloss|burg)\s*$")
# "X in/bei Y" — Y ist der Ortsbezug und bleibt erhalten.
_ORTSBEZUG = re.compile(r"(?i)^(.*?)\s+(?:in|bei|an|am|nahe|von)\s+(.+)$")


def suchvarianten(name: str) -> List[str]:
    """
    Zerlegt einen Ortsnamen in Suchvarianten, von spezifisch nach allgemein.

    Jede Variante ist eine eigene Anfrage; die erste, die einen plausiblen
    Treffer liefert, gewinnt. Die Reihenfolge ist der Punkt: die
    ungeschnittene Form zuerst, damit ein exakter Treffer nicht durch eine
    Vereinfachung verdrängt wird.
    """
    varianten: List[str] = []

    def dazu(text: str) -> None:
        text = text.strip(" ,-")
        if text and text not in varianten:
            varianten.append(text)

    dazu(name)
    ohne_gattung = _GATTUNG.sub("", name).strip()
    dazu(ohne_gattung)

    for kandidat in (ohne_gattung, name):
        treffer = _ORTSBEZUG.match(kandidat)
        if treffer:
            kern = _GATTUNG.sub("", treffer.group(1)).strip()
            ort = _GATTUNG.sub("", treffer.group(2)).strip()
            if kern and ort:
                dazu(f"{kern}, {ort}")
                # Der KERN ALLEIN. Diese Frage fehlte bis zum 2026-08-26, und
                # sie ist die einzige, die eine falsche Ortsangabe des Modells
                # aufdecken kann: "Terme Jezerčica in Popovača" liefert unter
                # den ersten beiden Varianten NICHTS (gemessen), unter dem
                # blossen Kern aber den echten Ort in Donja Stubica —
                # 69,2 km von Popovača entfernt.
                #
                # Ein Kern allein kann daneben greifen ("Erdödy" findet ein
                # Erdody in der Slowakei, 346,8 km). Das faengt die
                # 150-km-Schranke in `_naechster` ab; der Ortsname bleibt
                # deshalb als letzte Variante stehen.
                dazu(kern)
            dazu(ort)  # notfalls wenigstens der Ort selbst

    dazu(_ANHANG.sub("", ohne_gattung or name).strip())
    return varianten


def abstand_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Großkreisabstand in Kilometern (Haversine)."""
    dy = math.radians(b[0] - a[0])
    dx = math.radians(b[1] - a[1])
    h = math.sin(dy / 2) ** 2 + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dx / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def _ist_null_insel(lat: Optional[float], lon: Optional[float]) -> bool:
    """
    0/0 ist keine Position, sondern ein Ersatzwert.

    Die Null-Insel liegt im Golf von Guinea. Ein Reiseort landet dort nie
    absichtlich; steht es trotzdem in den Daten, ist eine Geokodierung
    fehlgeschlagen und wurde als Erfolg gespeichert.
    """
    if lat is None or lon is None:
        return False
    return abs(lat) < 0.001 and abs(lon) < 0.001


async def _nominatim(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    params = {"q": query, "format": "json", "limit": limit, "addressdetails": 1}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            antwort = await client.get(NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT})
            antwort.raise_for_status()
            ergebnisse = antwort.json()
        await asyncio.sleep(RATE_LIMIT_DELAY)
        return [
            {
                "lat": float(e["lat"]),
                "lon": float(e["lon"]),
                "name": e.get("display_name", ""),
                # Laenderkennung: entscheidet mit, welcher Kandidat gewinnt.
                # Fehlt sie, zaehlt nur die Entfernung — und ein "Zeleni vir"
                # in Bosnien gewinnt gegen den kroatischen, weil er naeher am
                # Anker liegt.
                "land": ((e.get("address") or {}).get("country_code") or "").lower() or None,
                # Die ART des Treffers. Ohne sie kann niemand merken, dass die
                # Suche nach einem Thermalbad eine GEMEINDE gefunden hat —
                # genau so kam am 2026-08-26 der Stadtmittelpunkt von Popovača
                # als Position von "Terme Jezerčica" in die Datenbank.
                "typ": e.get("addresstype") or e.get("type"),
            }
            for e in ergebnisse
        ]
    except httpx.HTTPError as fehler:
        logger.warning("geocoding_http_fehler", dienst="nominatim", query=query, fehler=str(fehler))
        return []
    except (ValueError, KeyError, TypeError) as fehler:
        logger.warning("geocoding_antwort_unlesbar", dienst="nominatim", query=query, fehler=str(fehler))
        return []


async def _photon(query: str, anker: Optional[Tuple[float, float]] = None) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"q": query, "limit": 5, "lang": "de"}
    if anker:
        params["lat"], params["lon"] = anker
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            antwort = await client.get(PHOTON_URL, params=params, headers={"User-Agent": USER_AGENT})
            antwort.raise_for_status()
            daten = antwort.json()
        aus = []
        for eintrag in daten.get("features", []):
            koordinaten = eintrag.get("geometry", {}).get("coordinates")
            if not koordinaten or len(koordinaten) < 2:
                continue
            eigenschaften = eintrag.get("properties", {})
            aus.append(
                {
                    "lat": float(koordinaten[1]),
                    "lon": float(koordinaten[0]),
                    "name": eigenschaften.get("name", ""),
                    "land": (eigenschaften.get("countrycode") or "").lower() or None,
                    "typ": eigenschaften.get("osm_value") or eigenschaften.get("type"),
                }
            )
        return aus
    except httpx.HTTPError as fehler:
        logger.warning("geocoding_http_fehler", dienst="photon", query=query, fehler=str(fehler))
        return []
    except (ValueError, KeyError, TypeError) as fehler:
        logger.warning("geocoding_antwort_unlesbar", dienst="photon", query=query, fehler=str(fehler))
        return []


def _naechster(
    kandidaten: List[Dict[str, Any]],
    anker: Optional[Tuple[float, float]],
    max_km: float,
    land: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Wählt den zum Anker nächstgelegenen Kandidaten innerhalb der Schranke.

    Treffer im Land des Reiseziels haben **Vorrang**. Die Entfernung allein
    reicht nicht: "Etno-Restaurant Zeleni Vir" fand ein Zeleni vir bei Banja
    Luka, 107 km entfernt und damit innerhalb der Schranke — aber in Bosnien,
    während die Reise in Kroatien stattfindet. Ein Treffer im falschen Land
    ist schlimmer als keiner, weil er wie ein Ergebnis aussieht.

    Ein anderes Land wird nicht ausgeschlossen, nur nachgeordnet: ein
    Tagesausflug über die Grenze ist ein normaler Reisewunsch. Fehlt die
    Länderkennung, zählt nur die Entfernung.

    Ohne Anker gibt es keine Schranke — dann ist der erste Treffer der beste,
    den der Dienst kennt, und mehr lässt sich ohne Bezugspunkt nicht sagen.
    """
    brauchbar = [k for k in kandidaten if not _ist_null_insel(k["lat"], k["lon"])]
    if not brauchbar:
        return None
    if anker is None:
        treffer = dict(brauchbar[0])
        treffer["abstand_km"] = None
        return treffer
    bewertet = [(abstand_km(anker, (k["lat"], k["lon"])), k) for k in brauchbar]
    im_umkreis = [(d, k) for d, k in bewertet if d <= max_km]
    if not im_umkreis:
        return None
    # Sortierschlüssel: erst "richtiges Land", dann Entfernung.
    entfernung, treffer = min(
        im_umkreis,
        key=lambda x: (0 if (land and x[1].get("land") == land) else 1, x[0]),
    )
    treffer = dict(treffer)
    treffer["abstand_km"] = round(entfernung, 1)
    treffer["fremdes_land"] = bool(land and treffer.get("land") and treffer["land"] != land)
    return treffer


# Anker -> Laenderkennung. Bewusst nur ein Beiwerk: die Signatur von
# `anker_fuer_ziel` bleibt ein Koordinatenpaar, damit kein Aufrufer sich
# aendern muss, und `geocode_place` kann das Land trotzdem nachschlagen.
_anker_land: Dict[Tuple[float, float], Optional[str]] = {}


async def anker_fuer_ziel(destination: Optional[str]) -> Optional[Tuple[float, float]]:
    """
    Löst das Reiseziel zu einem Bezugspunkt auf.

    Ist das Ziel eine Hausadresse, trägt sie als Anker — als Suchzusatz für
    einzelne Orte taugt sie dagegen nicht (das war der ursprüngliche Fehler).
    Schlägt die volle Adresse fehl, wird sie schrittweise gekürzt.
    """
    if not destination:
        return None
    for kandidat in (destination, re.sub(r"\s*\d+\s*$", "", destination).strip()):
        if not kandidat:
            continue
        treffer = await _nominatim(kandidat, limit=1)
        if treffer:
            logger.info("geocoding_anker", ziel=destination, benutzt=kandidat, land=treffer[0].get("land"))
            _anker_land[(treffer[0]["lat"], treffer[0]["lon"])] = treffer[0].get("land")
            return (treffer[0]["lat"], treffer[0]["lon"])
    logger.warning("geocoding_anker_fehlt", ziel=destination)
    return None


# Woerter, die keinen Ort unterscheiden. Bewusst kurz gehalten: die Liste soll
# Gattungsbegriffe wegnehmen, nicht Eigennamen erraten.
_ALLERWELTSWOERTER = {
    "altstadt",
    "aussichtspunkt",
    "burg",
    "dorf",
    "ethno",
    "etno",
    "festung",
    "fluss",
    "grad",
    "kirche",
    "kloster",
    "konoba",
    "museum",
    "nationalpark",
    "naturpark",
    "park",
    "restaurant",
    "schloss",
    "stadt",
    "wanderweg",
}


def _entkleidet(text: str) -> str:
    """Kleinbuchstaben ohne diakritische Zeichen — 'Jezerčica' und 'Jezercica'
    sollen dasselbe Wort sein."""
    zerlegt = unicodedata.normalize("NFKD", text.lower())
    return "".join(z for z in zerlegt if not unicodedata.combining(z))


def _kennwoerter(name: str) -> List[str]:
    """Die Woerter, die diesen Ort von anderen unterscheiden."""
    roh = re.split(r"[^0-9a-zA-ZÀ-ÿčćđšžČĆĐŠŽ]+", _entkleidet(name))
    return [w for w in roh if len(w) >= 4 and w not in _ALLERWELTSWOERTER]


def _ist_nur_ort(treffer: Dict[str, Any], name: str, variante: str) -> bool:
    """Gehoert diese Position nachweislich zur gesuchten Sache — oder nicht?

    Am 2026-08-26 an den 16 Orten einer echten Reise gemessen. Erst kannte
    diese Pruefung nur SIEDLUNGSTREFFER; der Trockenlauf zeigte, dass das zu
    eng ist. Die Kette lieferte ausserdem:

        "Franziskanerkloster … in Kutina"   -> typ=river   (ein Fluss)
        "Altstadt Sisak mit Festung …"      -> typ=pastry  (eine Baeckerei)
        "Etno-Restaurant Zeleni Vir"        -> typ=valley  (ein Tal)

    Alle drei waren unmarkiert, weil sie keine Gemeinde sind — und alle drei
    sind genauso falsch. Deshalb zwei Wege, und einer genuegt:

    1. **Siedlungstreffer ueber eine Abkuerzung.** Wer nach "Popovača" sucht
       und Popovača bekommt, hat gefunden was er wollte; wer nach
       "Terme Jezerčica in Popovača" sucht und Popovača bekommt, nicht.

    2. **Kein gemeinsames Kennwort.** Traegt der gefundene Eintrag keines der
       unterscheidenden Woerter des gesuchten Namens, ist es etwas anderes.
       "Gostionica Purger" traegt "purger" — passt. "Kutina" traegt weder
       "franziskanerkloster" noch "moslavina" — passt nicht.

    **Was das NICHT faengt:** einen Treffer, der zufaellig denselben Namen
    traegt. "Schloss Erdödy in Jastrebarsko" findet eine *Pizzeria Erdody* —
    Kennwort vorhanden, Sache falsch. Diese Pruefung macht das Offensichtliche
    sichtbar, nicht das Subtile.
    """
    if treffer.get("typ") in GEMEINDE_TYPEN and variante.strip().lower() != name.strip().lower():
        return True

    # Der behauptete Ort zaehlt hier NICHT mit. Erster Versuch tat es, und das
    # Kriterium ging genau falsch herum: bei "Franziskanerkloster … in Kutina"
    # stand "kutina" in den Kennwoertern, der Rueckfalltreffer hiess "Kutina",
    # also fand sich immer eine Ueberschneidung — der Fehlgriff blieb
    # unmarkiert. Ob die Ortsangabe stimmt, klaert `_ortsangabe_pruefen`;
    # hier geht es allein um die SACHE.
    ohne = set(_kennwoerter(_behaupteter_ort_aus_namen(name) or ""))
    kennwoerter = [w for w in _kennwoerter(name) if w not in ohne]
    if not kennwoerter:
        # Ohne unterscheidendes Wort laesst sich nichts sagen — dann wird auch
        # nichts behauptet. Ein Verdacht ohne Messung ist keiner.
        return False
    gefunden = _entkleidet(treffer.get("name") or "")
    # ALLE, nicht irgendeines: "Mil burger & Milčinkica Sisak" traegt "sisak"
    # und ist trotzdem keine Festung.
    return not all(w in gefunden for w in kennwoerter)


async def _ortsangabe_pruefen(
    treffer: Dict[str, Any], name: str, behaupteter_ort: Optional[str]
) -> Tuple[bool, Optional[float]]:
    """Liegt der gefundene Ort wirklich dort, wo das Modell behauptet?

    Ein Sprachmodell schreibt Ortszuordnungen mit derselben Sicherheit hin wie
    Namen — und liegt dabei falsch, ohne dass es jemandem auffaellt. Am
    2026-08-26 in der Produktion: "Terme Jezerčica in Popovača". Das Bad gibt
    es, aber in Donja Stubica, **69,2 km** entfernt.

    Die Behauptung ist pruefbar, sobald die Sache SELBST gefunden ist: dann
    wird der behauptete Ort einzeln aufgeloest und die Entfernung gerechnet.
    Ueber `WIDERSPRUCH_KM` ist die Zuordnung widerlegt — kein Verdacht,
    sondern eine Messung.

    Gibt (widerlegt, abstand_km) zurueck. Ohne behauptete Ortsangabe oder
    ohne auffindbaren Ort gibt es nichts zu widerlegen: (False, None).
    """
    if not behaupteter_ort:
        return (False, None)
    ortstreffer = await _nominatim(behaupteter_ort, limit=1)
    if not ortstreffer:
        return (False, None)
    abstand = abstand_km((treffer["lat"], treffer["lon"]), (ortstreffer[0]["lat"], ortstreffer[0]["lon"]))
    if abstand > WIDERSPRUCH_KM:
        logger.warning(
            "geocoding_ortsangabe_widerlegt",
            name=name,
            behaupteter_ort=behaupteter_ort,
            gefunden=treffer["name"],
            abstand_km=round(abstand, 1),
            schranke_km=WIDERSPRUCH_KM,
            hinweis="Die Ortszuordnung im Namen ist falsch — die Sache liegt woanders",
        )
        return (True, round(abstand, 1))
    return (False, round(abstand, 1))


def _behaupteter_ort_aus_namen(name: str) -> Optional[str]:
    """Zieht das "Y" aus "X in Y" — fuer Altbestand ohne eigenes Feld."""
    treffer = _ORTSBEZUG.match(_GATTUNG.sub("", name).strip()) or _ORTSBEZUG.match(name)
    if not treffer:
        return None
    ort = _GATTUNG.sub("", treffer.group(2)).strip()
    return ort or None


async def geocode_place(
    name: str,
    address: Optional[str] = None,
    destination: Optional[str] = None,
    anker: Optional[Tuple[float, float]] = None,
    land: Optional[str] = None,
    behaupteter_ort: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Sucht die Position eines Ortes. Gibt None zurück, wenn nichts trägt.

    `anker` kann von aussen mitgegeben werden, damit beim Massenimport das
    Reiseziel nur EINMAL aufgelöst wird statt je Ort.
    """
    if anker is None and destination:
        anker = await anker_fuer_ziel(destination)

    # Das Land des Reiseziels bevorzugt Treffer im richtigen Staat.
    anker_land = _anker_land.get(anker) if anker else None

    # Eine echte Adresse ist die verlässlichste Angabe — zuerst versuchen.
    if address:
        treffer = _naechster(await _nominatim(address), anker, MAX_ABSTAND_KM, anker_land)
        if treffer:
            logger.info("geocoding_treffer", name=name, quelle="nominatim/adresse", gefunden=treffer["name"])
            return {**treffer, "quelle": "nominatim/adresse"}

    varianten = suchvarianten(name)

    for variante in varianten:
        anfrage = f"{variante}, {land}" if land else variante
        treffer = _naechster(await _nominatim(anfrage), anker, MAX_ABSTAND_KM, anker_land)
        if treffer:
            nur_ort = _ist_nur_ort(treffer, name, variante)
            logger.info(
                "geocoding_treffer",
                name=name,
                quelle="nominatim",
                variante=variante,
                gefunden=treffer["name"],
                typ=treffer.get("typ"),
                nur_ort=nur_ort,
                abstand_km=treffer.get("abstand_km"),
                fremdes_land=treffer.get("fremdes_land"),
            )
            if nur_ort:
                logger.warning(
                    "geocoding_nur_ortsgenau",
                    name=name,
                    variante=variante,
                    gefunden=treffer["name"],
                    typ=treffer.get("typ"),
                    hinweis="Gefunden wurde die SIEDLUNG, nicht die genannte Sache",
                )
            widerlegt, abweichung = (False, None)
            if not nur_ort:
                # Nur pruefbar, wenn die SACHE gefunden wurde. Steckt hinter
                # dem Treffer ohnehin nur die Gemeinde, gibt es nichts zu
                # vergleichen — dann ist `nur_ort` die Auskunft.
                widerlegt, abweichung = await _ortsangabe_pruefen(
                    treffer, name, behaupteter_ort or _behaupteter_ort_aus_namen(name)
                )
            return {
                **treffer,
                "quelle": "nominatim",
                "variante": variante,
                "nur_ort": nur_ort,
                "ortsangabe_widerlegt": widerlegt,
                "abweichung_km": abweichung,
            }

    # Photon ist fehlertoleranter, aber liefert IMMER etwas — ohne Anker also
    # regelmäßig einen Ort im falschen Land. Nur mit Anker sinnvoll.
    if anker:
        for variante in varianten:
            treffer = _naechster(await _photon(variante, anker), anker, MAX_ABSTAND_KM, anker_land)
            if treffer:
                logger.info(
                    "geocoding_treffer",
                    name=name,
                    quelle="photon",
                    variante=variante,
                    gefunden=treffer["name"],
                    abstand_km=treffer.get("abstand_km"),
                )
                return {
                    **treffer,
                    "quelle": "photon",
                    "variante": variante,
                    "nur_ort": _ist_nur_ort(treffer, name, variante),
                }

    logger.warning(
        "geocoding_ohne_treffer",
        name=name,
        varianten=varianten,
        hatte_anker=anker is not None,
        hinweis="Ort wird OHNE Position gespeichert — nicht auf 0/0",
    )
    return None


class Position(NamedTuple):
    """Was eine Geokodierung zurueckgibt — samt Vorbehalt.

    Vorher war es ein blosses `(lat, lon)`. Damit ging genau die Auskunft
    verloren, die den Unterschied macht: ob die Koordinate die SACHE meint
    oder nur den Ort drumherum. Am 2026-08-26 waren 9 von 16 Positionen einer
    echten Reise Gemeindemittelpunkte, und niemand konnte es sehen.
    """

    lat: Optional[float]
    lon: Optional[float]
    nur_ort: Optional[bool] = None
    ortsangabe_widerlegt: bool = False
    abweichung_km: Optional[float] = None


async def geocode_location(
    name: str, address: Optional[str] = None, destination: Optional[str] = None
) -> Optional[Tuple[float, float]]:
    """Rückwärtskompatible Hülle: (lat, lon) oder None."""
    treffer = await geocode_place(name=name, address=address, destination=destination)
    return (treffer["lat"], treffer["lon"]) if treffer else None


async def geocode_if_missing(
    name: str,
    latitude: Optional[float],
    longitude: Optional[float],
    address: Optional[str] = None,
    destination: Optional[str] = None,
    anker: Optional[Tuple[float, float]] = None,
    land: Optional[str] = None,
    behaupteter_ort: Optional[str] = None,
) -> Position:
    """
    Ergänzt fehlende Koordinaten.

    Der Unterschied zur alten Fassung steht in der Rückgabe: schlägt die
    Suche fehl, kommt **(None, None)** zurück und nicht (0.0, 0.0). Ein Ort
    ohne Position ist damit im Datenbestand als solcher erkennbar, statt sich
    als Ort im Golf von Guinea auszugeben.
    """
    hat_position = latitude is not None and longitude is not None and not _ist_null_insel(latitude, longitude)
    if hat_position:
        # Mitgebrachte Koordinaten: ueber ihre Genauigkeit ist nichts bekannt.
        # `None` heisst hier "ungeprueft" und nicht "objektgenau" — der
        # Unterschied entscheidet, ob die Karte etwas kennzeichnen darf.
        return Position(latitude, longitude)

    treffer = await geocode_place(
        name=name,
        address=address,
        destination=destination,
        anker=anker,
        land=land,
        behaupteter_ort=behaupteter_ort,
    )
    if treffer:
        return Position(
            treffer["lat"],
            treffer["lon"],
            treffer.get("nur_ort"),
            bool(treffer.get("ortsangabe_widerlegt")),
            treffer.get("abweichung_km"),
        )
    return Position(None, None)


async def batch_geocode_places(places: list, destination: Optional[str] = None) -> list:
    """
    Geokodiert mehrere Orte. Das Reiseziel wird EINMAL zum Anker aufgelöst.

    Orte ohne Treffer behalten `latitude`/`longitude` als None — der Aufrufer
    entscheidet, wie er sie darstellt, aber er bekommt keine Falschangabe.
    """
    anker = await anker_fuer_ziel(destination) if destination else None
    aktualisiert = []
    for eintrag in places:
        position = await geocode_if_missing(
            name=eintrag.get("name", ""),
            latitude=eintrag.get("latitude"),
            longitude=eintrag.get("longitude"),
            address=eintrag.get("address"),
            anker=anker,
        )
        aktualisiert.append(
            {
                **eintrag,
                "latitude": position.lat,
                "longitude": position.lon,
                "position_unsicher": position.nur_ort,
            }
        )
    return aktualisiert
