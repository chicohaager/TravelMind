# Migration Guide: AI Settings Update

## Problem
Nach der Umstellung auf user-spezifische AI-Provider-Konfiguration funktioniert der Login nicht mehr (Spinner dreht sich endlos).

## Ursache
Die Datenbank-Tabelle `users` hat noch nicht die neuen Spalten `ai_provider` und `encrypted_api_key`.

## Lösung

### Option 1: Automatische Migration (Empfohlen)

Das Backend wurde aktualisiert, um Migrationen automatisch beim Start durchzuführen.

**Einfach das Backend neu starten:**

```bash
# Terminal 1: Backend neu starten
cd backend
python main.py
```

Die Migration wird automatisch beim Start ausgeführt. Sie sehen dann:
```
✓ Added ai_provider column to users table
✓ Added encrypted_api_key column to users table
✅ Database initialized
```

### Option 2: Manuelle Migration

Falls das Backend als root läuft und Sie es nicht neu starten können:

```bash
# 1. Backend stoppen
sudo pkill -f "uvicorn main:app"

# 2. Migration ausführen
python3 migrate_user_ai_settings.py

# 3. Backend neu starten
cd backend
python main.py
```

## Überprüfung

Nach dem Neustart sollte der Login wieder funktionieren.

### Test:
1. Öffne http://localhost:5173/login
2. Melde dich mit deinem Account an
3. Gehe zu http://localhost:5173/settings
4. Du solltest den neuen "AI-Konfiguration" Bereich sehen

## Nächste Schritte

Nach erfolgreichem Login:

1. **Gehe zu Einstellungen** (`/settings`)
2. **Wähle deinen AI-Provider** (Claude, OpenAI, oder Gemini)
3. **Gib deinen API-Key ein**
4. **Klicke auf "Validieren"** zum Testen
5. **Klicke auf "Speichern"**

Dein API-Key wird verschlüsselt gespeichert und nur für deine Anfragen verwendet.

## Support

Falls weiterhin Probleme auftreten:
- Überprüfe Backend-Logs: `cd backend && python main.py`
- Überprüfe Datenbank-Schema: `sqlite3 data/travelmind.db ".schema users"`
- Die Spalten `ai_provider` und `encrypted_api_key` sollten vorhanden sein
