import { AddToTimelineModal } from 'travelmind-frontend'

const orte = [
  { id: 1, name: 'Speicherstadt', category: 'attraction', latitude: 53.5436, longitude: 9.9884 },
  { id: 2, name: 'Elbphilharmonie', category: 'attraction', latitude: 53.5413, longitude: 9.9841 },
  { id: 3, name: 'Restaurant Porto', category: 'restaurant', latitude: 53.5461, longitude: 9.9503 },
]

/** Geöffnet: Ort und Tag wählen, innerhalb des Reisezeitraums. */
export const Geoeffnet = () => (
  <AddToTimelineModal
    isOpen
    places={orte}
    tripStartDate="2026-09-01T00:00:00"
    tripEndDate="2026-09-05T00:00:00"
    onClose={() => {}}
    onSubmit={() => {}}
  />
)

/** Ohne Orte — dann gibt es nichts einzuplanen, und das muss die Karte sagen. */
export const OhneOrte = () => (
  <AddToTimelineModal
    isOpen
    places={[]}
    tripStartDate="2026-09-01T00:00:00"
    tripEndDate="2026-09-05T00:00:00"
    onClose={() => {}}
    onSubmit={() => {}}
  />
)
