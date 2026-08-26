import { PlaceDetailModal } from 'travelmind-frontend'

const belem = {
  id: 1,
  name: 'Torre de Belém',
  description:
    'Wehrturm aus dem 16. Jahrhundert am Tejo. Von der Plattform sieht man über die Mündung ' +
    'bis zur Ponte 25 de Abril.',
  address: 'Av. Brasília, 1400-038 Lisboa',
  latitude: 38.6916,
  longitude: -9.216,
  category: 'sight',
  rating: 5,
  cost: 8,
  currency: 'EUR',
  website: 'https://www.torrebelem.gov.pt',
  notes: 'Früh da sein — ab 10 Uhr lange Schlange.',
  tags: ['UNESCO', 'Aussicht'],
}

/** Geöffnet mit allen Angaben — so sieht der Nutzer einen Ort im Detail. */
export const Geoeffnet = () => <PlaceDetailModal place={belem} isOpen onClose={() => {}} />

/** Ein knapper Datensatz: nur Name, Kategorie und Koordinaten. */
export const Knapp = () => (
  <PlaceDetailModal
    place={{ id: 2, name: 'Time Out Market', latitude: 38.7071, longitude: -9.1459, category: 'restaurant' }}
    isOpen
    onClose={() => {}}
  />
)
