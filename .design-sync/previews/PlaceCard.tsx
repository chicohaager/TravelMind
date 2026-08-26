import { PlaceCard } from 'travelmind-frontend'

// Echte Orte aus einer echten Reise — keine foo/bar-Platzhalter. Die Karten
// werden von Menschen durchgesehen und vom Design-Agenten nachgeahmt.
const belem = {
  id: 1,
  name: 'Torre de Belém',
  description: 'Wehrturm aus dem 16. Jahrhundert am Tejo, Wahrzeichen der Entdeckerzeit.',
  address: 'Av. Brasília, 1400-038 Lisboa',
  latitude: 38.6916,
  longitude: -9.216,
  category: 'sight',
  rating: 5,
  cost: 8,
  currency: 'EUR',
  visited: false,
  tags: ['UNESCO', 'Aussicht'],
}

export const Standard = () => <PlaceCard place={belem} />

/** Besucht: die Karte kennzeichnet, was schon abgehakt ist. */
export const Besucht = () => (
  <PlaceCard place={{ ...belem, visited: true, notes: 'Früh da sein — ab 10 Uhr lange Schlange.' }} />
)

/** Ohne Bewertung und ohne Preis — der Normalfall beim Anlegen. */
export const Schlicht = () => (
  <PlaceCard
    place={{
      id: 2,
      name: 'Time Out Market',
      latitude: 38.7071,
      longitude: -9.1459,
      category: 'restaurant',
    }}
  />
)

/** Mit allen Handlungen: so steht sie in der Ortsliste einer Reise. */
export const MitAktionen = () => (
  <PlaceCard place={belem} onEdit={() => {}} onDelete={() => {}} onToggleVisited={() => {}} />
)
