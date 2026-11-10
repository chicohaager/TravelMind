import { IconSelector } from 'travelmind-frontend'

/** Die Vorgabe: „Ort" ist ausgewählt. */
export const Standard = () => <IconSelector value="location" onChange={() => {}} />

/** Ein Restaurant — zeigt, dass die Auswahl sichtbar wandert. */
export const Restaurant = () => <IconSelector value="restaurant" onChange={() => {}} />

/** Mit eigener Beschriftung statt der Vorgabe „Symbol". */
export const MitBeschriftung = () => (
  <IconSelector value="beach" label="Symbol für diesen Ort" onChange={() => {}} />
)
