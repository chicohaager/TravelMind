# 🚀 Einfacher Backend-Start

## Problem

Das Backend konnte nicht starten wegen einer falschen `DATABASE_URL` Variable in Ihrer Shell-Umgebung.

## Lösung

### 1. Backend stoppen (falls läuft)

Drücken Sie in allen Terminals, wo das Backend läuft, **Ctrl+C** um es zu stoppen.

Oder öffnen Sie ein **neues Terminal** und führen aus:

```bash
# Alle laufenden Backend-Prozesse stoppen
pkill -f "uvicorn.*8001"
pkill -f "python.*main.py"
```

### 2. Backend mit dem neuen Skript starten

Öffnen Sie ein **NEUES Terminal-Fenster** (wichtig!) und führen Sie aus:

```bash
cd /home/der Betreiber/dev/TravelMind
./START_BACKEND_CLEAN.sh
```

Sie sollten sehen:

```
🌍 Starting TravelMind Backend (Clean Environment)...

🔍 Checking environment...
  ✓ Cleared DATABASE_URL from environment
  ✓ Virtual environment found
  ✓ Virtual environment activated

🚀 Starting backend on port 8001...
   Press Ctrl+C to stop

🌍 TravelMind Backend starting...
  ✓ Added ai_provider column to users table
  ✓ Added encrypted_api_key column to users table
✅ Database initialized
✅ Backend ready!
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

### 3. Registrierung testen

Öffnen Sie im Browser:
```
http://localhost:5173/register
```

Erstellen Sie einen neuen Account.

## Was wurde gefixt?

1. ✅ DATABASE_URL wird jetzt korrekt aus `.env` geladen
2. ✅ Startup-Skript löscht fehlerhafte Umgebungsvariablen
3. ✅ Relative Pfade funktionieren jetzt korrekt

## Falls es immer noch nicht funktioniert

Bitte senden Sie mir die **komplette Ausgabe** vom Terminal, nachdem Sie `./START_BACKEND_CLEAN.sh` ausgeführt haben.
