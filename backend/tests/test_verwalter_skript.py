"""
Wächter für `scripts/verwalter.py` — den einzigen Weg, das erste
Verwalterrecht zu vergeben.

Am 2026-08-26 in der Produktionsdatenbank gemessen: zwei Konten, beide
`is_superuser = false`. Die Benutzerverwaltung war vollständig gebaut
(21 Endpunkte in `routes/admin.py`, 723 Zeilen `AdminPanel.jsx`) und für
niemanden erreichbar — das Recht vergibt nur die Verwaltung, und in die
Verwaltung kommt nur, wer das Recht hat.

Die beiden Eigenschaften, an denen das hängt und die deshalb hier festgehalten
werden: `setzen` funktioniert ohne vorhandenen Verwalter, und `entziehen`
weigert sich beim letzten. Ohne die zweite wäre man mit einem Aufruf wieder in
derselben Sackgasse.
"""

import os

import pytest
from models.user import User
from sqlalchemy import select

from scripts import verwalter as skript


@pytest.fixture
def sitzungsfabrik(monkeypatch, db_session):
    """Das Skript legt seine eigene Sitzung an. Im Test bekommt es die des
    Tests untergeschoben — sonst redet es mit einer anderen Datenbank als die
    Zusicherungen unten, und der Test prüfte seinen eigenen Aufbau."""

    class _Fabrik:
        def __call__(self):
            return self

        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *_):
            return False

    monkeypatch.setattr(skript, "AsyncSessionLocal", _Fabrik())


async def _anlegen(db, benutzername, verwalter=False):
    u = User(
        username=benutzername,
        email=f"{benutzername}@example.invalid",
        hashed_password=User.hash_password("Ein-Passwort-123"),
        is_active=True,
        is_superuser=verwalter,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.mark.asyncio
async def test_setzen_funktioniert_ohne_vorhandenen_verwalter(sitzungsfabrik, db_session, capsys):
    """Genau der Fall aus der Produktion: niemand ist Verwalter."""
    await _anlegen(db_session, "erste")
    assert await skript.setzen("erste") == 0
    u = (await db_session.execute(select(User).where(User.username == "erste"))).scalar_one()
    assert u.is_superuser is True
    assert "jetzt Verwalter" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_setzen_ist_wiederholbar(sitzungsfabrik, db_session, capsys):
    await _anlegen(db_session, "zweite", verwalter=True)
    assert await skript.setzen("zweite") == 0
    assert "bereits Verwalter" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_der_letzte_verwalter_kann_sich_nicht_selbst_aussperren(sitzungsfabrik, db_session):
    await _anlegen(db_session, "einzige", verwalter=True)
    with pytest.raises(SystemExit) as fehler:
        await skript.entziehen("einzige")
    assert "EINZIGE" in str(fehler.value)
    u = (await db_session.execute(select(User).where(User.username == "einzige"))).scalar_one()
    assert u.is_superuser is True  # nichts geändert


@pytest.mark.asyncio
async def test_entziehen_geht_solange_ein_zweiter_bleibt(sitzungsfabrik, db_session, capsys):
    """Gegenkontrolle: die Sperre oben darf nicht jedes Entziehen verbieten."""
    await _anlegen(db_session, "eine", verwalter=True)
    await _anlegen(db_session, "andere", verwalter=True)
    assert await skript.entziehen("eine") == 0
    u = (await db_session.execute(select(User).where(User.username == "eine"))).scalar_one()
    assert u.is_superuser is False
    assert "1 verbleiben" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_unbekannter_benutzer_nennt_die_vorhandenen(sitzungsfabrik, db_session):
    """Auf dieser Instanz gibt es `holgi` UND `Holgi`. Ein Vertipper darf
    nicht stillschweigend nichts tun."""
    await _anlegen(db_session, "holgi")
    with pytest.raises(SystemExit) as fehler:
        await skript.setzen("Holgi")
    assert "holgi" in str(fehler.value)


@pytest.mark.asyncio
async def test_zeigen_warnt_wenn_niemand_verwalter_ist(sitzungsfabrik, db_session, capsys):
    await _anlegen(db_session, "niemand")
    assert await skript.zeigen() == 0
    ausgabe = capsys.readouterr().out
    assert "0 Verwalter" in ausgabe
    assert "erreichbar" in ausgabe  # der Warnhinweis, nicht nur die Zahl


# ── Der Lauf in einem FRISCHEN Interpreter ──────────────────────────────────
#
# Die Tests oben liefen alle grün, während das Skript in der Produktion beim
# ersten Aufruf mit
#
#   InvalidRequestError: When initializing mapper Mapper[Trip(trips)],
#   expression 'Route' failed to locate a name ('Route')
#
# abstürzte — und zwar bei `select(User)`, einer Abfrage, die `Trip` nicht
# einmal anfasst. SQLAlchemy löst Beziehungen über Klassennamen auf, und
# `conftest.py` importiert alle Modelle: die TESTWELT hatte die Registrierung,
# die Produktion nicht. Genau die Eigenschaft, an der es zerbrach, war in den
# Fixtures wegvereinfacht.
#
# Dieser Test startet deshalb einen eigenen Prozess. Nur dort ist die
# Registrierung so leer wie im Container.


def test_das_skript_laeuft_in_einem_frischen_interpreter(tmp_path):
    import subprocess
    import sys as _sys
    from pathlib import Path

    backend = Path(__file__).resolve().parent.parent
    datenbank = tmp_path / "verwalter.db"

    umgebung = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{datenbank}",
        "PYTHONPATH": str(backend),
    }
    lauf = subprocess.run(
        [_sys.executable, "scripts/verwalter.py", "zeigen"],
        cwd=backend,
        env=umgebung,
        capture_output=True,
        text=True,
        timeout=60,
    )

    # Erwartet wird KEIN Erfolg der Abfrage — die Datenbank ist leer und hat
    # nicht einmal Tabellen. Erwartet wird, dass die MAPPER sich auflösen
    # lassen: der Registrierungsfehler darf nicht auftreten.
    gesamt = lauf.stdout + lauf.stderr
    assert "failed to locate a name" not in gesamt, gesamt
    assert "InvalidRequestError" not in gesamt, gesamt
