"""
Wächter gegen eine Version, die an mehreren Stellen einzeln gepflegt wird.

Dies ist der EINZIGE Versionswächter. Ein zweiter lag kurzzeitig im Frontend
(`src/test/version.test.js`) und suchte `version=` wörtlich in `main.py` —
nach dem Zentralisieren in `version.py` fand er dort nichts mehr und meldete
rot, obwohl alles stimmte. Zwei Wächter für dieselbe Eigenschaft können
einander widersprechen; dann glaubt man dem bequemeren. Also einer, und der
prüft beide Seiten.

Am 2026-08-25 stand sie im Backend an FÜNF Stellen im Quelltext. Nach dem
Sprung auf 1.1.0 meldete `/api/health` weiter 1.0.0 — ausgerechnet der Wert,
an dem die Überwachung hängt und den ein Nutzer in einem Fehlerbericht nennt.

Eine Zahl an fünf Stellen ist keine Versionierung, sondern fünf Zahlen, die
zufällig mal gleich waren. Diese Prüfung sorgt dafür, dass keine sechste
dazukommt — und dass die Auskunft, die nach außen geht, dieselbe ist wie die
im Code.
"""

import re
from pathlib import Path

import pytest
from httpx import AsyncClient
from version import VERSION

BACKEND = Path(__file__).parent.parent


def test_die_version_sieht_wie_eine_version_aus():
    assert re.fullmatch(r"\d+\.\d+\.\d+", VERSION), VERSION


def test_keine_zweite_versionsangabe_im_quelltext():
    """Sucht nach Versionsziffern in Zuweisungen — nicht nach der Zahl an
    sich, sonst schlägt jede Jahreszahl an."""
    muster = re.compile(
        r'["\']?(version|release)["\']?\s*[=:]\s*[f]?["\']([^"\']*\d+\.\d+\.\d+[^"\']*)["\']', re.IGNORECASE
    )
    treffer = []
    for datei in BACKEND.rglob("*.py"):
        rel = datei.relative_to(BACKEND).as_posix()
        if rel.startswith(("alembic/", "tests/", "venv/")) or rel == "version.py":
            continue
        for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), 1):
            if zeile.strip().startswith("#"):
                continue  # Begründungen dürfen Versionen nennen
            for m in muster.finditer(zeile):
                # Die Prometheus-Textfassung ist eine Formatversion, keine App-Version.
                if "0.0.4" in m.group(2):
                    continue
                treffer.append(f"{rel}:{nr}  {m.group(0).strip()}")
    assert treffer == [], "Versionsangabe außerhalb von version.py"


def test_positivkontrolle_der_scanner_erkennt_eine_zuweisung():
    muster = re.compile(
        r'["\']?(version|release)["\']?\s*[=:]\s*[f]?["\']([^"\']*\d+\.\d+\.\d+[^"\']*)["\']', re.IGNORECASE
    )
    assert muster.search('    version="1.0.0",')
    assert muster.search('        "version": "2.3.4",')
    # Gegenkontrolle: der Verweis auf die Konstante darf NICHT auslösen.
    assert not muster.search("    version=VERSION,")


@pytest.mark.asyncio
async def test_die_gesundheitsauskunft_nennt_dieselbe_version(client: AsyncClient):
    """Die Stelle, an der es zuletzt auseinanderlief: der Endpunkt, den die
    Überwachung abfragt."""
    # Achtung: `/health` (ohne Praefix) und `/api/health` sind NICHT dieselbe
    # Auskunft — gemessen am 2026-08-25 liefert `/health` nur
    # {status, service}, die ausfuehrliche Fassung steht unter `/api/health`.
    # Der Waechter (deploy/waechter/waechter.sh) fragt die ausfuehrliche ab.
    antwort = await client.get("/api/health")
    assert antwort.status_code == 200
    assert antwort.json()["version"] == VERSION

    kurz = await client.get("/health")
    assert kurz.status_code == 200
    assert kurz.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_das_openapi_schema_nennt_dieselbe_version(client: AsyncClient):
    from main import app

    assert app.openapi()["info"]["version"] == VERSION


def test_frontend_und_backend_tragen_dieselbe_version():
    import json

    paket = json.loads((BACKEND.parent / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert paket["version"] == VERSION

    seitenleiste = (BACKEND.parent / "frontend/src/components/layout/Sidebar.jsx").read_text(encoding="utf-8")
    m = re.search(r"TravelMind v(\d+\.\d+\.\d+)", seitenleiste)
    assert m and m.group(1) == VERSION, "Fußzeile der Seitenleiste weicht ab"


def test_der_changelog_kennt_diese_version():
    changelog = (BACKEND.parent / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{VERSION}]" in changelog
