import { DiaryEntry } from 'travelmind-frontend'

const tagEins = {
  id: 1,
  title: 'Tag 1 — Ankunft in der Alfama',
  content:
    'Der Zug aus dem Flughafen war voll, aber die Gasse hinauf zum Castelo hat alles wettgemacht. ' +
    'Abends Fado in einer Tasca, in der außer uns niemand Englisch sprach.',
  entry_date: '2026-09-01T19:30:00',
  location_name: 'Alfama, Lissabon',
  latitude: 38.7139,
  longitude: -9.1334,
  mood: 'happy' as const,
  rating: 5,
  tags: ['Fado', 'Altstadt'],
}

export const Standard = () => <DiaryEntry entry={tagEins} />

/** Die drei Stimmungen — die Achse, die das Aussehen am stärksten ändert. */
export const StimmungNeutral = () => (
  <DiaryEntry entry={{ ...tagEins, title: 'Tag 2 — Regen in Belém', mood: 'neutral', rating: 3 }} />
)

export const StimmungTraurig = () => (
  <DiaryEntry
    entry={{
      ...tagEins,
      title: 'Tag 5 — Abreise',
      content: 'Zu früh am Flughafen und zu wenig Zeit gehabt für den Norden.',
      mood: 'sad',
      rating: 2,
    }}
  />
)

/** Nur Text: kein Ort, keine Stimmung, keine Schlagwörter. */
export const NurText = () => (
  <DiaryEntry
    entry={{
      id: 4,
      title: 'Notiz unterwegs',
      content: 'Bus 728 fährt direkt zum Mosteiro. Ticket im Bus teurer als am Automaten.',
    }}
  />
)

/** Mit Handlungen, wie er in der Tagebuchliste steht. */
export const MitAktionen = () => <DiaryEntry entry={tagEins} onEdit={() => {}} onDelete={() => {}} />
