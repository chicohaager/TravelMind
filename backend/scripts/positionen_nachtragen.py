#!/usr/bin/env python3
"""
Trägt fehlende Positionen für bereits gespeicherte Orte nach.

Gedacht für Orte, die vor dem 2026-08-26 angelegt wurden: damals speicherte
eine fehlgeschlagene Geokodierung 0/0, Migration 0006 hat daraus NULL
gemacht. Dieses Skript sucht die Positionen nun mit der reparierten Kette
nach (utils/geocoding.py).

Benutzt bewusst denselben Code wie die Anwendung. Eine Sonderlösung hier
würde etwas anderes messen als das, was im Betrieb läuft — und genau diese
Differenz war die Ursache des ursprünglichen Fehlers.

    # Was wäre zu tun (schreibt nichts):
    python3 scripts/positionen_nachtragen.py

    # Wirklich schreiben:
    python3 scripts/positionen_nachtragen.py --schreiben

    # Nur eine Reise:
    python3 scripts/positionen_nachtragen.py --reise 100007 --schreiben

Ohne `--schreiben` wird nichts verändert. Nominatim erlaubt eine Anfrage je
Sekunde, und die Variantenkette stellt bis zu vier je Ort — bei vielen Orten
dauert der Lauf entsprechend.
"""

import argparse
import asyncio
import os
import sys

# Auch ueber stdin lauffaehig (`docker exec -i … python3 - < skript.py`):
# das Container-Dateisystem ist read-only, hineinkopieren geht nicht, und
# ohne Datei gibt es kein `__file__`.
_wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if "__file__" in globals() else os.getcwd()
sys.path.insert(0, _wurzel)

# ALLE Modelle importieren, nicht nur die zwei benutzten.
#
# SQLAlchemy loest Beziehungen ueber Klassennamen auf: `Trip` verweist auf
# `Route`, und ohne dessen Registrierung scheitert schon das erste SELECT mit
# "failed to locate a name ('Route')". Das ist derselbe Nebenwirkungs-Import,
# den models/database.py und tests/conftest.py fuehren — siehe CLAUDE.md.
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
from utils.geocoding import anker_fuer_ziel, geocode_place  # noqa: E402


async def nachtragen(reise_id: int | None, schreiben: bool) -> int:
    async with AsyncSessionLocal() as db:
        abfrage = select(Place, Trip).join(Trip, Trip.id == Place.trip_id).where(Place.latitude.is_(None))
        if reise_id is not None:
            abfrage = abfrage.where(Place.trip_id == reise_id)
        paare = (await db.execute(abfrage)).all()

        if not paare:
            print("Kein Ort ohne Position. Nichts zu tun.")
            return 0

        # Anker je Reise nur EINMAL auflösen.
        anker_je_reise: dict[int, tuple[float, float] | None] = {}
        gefunden = 0

        print(
            f"{len(paare)} Ort(e) ohne Position." + ("" if schreiben else "  [Probelauf — es wird nichts geschrieben]")
        )

        for ort, reise in paare:
            if reise.id not in anker_je_reise:
                anker_je_reise[reise.id] = await anker_fuer_ziel(reise.destination)
                print(f"\n  Reise {reise.id} „{reise.title}“ — Ziel: {reise.destination}")
                print(f"  Anker: {anker_je_reise[reise.id] or 'nicht auflösbar'}")

            treffer = await geocode_place(
                name=ort.name,
                address=ort.address,
                anker=anker_je_reise[reise.id],
                land=None,
            )
            if treffer:
                gefunden += 1
                abstand = treffer.get("abstand_km")
                print(
                    f"    ✓ {ort.name[:38]:40s} {treffer['lat']:.4f},{treffer['lon']:.4f}"
                    f"  {f'{abstand:5.1f} km' if abstand is not None else '   —   '}"
                    f"  [{treffer['quelle']}]  {treffer['name'][:38]}"
                )
                if schreiben:
                    ort.latitude = treffer["lat"]
                    ort.longitude = treffer["lon"]
            else:
                # Kein Treffer bleibt kein Treffer. Nichts eintragen.
                print(f"    ✗ {ort.name[:38]:40s} nicht gefunden — bleibt ohne Position")

        if schreiben:
            await db.commit()
            print(f"\nGeschrieben: {gefunden} von {len(paare)}.")
        else:
            print(f"\nGefunden: {gefunden} von {len(paare)}. Mit --schreiben übernehmen.")
        return len(paare) - gefunden


if __name__ == "__main__":
    zerleger = argparse.ArgumentParser(description=__doc__)
    zerleger.add_argument("--reise", type=int, default=None, help="nur diese Reise-ID")
    zerleger.add_argument("--schreiben", action="store_true", help="Ergebnisse wirklich speichern")
    argumente = zerleger.parse_args()
    sys.exit(0 if asyncio.run(nachtragen(argumente.reise, argumente.schreiben)) == 0 else 0)
