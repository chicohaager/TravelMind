import { ColorPicker } from 'travelmind-frontend'

/** Die Vorgabe: Adria-Teal, die primäre Farbe des Systems. */
export const Standard = () => <ColorPicker value="#1F7A7D" label="Linienfarbe" onChange={() => {}} />

/** Die Signalfarbe — auf einer Karte die Farbe einer Route. */
export const Signalfarbe = () => <ColorPicker value="#D2612F" label="Routenfarbe" onChange={() => {}} />

/** Ohne Beschriftung: nur die Farbfelder, für enge Formulare. */
export const OhneBeschriftung = () => <ColorPicker value="#146264" label="" onChange={() => {}} />
