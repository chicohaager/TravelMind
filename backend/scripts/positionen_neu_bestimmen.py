#!/usr/bin/env python3
"""Bestimmt die Positionen VORHANDENER Orte neu — und kennzeichnet ihre Güte.

Der Unterschied zu `positionen_nachtragen.py`: das Schwesterskript fuellt nur
LUECKEN. Dieses hier fasst auch Orte an, die schon eine Position haben — denn
genau die waren am 2026-08-26 das Problem. An 16 Orten einer echten Reise
gemessen: **9** Positionen waren Gemeindemittelpunkte, weil der Geocoder am
Ende seiner Suchkette auf den blossen Ortsnamen zurueckfiel. Auf der Karte
sahen sie aus wie ein echter Fund.

Seit dem 2026-08-26 kann die Kette zweierlei mehr:
  * sie fragt nach dem KERN allein ("Terme Jezerčica" statt nur
    "Terme Jezerčica in Popovača" und "Popovača"), und
  * sie merkt sich, ob die Position nicht nachweislich zur gesuchten Sache
    gehoert (`position_unsicher`).

Beides wirkt nur auf neu bestimmte Positionen. Der Altbestand braucht diesen
Lauf.

    # Was sich aendern wuerde (schreibt NICHTS):
    docker exec travelmind-backend python3 scripts/positionen_neu_bestimmen.py --reise 100007

    # Wirklich schreiben:
    docker exec travelmind-backend python3 scripts/positionen_neu_bestimmen.py --reise 100007 --schreiben

Ohne `--reise` werden alle Reisen bearbeitet. Nominatim erlaubt eine Anfrage
je Sekunde und die Kette stellt bis zu fuenf je Ort — ein Lauf ueber 16 Orte
dauert entsprechend eine gute Minute.
"""

import argparse
import asyncio
import os
import sys

# Auch ueber stdin lauffaehig (`docker exec -i … python3 - < skript.py`).
_wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if "__file__" in globals() else os.getcwd()
sys.path.insert(0, _wurzel)

# ALLE Modelle importieren, nicht nur die zwei benutzten. SQLAlchemy loest
# Beziehungen ueber Klassennamen auf; ohne registriertes `Route` scheitert
# schon das erste SELECT. Siehe CLAUDE.md, "Nebenwirkungs-Importe".
from models import (  # noqa: E402,F401
    audit_log,
    diary,
    expense,
    media,
    notification,
    participant,
    place,
    place_list,
    route,
    settings,
    trip,
    user,
)
from models.database import AsyncSessionLocal  # noqa: E402
from models.place import Place  # noqa: E402
from models.trip import Trip  # noqa: E402
from sqlalchemy import select  # noqa: E402
from utils.geocoding import abstand_km, anker_fuer_ziel, geocode_place  # noqa: E402


def _pfeil(alt, neu):
    """Wie weit ist die Position gewandert? Ohne Zahl ist "geaendert" wertlos."""
    if alt[0] is None or alt[1] is None:
        return "war ohne Position"
    d = abstand_km(alt, neu)
    return f"{d:.1f} km verschoben" if d >= 0.05 else "unveraendert"


async def main() -> int:
    zerleger = argparse.ArgumentParser(description=__doc__)
    zerleger.add_argument("--reise", type=int, help="nur diese Reise-ID")
    zerleger.add_argument("--schreiben", action="store_true", help="Ergebnisse wirklich speichern")
    argumente = zerleger.parse_args()

    async with AsyncSessionLocal() as db:
        abfrage = select(Place)
        if argumente.reise:
            abfrage = abfrage.where(Place.trip_id == argumente.reise)
        orte = (await db.execute(abfrage.order_by(Place.trip_id, Place.id))).scalars().all()
        if not orte:
            print("Keine Orte gefunden.")
            return 1

        anker_je_reise = {}
        geaendert = nur_ort = widerlegt = ohne = 0

        for ort in orte:
            if ort.trip_id not in anker_je_reise:
                reise = (await db.execute(select(Trip).where(Trip.id == ort.trip_id))).scalar_one_or_none()
                ziel = reise.destination if reise else None
                anker_je_reise[ort.trip_id] = (ziel, await anker_fuer_ziel(ziel) if ziel else None)
            ziel, anker = anker_je_reise[ort.trip_id]

            treffer = await geocode_place(name=ort.name, address=ort.address, anker=anker)
            if not treffer:
                ohne += 1
                print(f"  ✗ keine Position   {ort.name}   (bisher: {ort.latitude}, {ort.longitude})")
                continue

            neu = (treffer["lat"], treffer["lon"])
            bewegung = _pfeil((ort.latitude, ort.longitude), neu)
            marken = []
            if treffer.get("nur_ort"):
                marken.append("POSITION UNSICHER")
                nur_ort += 1
            if treffer.get("ortsangabe_widerlegt"):
                marken.append(f"ORTSANGABE WIDERLEGT ({treffer['abweichung_km']} km)")
                widerlegt += 1
            if bewegung != "unveraendert":
                geaendert += 1

            print(
                f"  {'⚠' if marken else ' '} {ort.name[:46]:<46} {bewegung:<22} "
                f"{' | '.join(marken) if marken else ''}\n"
                f"{'':6}{neu[0]:.6f},{neu[1]:.6f}  typ={treffer.get('typ')}  "
                f"variante={treffer.get('variante')!r}"
            )

            if argumente.schreiben:
                ort.latitude, ort.longitude = neu
                ort.position_unsicher = bool(treffer.get("nur_ort"))

        print(
            f"\n{len(orte)} Orte geprueft · {geaendert} Positionen wuerden sich aendern · "
            f"{nur_ort} unsichere Positionen · {widerlegt} Ortsangaben widerlegt · {ohne} ohne Treffer"
        )
        if argumente.schreiben:
            await db.commit()
            print("→ gespeichert.")
        else:
            print("→ NICHTS gespeichert. Mit --schreiben wiederholen.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
