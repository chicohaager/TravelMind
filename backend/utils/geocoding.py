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
from typing import Any, Dict, List, Optional, Tuple

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
        return [{"lat": float(e["lat"]), "lon": float(e["lon"]), "name": e.get("display_name", "")} for e in ergebnisse]
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
    kandidaten: List[Dict[str, Any]], anker: Optional[Tuple[float, float]], max_km: float
) -> Optional[Dict[str, Any]]:
    """
    Wählt den zum Anker nächstgelegenen Kandidaten innerhalb der Schranke.

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
    entfernung, treffer = min(im_umkreis, key=lambda x: x[0])
    treffer = dict(treffer)
    treffer["abstand_km"] = round(entfernung, 1)
    return treffer


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
            logger.info("geocoding_anker", ziel=destination, benutzt=kandidat)
            return (treffer[0]["lat"], treffer[0]["lon"])
    logger.warning("geocoding_anker_fehlt", ziel=destination)
    return None


async def geocode_place(
    name: str,
    address: Optional[str] = None,
    destination: Optional[str] = None,
    anker: Optional[Tuple[float, float]] = None,
    land: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Sucht die Position eines Ortes. Gibt None zurück, wenn nichts trägt.

    `anker` kann von aussen mitgegeben werden, damit beim Massenimport das
    Reiseziel nur EINMAL aufgelöst wird statt je Ort.
    """
    if anker is None and destination:
        anker = await anker_fuer_ziel(destination)

    # Eine echte Adresse ist die verlässlichste Angabe — zuerst versuchen.
    if address:
        treffer = _naechster(await _nominatim(address), anker, MAX_ABSTAND_KM)
        if treffer:
            logger.info("geocoding_treffer", name=name, quelle="nominatim/adresse", gefunden=treffer["name"])
            return {**treffer, "quelle": "nominatim/adresse"}

    varianten = suchvarianten(name)

    for variante in varianten:
        anfrage = f"{variante}, {land}" if land else variante
        treffer = _naechster(await _nominatim(anfrage), anker, MAX_ABSTAND_KM)
        if treffer:
            logger.info(
                "geocoding_treffer",
                name=name,
                quelle="nominatim",
                variante=variante,
                gefunden=treffer["name"],
                abstand_km=treffer.get("abstand_km"),
            )
            return {**treffer, "quelle": "nominatim", "variante": variante}

    # Photon ist fehlertoleranter, aber liefert IMMER etwas — ohne Anker also
    # regelmäßig einen Ort im falschen Land. Nur mit Anker sinnvoll.
    if anker:
        for variante in varianten:
            treffer = _naechster(await _photon(variante, anker), anker, MAX_ABSTAND_KM)
            if treffer:
                logger.info(
                    "geocoding_treffer",
                    name=name,
                    quelle="photon",
                    variante=variante,
                    gefunden=treffer["name"],
                    abstand_km=treffer.get("abstand_km"),
                )
                return {**treffer, "quelle": "photon", "variante": variante}

    logger.warning(
        "geocoding_ohne_treffer",
        name=name,
        varianten=varianten,
        hatte_anker=anker is not None,
        hinweis="Ort wird OHNE Position gespeichert — nicht auf 0/0",
    )
    return None


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
) -> Tuple[Optional[float], Optional[float]]:
    """
    Ergänzt fehlende Koordinaten.

    Der Unterschied zur alten Fassung steht in der Rückgabe: schlägt die
    Suche fehl, kommt **(None, None)** zurück und nicht (0.0, 0.0). Ein Ort
    ohne Position ist damit im Datenbestand als solcher erkennbar, statt sich
    als Ort im Golf von Guinea auszugeben.
    """
    hat_position = latitude is not None and longitude is not None and not _ist_null_insel(latitude, longitude)
    if hat_position:
        return (latitude, longitude)

    treffer = await geocode_place(name=name, address=address, destination=destination, anker=anker, land=land)
    if treffer:
        return (treffer["lat"], treffer["lon"])
    return (None, None)


async def batch_geocode_places(places: list, destination: Optional[str] = None) -> list:
    """
    Geokodiert mehrere Orte. Das Reiseziel wird EINMAL zum Anker aufgelöst.

    Orte ohne Treffer behalten `latitude`/`longitude` als None — der Aufrufer
    entscheidet, wie er sie darstellt, aber er bekommt keine Falschangabe.
    """
    anker = await anker_fuer_ziel(destination) if destination else None
    aktualisiert = []
    for eintrag in places:
        lat, lon = await geocode_if_missing(
            name=eintrag.get("name", ""),
            latitude=eintrag.get("latitude"),
            longitude=eintrag.get("longitude"),
            address=eintrag.get("address"),
            anker=anker,
        )
        aktualisiert.append({**eintrag, "latitude": lat, "longitude": lon})
    return aktualisiert
