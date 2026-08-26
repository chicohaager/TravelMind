import { InteractiveMap } from 'travelmind-frontend'

const orte = [
  { id: 1, name: 'Speicherstadt', category: 'attraction', latitude: 53.5436, longitude: 9.9884 },
  { id: 2, name: 'Elbphilharmonie', category: 'attraction', latitude: 53.5413, longitude: 9.9841 },
  { id: 3, name: 'Reeperbahn', category: 'nightlife', latitude: 53.5497, longitude: 9.9619 },
]

/** Drei Orte einer Reise — die Karte zoomt auf ihre Ausdehnung. */
export const MitOrten = () => <InteractiveMap places={orte} />

/** Mit gezeichneter Route: die Linie in der Signalfarbe der Palette. */
export const MitRoute = () => (
  <InteractiveMap
    places={orte}
    routes={[{ id: 1, name: 'Tag 1: Hafen', color: '#D2612F', place_ids: [1, 2, 3] }]}
  />
)

/** Ohne Orte — der Zustand einer frisch angelegten Reise. */
export const Leer = () => <InteractiveMap places={[]} />
