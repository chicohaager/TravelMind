# 🔧 Manuelle Backend-Start-Anleitung

## Das Problem

Die automatischen Starts haben nicht funktioniert. Hier ist die manuelle Lösung:

## ✅ Schritt-für-Schritt-Anleitung

### 1. Alte Prozesse stoppen

Öffnen Sie ein **neues Terminal** und führen Sie aus:

```bash
# Alle Python-Prozesse auf Port 8000 und 8001 finden
ps aux | grep -E "(uvicorn|python.*main)" | grep -v grep

# Stoppen Sie jeden Prozess (ersetzen Sie <PID> mit der Prozess-ID):
kill <PID>

# Oder alle auf einmal:
pkill -f "uvicorn"
pkill -f "python.*main.py"
```

Warten Sie 5 Sekunden.

### 2. Backend starten

```bash
cd /home/holgi/dev/TravelMind
source venv/bin/activate
cd backend
python main.py
```

**Sie sollten sehen:**
```
🌍 TravelMind Backend starting...
✓ Added ai_provider column to users table
✓ Added encrypted_api_key column to users table
✅ Database initialized
✅ Backend ready!
INFO:     Uvicorn running on http://0.0.0.0:8001
```

Wenn Sie stattdessen einen Fehler sehen, **lassen Sie das Terminal offen** und teilen Sie mir den Fehler mit!

### 3. Frontend prüfen/neu starten (in neuem Terminal)

```bash
cd /home/holgi/dev/TravelMind/frontend
npm run dev
```

### 4. Registrierung testen

1. Öffnen Sie: http://localhost:5173/register
2. Erstellen Sie einen neuen Account
3. Nach erfolgreicher Registrierung: Gehen Sie zu **Settings**
4. Konfigurieren Sie Ihren AI-Provider

## 🔍 Fehlerbehebung

### Port schon belegt

```bash
# Port 8001 freigeben
lsof -ti:8001 | xargs kill -9

# Port 8000 freigeben
lsof -ti:8000 | xargs kill -9
```

### Datenbank-Fehler

```bash
# Prüfen
ls -la /home/holgi/dev/TravelMind/data/travelmind.db

# Neu erstellen falls nötig
rm /home/holgi/dev/TravelMind/data/travelmind.db
touch /home/holgi/dev/TravelMind/data/travelmind.db
```

### Frontend verbindet nicht

Prüfen Sie: `frontend/.env` sollte enthalten:
```
VITE_PROXY_TARGET=http://localhost:8001
```

Falls geändert, Frontend neu starten!

## ℹ️ Was passiert gerade

Ihr **Frontend verbindet vermutlich noch zum alten Backend** auf Port 8000, das nicht mehr funktioniert. Deshalb hängt die Registrierung.

**Lösung:** Backend **manuell** auf Port 8001 starten (siehe oben) und dann Frontend **neu starten**.
