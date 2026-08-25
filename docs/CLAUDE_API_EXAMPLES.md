# 🤖 Claude API - Beispiele & Verwendung

## Übersicht

TravelMind nutzt die Claude API von Anthropic für intelligente Reiseempfehlungen und Planung.

## Setup

```python
from anthropic import Anthropic

client = Anthropic(api_key="sk-ant-...")

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2048,
    messages=[{
        "role": "user",
        "content": "Dein Prompt hier..."
    }]
)

result = response.content[0].text
```

## Beispiel 1: Reiseziele vorschlagen

### Request

```python
prompt = """Du bist ein erfahrener Reiseplaner. Empfehle 5 passende Reiseziele basierend auf:

Interessen: Natur, Fotografie, Wandern
Dauer: 7 Tage
Budget: medium
Jahreszeit: Sommer

Gib für jedes Ziel:
- Name und Land
- Warum es passt (2-3 Sätze)
- Beste Reisezeit
- Geschätztes Budget pro Tag
- Top 3 Aktivitäten

Ausgabe als JSON:
{
    "destinations": [
        {
            "name": "...",
            "country": "...",
            "reason": "...",
            "best_time": "...",
            "daily_budget": "...",
            "activities": ["...", "...", "..."],
            "coordinates": {"lat": 0.0, "lng": 0.0}
        }
    ]
}"""
```

### Response

```json
{
  "destinations": [
    {
      "name": "Lofoten",
      "country": "Norwegen",
      "reason": "Die Lofoten-Inseln bieten spektakuläre Fjordlandschaften, dramatische Berge und unberührte Natur. Perfekt für Wanderer und Fotografen mit der Mitternachtssonne im Sommer. Die Kombination aus Bergen, Meer und malerischen Fischerdörfern ist ein Paradies für Naturliebhaber.",
      "best_time": "Juni - August",
      "daily_budget": "120-150 EUR",
      "activities": [
        "Wanderung zum Reinebringen",
        "Kayaking in den Fjorden",
        "Fotografie der Mitternachtssonne"
      ],
      "coordinates": {
        "lat": 68.1102,
        "lng": 13.5467
      }
    },
    {
      "name": "Dolomiten",
      "country": "Italien",
      "reason": "UNESCO-Welterbe mit beeindruckenden Kalksteingipfeln und spektakulären Wanderwegen. Die Dolomiten bieten perfekte Bedingungen für Bergfotografie und mehrtägige Hüttenwanderungen. Kombiniert alpines Erlebnis mit italienischer Küche und Kultur.",
      "best_time": "Juni - September",
      "daily_budget": "90-120 EUR",
      "activities": [
        "Tre Cime di Lavaredo Umrundung",
        "Alpenglühen-Fotografie",
        "Via Ferratas klettern"
      ],
      "coordinates": {
        "lat": 46.4102,
        "lng": 11.8440
      }
    },
    {
      "name": "Schottisches Hochland",
      "country": "Schottland",
      "reason": "Mystische Landschaften mit Bergen, Seen und alten Burgen. Ideal für Landschaftsfotografie mit dramatischem Licht und wechselndem Wetter. Einsame Wanderwege durch Glens und Munros bieten authentische Naturerlebnisse.",
      "best_time": "Mai - September",
      "daily_budget": "80-110 EUR",
      "activities": [
        "West Highland Way wandern",
        "Glencoe Fotografie",
        "Munro-Besteigung"
      ],
      "coordinates": {
        "lat": 57.4778,
        "lng": -4.2247
      }
    },
    {
      "name": "Patagonien",
      "country": "Chile/Argentinien",
      "reason": "Eines der spektakulärsten Naturwunder der Welt mit Gletschern, türkisfarbenen Seen und dramatischen Berglandschaften. Torres del Paine Nationalpark bietet Weltklasse-Trekking und Fotomotive. Für abenteuerlustige Naturliebhaber ein absolutes Highlight.",
      "best_time": "Dezember - Februar (Südsommer)",
      "daily_budget": "100-140 EUR",
      "activities": [
        "W-Trek in Torres del Paine",
        "Perito Moreno Gletscher",
        "Wildlife-Fotografie"
      ],
      "coordinates": {
        "lat": -50.9423,
        "lng": -73.4068
      }
    },
    {
      "name": "Island",
      "country": "Island",
      "reason": "Land aus Feuer und Eis mit Vulkanen, Wasserfällen, Geysiren und Gletschern auf kleinstem Raum. Perfekt für Naturfotografie mit einzigartigen Landschaften. Die Ringstraße ermöglicht einfache Selbstfahrer-Touren zu allen Highlights.",
      "best_time": "Juni - August",
      "daily_budget": "130-180 EUR",
      "activities": [
        "Golden Circle Tour",
        "Gletscherwanderung",
        "Wasserfall-Fotografie"
      ],
      "coordinates": {
        "lat": 64.9631,
        "lng": -19.0208
      }
    }
  ]
}
```

## Beispiel 2: Detaillierten Reiseplan erstellen

### Request

```python
prompt = """Du bist ein erfahrener Reiseplaner. Erstelle einen detaillierten 5-tägigen Reiseplan für Lissabon.

Interessen: Kultur, Essen, Fotografie

Erstelle für jeden Tag:
- Morgen, Mittag, Abend Aktivitäten
- Empfohlene Restaurants/Cafés
- Geschätzte Kosten
- Praktische Tipps (Transport, Tickets, etc.)

Füge hinzu:
- Geheimtipps abseits der Touristenpfade
- Lokale Spezialitäten zum Probieren
- Wichtige praktische Informationen

Ausgabe als strukturiertes JSON"""
```

### Response (gekürzt)

```json
{
  "trip_overview": {
    "destination": "Lissabon",
    "duration": 5,
    "best_for": ["Kultur", "Kulinarik", "Fotografie"],
    "total_estimated_cost": "450-650 EUR"
  },
  "days": [
    {
      "day": 1,
      "theme": "Alfama & Historisches Zentrum",
      "morning": {
        "activity": "Castelo de São Jorge besichtigen",
        "location": "Castelo de São Jorge",
        "cost": "10 EUR",
        "tips": "Komme früh (9 Uhr) für beste Fotobedingungen und weniger Touristen"
      },
      "afternoon": {
        "activity": "Alfama-Viertel erkunden",
        "location": "Alfama",
        "cost": "kostenlos",
        "tips": "Verlaufe dich absichtlich in den Gassen - hier findest du die besten Fotomotive"
      },
      "evening": {
        "activity": "Fado-Abend mit Abendessen",
        "location": "Clube de Fado",
        "cost": "50-70 EUR",
        "tips": "Reserviere im Voraus. Authentischer Fado wird in kleineren Häusern gespielt"
      },
      "meals": [
        "Frühstück: Pastelaria Santo António (Pastéis de Nata)",
        "Mittagessen: Tasca do Chico (Petiscos)",
        "Abendessen: Im Fado-Haus inklusive"
      ],
      "transport": "Zu Fuß + Tram 28 (6 EUR Tageskarte)",
      "photo_spots": [
        "Miradouro das Portas do Sol (Sonnenaufgang)",
        "Gassen von Alfama (mittags)",
        "Castelo-Aussicht (Sonnenuntergang)"
      ]
    },
    {
      "day": 2,
      "theme": "Belém & Moderne Architektur",
      "morning": {
        "activity": "Mosteiro dos Jerónimos",
        "location": "Belém",
        "cost": "10 EUR",
        "tips": "Online-Ticket kaufen um Warteschlangen zu vermeiden"
      },
      "afternoon": {
        "activity": "MAAT Museum & Uferpromenade",
        "location": "Belém",
        "cost": "5 EUR",
        "tips": "Perfekt für Architekturfotografie, besonders bei Sonnenuntergang"
      },
      "evening": {
        "activity": "LX Factory erkunden",
        "location": "Alcântara",
        "cost": "20-30 EUR",
        "tips": "Kreatives Viertel mit Bars, Restaurants und Street Art"
      },
      "meals": [
        "Snack: Pastéis de Belém (Original)",
        "Mittagessen: Darwin's Café (in LX Factory)",
        "Abendessen: Rio Maravilha (LX Factory Rooftop)"
      ],
      "transport": "Tram 15E + zu Fuß"
    }
  ],
  "local_tips": [
    "🎫 Kaufe eine Viva Viagem Karte für öffentliche Verkehrsmittel",
    "🌅 Beste Fotospots bei goldenem Licht: Miradouros bei Sonnenauf-/untergang",
    "🍷 Probiere Ginjinha (Kirschlikör) in einer der kleinen Bars in Alfama",
    "📸 Vermeide Tram 28 zur Rushhour - überfüllt und schwer für Fotos",
    "🏛️ Viele Museen sind montags geschlossen - plane entsprechend",
    "💰 In Tascas (kleine Restaurants) isst man oft besser und günstiger"
  ],
  "food_recommendations": [
    "Pastéis de Nata - nur bei Pastéis de Belém",
    "Bacalhau (Kabeljau) - über 1000 Zubereitungsarten",
    "Bifana - portugiesisches Schweinefleisch-Sandwich",
    "Conservas - hochwertige Fischkonserven als Delikatesse",
    "Vinho Verde - junger, spritziger Weißwein"
  ],
  "hidden_gems": [
    "Miradouro da Graça - weniger touristisch als Santa Luzia",
    "Mercado de Campo de Ourique - lokaler Markt mit Food Court",
    "Cemitério dos Prazeres - friedliche Atmosphäre und Aussicht",
    "Jardim da Estrela - perfekt für Picknick",
    "Feira da Ladra - Flohmarkt (Di & Sa)"
  ],
  "practical_info": {
    "language": "Portugiesisch - Englisch wird in touristischen Bereichen gesprochen",
    "currency": "Euro (EUR)",
    "tipping": "5-10% in Restaurants, aufrunden bei Taxis",
    "safety": "Sehr sicher, aber Achtung vor Taschendieben in Tram 28 und touristischen Gebieten",
    "best_photo_time": "Golden Hour 7-8 Uhr morgens und 19-20 Uhr abends",
    "power": "230V, EU-Stecker (Typ F)"
  }
}
```

## Beispiel 3: Destination beschreiben

### Request

```python
prompt = """Erstelle eine poetische, aber informative Beschreibung des Reiseziels Kyoto.

Betone:
- Atmosphäre und Stimmung
- Kultur und Geschichte
- Natur und Landschaft
- Besondere Charakteristika

Stil: Inspirierend, reiselustig, aber nicht übertrieben
Länge: Maximal 300 Wörter
Ausgabe: Markdown-formatiert mit Absätzen"""
```

### Response

```markdown
# Kyoto - Wo die Seele Japans lebt

Zwischen den sanften Hügeln des Higashiyama-Gebirges und den nebelverhangenen Wäldern von Arashiyama liegt Kyoto – eine Stadt, die Zeit und Tradition in einer Weise bewahrt hat, die in der modernen Welt selten geworden ist.

## Tempel der Stille

Über tausend buddhistische Tempel und shintoistische Schreine prägen das Stadtbild. Der goldene Kinkaku-ji spiegelt sich perfekt im stillen Wasser seines Teiches, während der Fushimi Inari-Taisha mit seinen endlosen roten Torii-Toren Besucher auf mystische Pfade durch den Berg führt. Hier verschmilzt Spiritualität mit Natur zu einer Harmonie, die man nicht nur sieht, sondern fühlt.

## Vier Jahreszeiten der Schönheit

Kyoto verwandelt sich mit den Jahreszeiten. Im Frühling explodieren tausende Kirschbäume in zartem Rosa, während der Herbst die Ahornwälder in flammendes Rot und leuchtendes Gold taucht. Selbst der Winter legt einen stillen, weißen Schleier über die Zen-Gärten und schafft Momente zeitloser Schönheit.

## Tradition trifft Gegenwart

In den schmalen Gassen von Gion gleiten Geishas in prächtigen Kimonos zu ihren Terminen, während moderne Cafés und Restaurants traditionelle Kaiseki-Küche neu interpretieren. Der Philosophenweg führt entlang eines Kanals durch das alltägliche Leben – ein Spaziergang zwischen Kontemplation und urbanem Puls.

## Das Kyoto-Gefühl

Es ist schwer zu beschreiben, aber unmöglich zu vergessen: Dieses Gefühl, wenn man bei Sonnenaufgang durch den Bambuswald von Arashiyama wandert, wenn Nebel durch die Stämme zieht und das Licht die Welt in sanftes Grün taucht. Oder der Moment, wenn man in einem versteckten Teehaus sitzt und zum ersten Mal Matcha-Tee in vollkommener Stille genießt.

Kyoto ist nicht nur ein Reiseziel – es ist eine Reise zu sich selbst.
```

## Beispiel 4: Chat-Assistent

### Request

```python
message = "Was sind die besten Aussichtspunkte in Lissabon für Fotografen?"
context = {
    "destination": "Lissabon",
    "interests": ["Fotografie", "Kultur"]
}

system_prompt = """Du bist ein freundlicher, erfahrener Reiseassistent.
Du gibst hilfreiche, praktische Tipps und Empfehlungen.
Deine Antworten sind präzise, informativ und inspirierend.
Du kannst auch GPS-Koordinaten für Orte bereitstellen wenn relevant."""
```

### Response

```text
Großartige Frage! Lissabon ist ein Traum für Fotografen - hier sind meine Top-Aussichtspunkte:

🌅 **Miradouro da Senhora do Monte**
- Höchster Aussichtspunkt in Lissabon
- 360° Panorama über die ganze Stadt
- Beste Zeit: Sonnenuntergang (magisches goldenes Licht)
- GPS: 38.7194° N, 9.1333° W
- Tipp: Komme 30 Min vor Sonnenuntergang für besten Spot

🏰 **Castelo de São Jorge**
- Historische Burganlage mit mehreren Aussichtsplattformen
- Perfekt für Weitwinkelaufnahmen
- Beste Zeit: Früher Morgen (wenig Touristen) oder blaue Stunde
- GPS: 38.7139° N, 9.1334° W
- Kosten: 10 EUR Eintritt

🌊 **Miradouro das Portas do Sol**
- Blick über die Dächer von Alfama
- Perfekt für Sonnenaufgang
- Cafés mit Terrasse vor Ort
- GPS: 38.7117° N, 9.1333° W
- Tipp: Kostenlos und rund um die Uhr zugänglich

📸 **Miradouro de Santa Catarina**
- Lokaler Geheimtipp, weniger touristisch
- Blick auf Brücke 25 de Abril und Tejo
- Beste Zeit: Spätnachmittag
- GPS: 38.7081° N, 9.1467° W
- Street-Art Hintergrund für Urban Photography

🌉 **Cristo Rei**
- Gegenüberliegende Flussseite
- Spektakuläre Perspektive auf die ganze Stadt
- Erreichbar mit Fähre + Bus
- GPS: 38.6791° N, 9.1714° W
- Tipp: Beste Stadtansicht für Sonnenuntergang

**Pro-Tipps für Fotografen:**
- Goldene Stunde: 7:00-8:30 morgens, 19:00-20:30 abends (Sommer)
- App "The Photographer's Ephemeris" für Sonnenstand
- Polfilter für bessere Farben empfohlen
- Drohne fliegen nur mit Genehmigung!

Möchtest du mehr Details zu einem bestimmten Spot?
```

## Beispiel 5: Lokale Geheimtipps

### Request

```python
destination = "Barcelona"
category = "restaurants"

prompt = """Liste 10 Geheimtipps für Barcelona auf, Kategorie: Restaurants und Cafés.

Fokus auf:
- Authentische, lokale Orte
- Abseits der Touristenpfade
- Von Einheimischen geschätzt
- Besondere Atmosphäre

Ausgabe als JSON Array"""
```

### Response (gekürzt)

```json
[
  {
    "name": "Can Culleretes",
    "category": "Restaurant",
    "description": "Ältestes Restaurant Barcelonas seit 1786. Traditionelle katalanische Küche in rustikalem Ambiente. Hier essen Einheimische seit Generationen.",
    "why_special": "Authentisches katalanisches Essen ohne Touristenfallen. Familiengeführt mit Rezepten von vor 200 Jahren.",
    "location": "Carrer Quintana, 5, Barri Gòtic",
    "coordinates": {
      "lat": 41.3809,
      "lng": 2.1734
    },
    "insider_tip": "Bestelle 'Escudella i carn d'olla' - katalanischer Eintopf, den kein Tourist kennt. Keine Reservierung möglich, komme um 13:00 Uhr."
  },
  {
    "name": "Bar Bodega Quimet",
    "category": "Tapas Bar",
    "description": "Winzige Tapas-Bar in Poble Sec, nur Stehplätze. Berühmt für montaditos (belegte Brötchen) und Vermut.",
    "why_special": "Nur Einheimische kennen diesen Ort. Der Besitzer Quimet kreiert täglich neue, kunstvolle Tapas-Kombinationen.",
    "location": "Carrer del Poeta Cabanyes, 25",
    "coordinates": {
      "lat": 41.3728,
      "lng": 2.1661
    },
    "insider_tip": "Lass dich von Quimet beraten - er kennt jeden Stammgast beim Namen. Komme zwischen 12-14 Uhr oder 19-21 Uhr."
  },
  {
    "name": "Els Quatre Gats",
    "category": "Café & Restaurant",
    "description": "Historisches Café wo Picasso seine ersten Werke ausstellte. Modernistische Architektur und böhmisches Flair.",
    "why_special": "Kulturelles Erbe Barcelonas. Hier trafen sich Künstler und Intellektuelle des frühen 20. Jahrhunderts.",
    "location": "Carrer de Montsió, 3",
    "coordinates": {
      "lat": 41.3864,
      "lng": 2.1734
    },
    "insider_tip": "Komme für einen Kaffee am Nachmittag, nicht zum Essen (überteuert). Bewundere die Jugendstil-Details."
  }
]
```

## Best Practices

### 1. Strukturierte Ausgabe

Fordere immer JSON-Format für maschinelle Verarbeitung:

```python
prompt += "\n\nAusgabe als JSON: { ... }"
```

### 2. Klare Anweisungen

Sei spezifisch mit deinen Anforderungen:

- Welche Informationen?
- Welches Format?
- Welcher Ton/Stil?
- Maximale Länge?

### 3. Kontext bereitstellen

Gib Claude relevanten Kontext:

```python
context = {
    "trip": {
        "destination": "Paris",
        "dates": "2024-07-15 bis 2024-07-22",
        "travelers": 2,
        "budget": "medium"
    }
}
```

### 4. System Prompts nutzen

Definiere die Rolle von Claude:

```python
system_prompt = """Du bist ein Experte für [Thema].
Du antwortest [Stil].
Du gibst [Art von Informationen]."""
```

### 5. Error Handling

Fange Parsing-Fehler ab:

```python
try:
    data = json.loads(response)
except json.JSONDecodeError:
    # Fallback auf raw text
    data = {"raw_response": response}
```

## Rate Limits & Kosten

**Anthropic Claude Pricing (Stand 2024):**

- Input: ~$3 / 1M tokens
- Output: ~$15 / 1M tokens

**Empfohlene Limits:**

- `max_tokens`: 2048 für Pläne, 1024 für Chat
- Rate Limit: ~50 Requests/Minute
- Caching: Häufige Antworten cachen

## Weitere Ressourcen

- [Claude API Docs](https://docs.anthropic.com/)
- [Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)
- [Best Practices](https://docs.anthropic.com/claude/docs/best-practices)

---

Entwickelt mit ❤️ und Claude AI
