"""
Passwort-Regeln.

Ausrichtung: NIST SP 800-63B. Das heisst ausdruecklich **keine**
Komplexitaetsregeln ("mindestens ein Sonderzeichen") — die erzeugen
vorhersagbare Muster wie "Passwort1!" und schaden mehr, als sie nutzen.
Wirksam sind zwei Dinge: ausreichende Laenge und der Abgleich mit bekannten
Leaks.

Der Leak-Abgleich nutzt die k-Anonymitaets-Schnittstelle von
Have I Been Pwned: gesendet werden die ersten FUENF Zeichen des SHA-1-Hashes,
zurueck kommen alle Suffixe zu diesem Praefix. Das Passwort selbst — und auch
sein vollstaendiger Hash — verlaesst den Server nie.

Stand vor dem 2026-08-25: nur `Field(min_length=8)`. Kein Leak-Abgleich, keine
gemeinsame Stelle, an der die Regeln stehen.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Callable, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Mindestlaenge. 10 statt der bisherigen 8 — eine milde Anhebung, die
# bestehende Anmeldungen nicht beruehrt (geprueft wird nur beim Setzen).
MINDESTLAENGE = int(os.getenv("PASSWORD_MIN_LENGTH", "10"))
HOECHSTLAENGE = int(os.getenv("PASSWORD_MAX_LENGTH", "128"))

# Wie streng der Leak-Abgleich ist:
#   "required"    — ist die Abfrage nicht moeglich, wird das Passwort abgelehnt.
#   "best-effort" — ist sie nicht moeglich, wird eine WARNUNG protokolliert und
#                   das Passwort angenommen (Standard: die Anwendung soll auch
#                   ohne Internetzugang benutzbar bleiben).
#   "off"         — kein Abgleich.
#
# "best-effort" ist bewusst kein stiller Rueckfall: das Scheitern steht im
# Protokoll, mit Grund. Ein Fehler, der niemandem auffaellt, waere schlimmer
# als gar keine Pruefung.
LEAK_ABGLEICH = os.getenv("PASSWORD_BREACH_CHECK", "best-effort").lower()

HIBP_URL = "https://api.pwnedpasswords.com/range/{praefix}"
HIBP_TIMEOUT = float(os.getenv("PASSWORD_BREACH_TIMEOUT", "3.0"))


@dataclass(frozen=True)
class Pruefergebnis:
    """Ergebnis einer Passwortpruefung."""

    gueltig: bool
    grund: Optional[str] = None
    #: Wie oft das Passwort in bekannten Leaks auftaucht (None = nicht geprüft).
    leak_treffer: Optional[int] = None


def _sha1_hex(passwort: str) -> str:
    # SHA-1 ist hier KEINE Sicherheitsentscheidung: die Schnittstelle von
    # Have I Been Pwned ist so definiert. Gespeichert wird nichts davon —
    # das Passwort selbst liegt mit bcrypt in der Datenbank.
    return hashlib.sha1(passwort.encode("utf-8")).hexdigest().upper()  # nosec B324


async def _hibp_abfragen(praefix: str) -> str:
    """Die rohe Antwort der Range-Schnittstelle holen."""
    async with httpx.AsyncClient(timeout=HIBP_TIMEOUT) as klient:
        antwort = await klient.get(
            HIBP_URL.format(praefix=praefix),
            headers={"Add-Padding": "true", "User-Agent": "TravelMind"},
        )
        antwort.raise_for_status()
        return antwort.text


async def leak_treffer_zaehlen(
    passwort: str,
    abfrage: Callable[[str], "object"] = _hibp_abfragen,
) -> Optional[int]:
    """
    Wie oft taucht dieses Passwort in bekannten Leaks auf?

    Rueckgabe ``None`` heisst: nicht feststellbar (kein Netz, Zeitüberschreitung,
    Fehler bei der Gegenstelle) — NICHT "nicht betroffen".

    ``abfrage`` ist einspeisbar, damit die Tests ohne Netz auskommen.
    """
    hash_hex = _sha1_hex(passwort)
    praefix, suffix = hash_hex[:5], hash_hex[5:]
    try:
        text = await abfrage(praefix)
    except Exception as fehler:
        logger.warning(
            "Leak-Abgleich nicht moeglich",
            grund=str(fehler),
            hinweis="Das Passwort wurde NICHT gegen bekannte Leaks geprueft.",
        )
        return None

    for zeile in str(text).splitlines():
        teil, _, anzahl = zeile.partition(":")
        if teil.strip().upper() == suffix:
            try:
                return int(anzahl.strip())
            except ValueError:
                return 1
    return 0


async def passwort_pruefen(
    passwort: str,
    abfrage: Callable[[str], "object"] = _hibp_abfragen,
    leak_abgleich: Optional[str] = None,
) -> Pruefergebnis:
    """
    Ein Passwort gegen die Regeln pruefen.

    Reihenfolge: erst die Laenge (kostet nichts), dann der Leak-Abgleich.
    """
    modus = (leak_abgleich or LEAK_ABGLEICH).lower()

    if len(passwort) < MINDESTLAENGE:
        return Pruefergebnis(False, f"Das Passwort muss mindestens {MINDESTLAENGE} Zeichen lang sein.")
    if len(passwort) > HOECHSTLAENGE:
        return Pruefergebnis(False, f"Das Passwort darf hoechstens {HOECHSTLAENGE} Zeichen lang sein.")

    if modus == "off":
        return Pruefergebnis(True)

    treffer = await leak_treffer_zaehlen(passwort, abfrage=abfrage)

    if treffer is None:
        if modus == "required":
            return Pruefergebnis(
                False,
                "Das Passwort konnte nicht gegen bekannte Datenlecks geprueft werden. Bitte spaeter erneut versuchen.",
            )
        return Pruefergebnis(True, leak_treffer=None)

    if treffer > 0:
        return Pruefergebnis(
            False,
            (
                "Dieses Passwort taucht in bekannten Datenlecks auf "
                f"({treffer:,} Mal) und ist damit unsicher. Bitte ein anderes waehlen."
            ).replace(",", "."),
            leak_treffer=treffer,
        )

    return Pruefergebnis(True, leak_treffer=0)
