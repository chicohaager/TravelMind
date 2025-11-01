# 🚀 TravelMind - Quick Start Guide

## ✅ Was wurde geändert?

Ihr TravelMind wurde erfolgreich umgestellt auf **user-spezifische AI-Provider-Konfiguration**:

- ✅ Jeder User kann seinen eigenen AI-Provider wählen (Claude, OpenAI, Gemini)
- ✅ API-Keys werden verschlüsselt gespeichert
- ✅ Kein hardcodierter CLAUDE_API_KEY mehr nötig
- ✅ Backend läuft jetzt auf Port **8001** (statt 8000)

## 📋 Was Sie jetzt tun müssen:

### 1. Altes Backend stoppen

Das alte Backend läuft noch auf Port 8000 als root-Prozess. Sie müssen es manuell stoppen:

```bash
# Finden Sie die Prozess-ID
ps aux | grep "[u]vicorn main:app"

# Stoppen Sie den Prozess (als root)
sudo kill -9 <PROZESS_ID>
```

### 2. Neues Backend starten

```bash
cd /home/der Betreiber/dev/TravelMind
./START_BACKEND.sh
```

**Oder manuell:**

```bash
cd /home/der Betreiber/dev/TravelMind
source venv/bin/activate
cd backend
python main.py
```

### 3. Frontend neu starten (falls nötig)

Das Frontend ist bereits auf Port 8001 konfiguriert. Falls es nicht läuft:

```bash
cd /home/der Betreiber/dev/TravelMind/frontend
npm run dev
```

### 4. AI-Provider konfigurieren

1. Öffnen Sie http://localhost:5173
2. Melden Sie sich an
3. Gehen Sie zu **Einstellungen** (Settings)
4. Im Bereich **AI-Konfiguration**:
   - Wählen Sie Ihren AI-Provider (Claude, OpenAI, oder Gemini)
   - Geben Sie Ihren API-Key ein
   - Klicken Sie auf **Validieren** zum Testen
   - Klicken Sie auf **Speichern**

## 🔑 API-Keys erhalten

- **Claude**: https://console.anthropic.com/
- **OpenAI**: https://platform.openai.com/
- **Gemini**: https://makersuite.google.com/

## 📊 Ports

- **Backend**: http://localhost:8001
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8001/docs

## ⚠️ Wichtig: Neue Datenbank

Da die alte Datenbank root gehörte, wurde eine neue erstellt. Ihre Daten aus der alten DB befinden sich in:

```
/home/der Betreiber/dev/TravelMind/data/travelmind.db.backup
```

## 🐛 Bei Problemen

### Backend startet nicht
- Prüfen Sie, ob Port 8001 frei ist: `netstat -tlnp | grep 8001`
- Prüfen Sie Berechtigungen: `ls -la /home/der Betreiber/dev/TravelMind/data/`

### Frontend verbindet nicht zum Backend
- Prüfen Sie `frontend/.env`: `VITE_PROXY_TARGET=http://localhost:8001`
- Frontend neu starten

### Login funktioniert nicht
- Legen Sie einen neuen Account an (alte DB wurde durch neue ersetzt)
- Backend-Logs prüfen für Fehler

## 📝 Dateien die geändert wurden

- `backend/models/user.py` - AI Provider Settings
- `backend/utils/encryption.py` - API Key Encryption
- `backend/services/ai_service.py` - Multi-Provider Support
- `backend/routes/ai.py` - User-specific AI
- `backend/routes/user_settings.py` - Settings API
- `frontend/src/pages/Settings.jsx` - Settings UI
- `.env` - Port 8001, kein CLAUDE_API_KEY mehr
- `frontend/.env` - Proxy auf 8001

## ✨ Fertig!

Sobald das Backend läuft und Sie Ihren API-Key konfiguriert haben, können Sie alle AI-Features nutzen!
