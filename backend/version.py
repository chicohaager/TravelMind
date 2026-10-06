"""Die Version der Anwendung — an EINER Stelle.

Am 2026-08-25 stand sie im Backend an fuenf Stellen einzeln im Quelltext:
zweimal in `main.py`, in `utils/sentry.py`, als Vorgabewert von `APP_VERSION`
in `routes/health.py` und in der FastAPI-Beschreibung. Nach dem Sprung auf
1.1.0 meldete `/api/health` weiter 1.0.0 — der Wert, an dem die Ueberwachung
haengt.

Eine Zahl an fuenf Stellen ist keine Versionierung, sondern fuenf Zahlen, die
zufaellig mal gleich waren. `tests/test_version.py` haelt fest, dass keine
sechste dazukommt.

Die Umgebung darf sie ueberschreiben: beim Ausrollen kann der Commit-SHA
angehaengt werden, ohne dass ein neues Image noetig waere.
"""

import os

VERSION = os.getenv("APP_VERSION") or "1.1.0"
