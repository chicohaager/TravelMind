import { TimelineEntryCard } from 'travelmind-frontend'

const eintrag = {
  id: 1,
  place_id: 100,
  place_name: 'Miniatur Wunderland',
  place_category: 'attraction',
  place_latitude: 53.5436,
  place_longitude: 9.9884,
  order: 0,
  notes: 'Tickets vorab buchen — sonst zwei Stunden Wartezeit.',
}

export const Standard = () => <TimelineEntryCard entry={eintrag} index={0} />

/** Ohne Notiz — der häufigere Fall beim schnellen Planen. */
export const OhneNotiz = () => (
  <TimelineEntryCard
    entry={{ ...eintrag, id: 2, place_name: 'Elbphilharmonie', order: 1, notes: undefined }}
    index={1}
  />
)

// Eine dritte Zelle "SpaeterAmTag" (andere Ordnungszahl, andere Kategorie)
// stand hier bis zum 2026-08-26 — sie sah identisch zu `Standard` aus, weil
// die Komponente weder Ordnungszahl noch Kategorie rendert. Eine Zelle, die
// nichts Neues zeigt, ist Rauschen auf der Karte.
