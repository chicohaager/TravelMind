## TravelMind — wie man mit diesen Bauteilen baut

TravelMind ist eine Reise-App: Reisen planen, Orte sammeln, Tagebuch führen,
Ausgaben teilen, Tage auf einer Karte ordnen. Der eigentliche Inhalt sind
**Fotos und Karten** — die Oberfläche tritt bewusst zurück.

### 1. Alles gehört in `DesignSystemProvider`

Ohne ihn rendern die meisten Komponenten **gar nicht**: sie lesen
React-Query, Router, i18n und den Anmeldezustand aus dem Kontext. Ohne den
Provider fliegen `No QueryClient set`, `useNavigate() may be used only in the
context of a <Router>` oder `useAuth must be used within an AuthProvider`.

```jsx
import { DesignSystemProvider, PlaceCard } from 'travelmind-frontend'

<DesignSystemProvider>
  <PlaceCard place={{ id: 1, name: 'Torre de Belém', latitude: 38.69, longitude: -9.21 }} />
</DesignSystemProvider>
```

Die Reihenfolge im Provider ist nicht beliebig: QueryClient → i18n → Router →
Auth. `AuthProvider` braucht die beiden ersten.

### 2. Die Oberfläche ist auf DEUTSCH

Alle Beschriftungen kommen aus i18next; die Vorgabesprache ist Deutsch
(en/fr/es liegen bei). Schreibe **keine** eigenen Texte in Komponenten —
sie kämen in einer Sprache heraus und blieben in allen anderen stehen.
Eigene Überschriften und Fließtexte in der Sprache der Oberfläche verfassen.

### 3. Farben nur aus der Palette „Adria"

Zwei Familien, jeweils `50 … 950`, als Tailwind-Klassen verfügbar
(`bg-`, `text-`, `border-`, `ring-`, `from-`, `to-`, `via-`; dazu die
Varianten `hover:`, `focus:`, `active:`, `dark:`):

| Familie | Wofür | Anker |
|---|---|---|
| `primary` — Tiefsee-Teal | Flächen, Knöpfe, Links, alles Normale | `bg-primary-500` (#1F7A7D), Text `text-primary-600` |
| `secondary` — Signalorange | **sparsam**: was hervorsticht, wie eine Route auf der Karte | `bg-secondary-600`, Text `text-secondary-600` |
| `gray-*` | Fließtext, Rahmen, Hintergründe | Tailwind-Vorgabe |

🔴 **Weiße Schrift auf `bg-secondary-500` ist zu schwach** (3,82:1). Wo Weiß
auf der Signalfarbe steht, gehört `bg-secondary-600` hin (5,28:1).

Der Seitengrund ist `bg-primary-50` — ein leicht ins Teal gezogener
Neutralton, kein reines Grau. Keine Verläufe zwischen den beiden Akzenten;
wo ein Verlauf sein soll, bleibt er innerhalb einer Familie
(`from-primary-600 to-primary-400`).

### 4. Fertige Bausteinklassen

Statt Flächen und Rahmen selbst zu bauen:

| Klasse | Ergebnis |
|---|---|
| `btn` | Grundform eines Knopfes (Abstände, Radius, Übergang) |
| `btn-primary` | gefüllter Teal-Knopf mit weißer Schrift |
| `btn-outline` | Umrissvariante in Teal |
| `card` | weiße Fläche, weicher Schatten, Radius `xl` (0,625 rem) |
| `input` | Eingabefeld mit Fokusring in Teal |
| `badge`, `badge-primary` | kleines Abzeichen |
| `text-gradient` | Verlaufsschrift, innerhalb der Teal-Familie |

### 5. Schrift

- **Überschriften**: `font-display` → *Newsreader* (Serifen, redaktionell).
  Ein Reisetagebuch ist ein Lesetext, keine Systemsteuerung.
- **Oberfläche**: `font-sans` → *Public Sans*. Beträge und Tabellen fluchten,
  weil am `body` `font-variant-numeric: tabular-nums` gesetzt ist.
- Beide werden **mitgeliefert** (`fonts/`), nicht aus dem Netz geladen — die
  App muss offline funktionieren.

### 6. Form

Enge Radien: Knöpfe `rounded-lg` (0,5 rem), Karten `rounded-xl` (0,625 rem).
Keine Pillenform. Eine Reise-App ist ein Werkzeug, kein Spielzeug.

### 7. Wo die Wahrheit steht

- `styles.css` und seine Importe — die tatsächlich ausgelieferten Regeln.
- `components/<Gruppe>/<Name>/<Name>.d.ts` — der Prop-Vertrag. Die Formen von
  `place`, `entry`, `expense`, `day` und `trip` stehen dort ausgeschrieben.
- `components/<Gruppe>/<Name>/<Name>.prompt.md` — Kurzdoku je Bauteil.

### Beispiel

```jsx
<DesignSystemProvider>
  <div className="min-h-screen bg-primary-50 p-6">
    <h1 className="font-display text-3xl text-gray-900 mb-1">Meine Reisen</h1>
    <p className="text-sm text-gray-600 mb-6">Verwalte und plane deine Abenteuer</p>

    <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
      <PlaceCard place={{ id: 1, name: 'Torre de Belém', latitude: 38.6916,
                          longitude: -9.216, category: 'sight', rating: 5 }} />
    </div>

    <button className="btn btn-primary mt-6">Neue Reise</button>
  </div>
</DesignSystemProvider>
```
