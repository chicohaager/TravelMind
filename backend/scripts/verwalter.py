#!/usr/bin/env python3
"""Verwalterrecht (`is_superuser`) setzen, entziehen und anzeigen.

Warum es dieses Skript gibt: die Benutzerverwaltung war am 2026-08-26
vollstaendig gebaut — Endpunkte, Oberflaeche, Rechtepruefung — und trotzdem
fuer niemanden erreichbar. In der Datenbank stand bei beiden Konten
`is_superuser = false`:

    id | username | is_active | is_superuser
     1 | holgi    | t         | f
     2 | Holgi    | t         | f

Das Recht kann man nur ueber die Verwaltung vergeben, und in die Verwaltung
kommt nur, wer das Recht hat. Ein Henne-Ei-Problem, das ohne einen Weg von
aussen nicht aufloesbar ist — dieses Skript ist dieser Weg.

Absichtlich KEIN Selbstheilungsmechanismus in der Anwendung ("wenn kein
Verwalter existiert, mache den ersten Benutzer zum Verwalter"). So etwas
greift auch dann, wenn der letzte Verwalter gerade absichtlich entzogen
wurde, und dann vergibt das System Rechte von allein.

Aufrufen im laufenden Container:

    docker exec travelmind-backend python3 scripts/verwalter.py zeigen
    docker exec travelmind-backend python3 scripts/verwalter.py setzen <benutzername>
    docker exec travelmind-backend python3 scripts/verwalter.py entziehen <benutzername>

`entziehen` weigert sich, den letzten Verwalter zu entfernen — sonst waere man
wieder genau da, wo dieses Skript herkommt.
"""

import asyncio
import sys

from models.database import AsyncSessionLocal
from models.user import User
from sqlalchemy import func, select


async def _benutzer(db, benutzername: str) -> User:
    # Gross-/Kleinschreibung ist hier eine Stolperfalle: auf dieser Instanz
    # gibt es `holgi` UND `Holgi` als zwei verschiedene Konten. Deshalb wird
    # exakt verglichen und bei einem Fehlgriff die Liste ausgegeben.
    treffer = (await db.execute(select(User).where(User.username == benutzername))).scalar_one_or_none()
    if treffer is None:
        vorhanden = (await db.execute(select(User.username).order_by(User.id))).scalars().all()
        raise SystemExit(f"✗ Kein Benutzer '{benutzername}'. Vorhanden: {', '.join(vorhanden) or '(keiner)'}")
    return treffer


async def zeigen() -> int:
    async with AsyncSessionLocal() as db:
        benutzer = (await db.execute(select(User).order_by(User.id))).scalars().all()
        if not benutzer:
            print("(keine Benutzer)")
            return 1
        print(f"{'id':>3}  {'benutzername':<20} {'aktiv':<6} verwalter")
        for b in benutzer:
            print(f"{b.id:>3}  {b.username:<20} {'ja' if b.is_active else 'nein':<6} {'JA' if b.is_superuser else '—'}")
        anzahl = sum(1 for b in benutzer if b.is_superuser)
        print(f"\n{anzahl} Verwalter von {len(benutzer)} Konten.")
        if anzahl == 0:
            print("⚠️  Ohne Verwalter ist /admin fuer niemanden erreichbar.")
        return 0


async def setzen(benutzername: str) -> int:
    async with AsyncSessionLocal() as db:
        b = await _benutzer(db, benutzername)
        if b.is_superuser:
            print(f"'{b.username}' (id {b.id}) ist bereits Verwalter — nichts geaendert.")
            return 0
        b.is_superuser = True
        await db.commit()
        print(f"✓ '{b.username}' (id {b.id}) ist jetzt Verwalter.")
        return 0


async def entziehen(benutzername: str) -> int:
    async with AsyncSessionLocal() as db:
        b = await _benutzer(db, benutzername)
        if not b.is_superuser:
            print(f"'{b.username}' (id {b.id}) ist kein Verwalter — nichts geaendert.")
            return 0
        anzahl = (await db.execute(select(func.count()).select_from(User).where(User.is_superuser.is_(True)))).scalar()
        if anzahl <= 1:
            raise SystemExit(
                f"✗ '{b.username}' ist der EINZIGE Verwalter. Erst einen zweiten setzen, "
                f"sonst kommt niemand mehr in die Verwaltung."
            )
        b.is_superuser = False
        await db.commit()
        print(f"✓ '{b.username}' (id {b.id}) ist kein Verwalter mehr ({anzahl - 1} verbleiben).")
        return 0


def main() -> int:
    befehle = {"zeigen": (zeigen, 0), "setzen": (setzen, 1), "entziehen": (entziehen, 1)}
    if len(sys.argv) < 2 or sys.argv[1] not in befehle:
        print(__doc__)
        return 2
    funktion, argumente = befehle[sys.argv[1]]
    if len(sys.argv) - 2 != argumente:
        raise SystemExit(f"✗ '{sys.argv[1]}' erwartet {argumente} Argument(e).")
    return asyncio.run(funktion(*sys.argv[2:]))


if __name__ == "__main__":
    sys.exit(main())
