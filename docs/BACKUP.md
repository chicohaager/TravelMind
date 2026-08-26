# Sicherung und Wiederherstellung

**Neu geschrieben am 2026-08-25.** Die vorherige Fassung beschrieb einen Weg,
der in dieser Installation nie funktioniert hat — siehe *Was vorher nicht
stimmte* am Ende.

---

## Was gesichert wird

| Was | Warum es zählt |
|---|---|
| **Datenbank** | Reisen, Tagebuch, Orte, Bildunterschriften, GPS, Konten |
| **Fotos** (`uploads/`) | Die Bilder selbst — **sie lassen sich nicht neu erzeugen** |

Die Fotos sind kein Zusatz, sondern der wichtigere Teil. Eine Datenbank kann
man im Zweifel neu aufbauen; ein verlorenes Reisefoto ist weg.

---

## Wie es läuft

Ein eigener Container im Verbund (`travelmind-backup`), täglich um 03:00:

```text
1. pg_dump -Fc              Datenbank in das eigene Format
2. pg_restore --list        PRÜFUNG: ein Dump, den pg_restore nicht lesen
                            kann, ist kein Dump
3. tar czf uploads          Fotos, mit Vergleich der Dateizahl
4. sha256                   Manifest neben die beiden Dateien
5. Aufräumen                die 14 jüngsten Stände bleiben
6. Restore-Probe            siehe unten — läuft nach JEDER Sicherung
```

Er läuft im Compose-Netz und benutzt den `pg_dump` **desselben Image-Stands**
wie der Server. Damit können die Versionen nicht auseinanderlaufen — der
häufigste Grund, warum eine Sicherung eines Tages nicht mehr geht.

Bewusst **kein** Docker-Socket und **kein** systemd: beides braucht Root auf
dem Host. Der Container fährt mit dem Verbund hoch und runter und ist in
`docker ps` sichtbar. Ein ausgefallener Zeitgeber fällt damit auf, statt still
zu verschwinden.

### Einstellungen

In `deploy-params.conf` (keine Geheimnisse):

| Variable | Standard | Bedeutung |
|---|---|---|
| `BACKUP_UHRZEIT` | `03:00` | Uhrzeit des täglichen Laufs (lokale Zeit) |
| `BACKUP_KEEP` | `14` | Wie viele Stände bleiben |
| `BACKUP_BEIM_START` | `nein` | `ja` = ein Lauf sofort beim Hochfahren |

---

## Die Restore-Probe

**Eine Sicherung ist erst dann eine, wenn sie sich zurückspielen lässt.**
Alles andere ist eine Datei mit einem beruhigenden Namen.

Deshalb läuft nach **jeder** Sicherung `probe.sh`:

1. Prüfsummen gegen das Manifest.
2. Der Dump wird in eine **Wegwerf-Datenbank** zurückgespielt
   (`pg_restore --exit-on-error` — ohne das läuft pg_restore über Fehler
   hinweg und meldet am Ende trotzdem Erfolg).
3. Die Zeilen werden gezählt und mit der **laufenden** Datenbank verglichen.
4. Das Foto-Archiv wird wirklich **ausgepackt** — ein Inhaltsverzeichnis kann
   vollständig sein, während die Daten dahinter beschädigt sind.
5. Die Wegwerf-Datenbank wird entfernt, auch bei Abbruch.

Dazu eine Positivkontrolle: Enthält die zurückgespielte Datenbank keinen
einzigen Nutzer, bricht die Probe ab — zwei leere Datenbanken wären sonst
„gleich" und das Ergebnis wertlos.

Ergebnis eines echten Laufs:

```text
Pruefsummen stimmen
Wegwerf-Datenbank travelmind_probe_55 anlegen und zurueckspielen …
zurueckgespielt
    users                2 = 2      ok
    trips                5 = 5      ok
    places              18 = 18     ok
    diary_entries        2 = 2      ok
    media                7 = 7      ok
    expenses             0 = 0      ok
    uploads             45 entpackt, 45 auf Platte
PROBE BESTANDEN — dieser Stand laesst sich zurueckspielen.
```

### Von Hand anstoßen

```bash
docker exec travelmind-backup /skripte/sichern.sh
docker exec travelmind-backup /skripte/probe.sh
docker logs --tail 40 travelmind-backup
```

---

## Wiederherstellen

```bash
# Welche Stände gibt es?
ls -lt /DATA/AppData/travelmind/backups/

# Prüfsummen zuerst — nie einen Stand einspielen, den man nicht geprüft hat
cd /DATA/AppData/travelmind/backups
sha256sum -c travelmind-<stempel>.manifest

# Datenbank (ACHTUNG: --clean verwirft den aktuellen Inhalt)
docker exec -i travelmind-db pg_restore -U travelmind -d travelmind \
  --clean --if-exists --exit-on-error < travelmind-db-<stempel>.dump

# Fotos
tar xzf travelmind-uploads-<stempel>.tar.gz -C /DATA/AppData/travelmind
chown -R 1001:1001 /DATA/AppData/travelmind/uploads
```

Die Zeile mit `chown` ist nicht optional: die Container laufen unter uid 1001,
und ohne sie startet das Backend mit `PermissionError: 'uploads/trips'`.

---

## Der Wächter

Sichern allein hätte den Fall vom Juni nicht verhindert: Die Anwendung war
zwei Monate abgeschaltet, und es ist niemandem aufgefallen. Deshalb läuft
neben der Sicherung ein zweiter Container, `travelmind-waechter`:

- fragt Oberfläche **und** API im Minutentakt, durch dieselbe Kette wie ein
  Nutzer,
- prüft den **Inhalt**, nicht den Statuscode — der SPA-Rückfall beantwortet
  jeden Pfad mit 200, und die API kann 200 liefern, während die Datenbank
  weg ist,
- meldet nach drei Fehlversuchen über Pushover, mit Priorität 1 (an
  Ruhezeiten vorbei), und schickt bei Rückkehr eine Entwarnung.

`PUSHOVER_TOKEN` und `PUSHOVER_USER` stehen in `.env`. Fehlen sie, meldet der
Wächter nur ins Protokoll — und sagt das auch.

---

## Die 3-2-1-Regel

Was hier läuft, deckt **eine** Kopie auf **einem** Gerät ab. Das schützt gegen
gelöschte Daten und misslungene Migrationen, nicht gegen Blitzschlag,
Diebstahl oder ein defektes Speichergerät.

Für den Rest gehört das Verzeichnis `backups/` regelmäßig auf ein zweites
Medium oder an einen anderen Ort — die Sicherung auf demselben Gerät wie die
Daten ist genau die Kopie, die mit ihnen zusammen verlorengeht.

---

## Was vorher nicht stimmte

Für die Nachwelt, weil der Fehler lehrreich ist:

- `backend/scripts/backup_database.py` liegt seit jeher im Repository und war
  dokumentiert. Es ruft `pg_dump` im Backend-Container auf — **dort gibt es
  keins.** Gemessen am 2026-08-25:
  `ERROR - pg_dump not found. Please install PostgreSQL client tools.`
- Nachinstallieren wäre die naheliegende und die falsche Antwort gewesen:
  Debian bookworm liefert `pg_dump` 15, der Server läuft auf 16, und `pg_dump`
  verweigert den Dienst gegen eine neuere Serverversion.
- Es gab keinen Zeitgeber. Im Sicherungsverzeichnis lag genau **eine** Datei,
  vom 24. Juni. Die **104 MB Fotos hatten überhaupt keine Sicherung.**
- Niemand hätte das bemerkt, weil niemand je versucht hat, etwas
  zurückzuholen.
