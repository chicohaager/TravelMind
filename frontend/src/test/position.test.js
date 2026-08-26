import { describe, it, expect } from 'vitest'
import { hatPosition, NULL_INSEL_SCHRANKE } from '../components/InteractiveMap'

/**
 * Wächter gegen die Fehlerklasse "ein Ersatzwert sieht aus wie eine Position".
 *
 * Am 2026-08-26 bekam eine Kroatien-Reise acht Orte mit den Koordinaten 0/0,
 * weil die Geokodierung scheiterte und der Fehlschlag als Erfolg gespeichert
 * wurde. Die Karte zentrierte daraufhin auf die Null-Insel im Golf von
 * Guinea: einfarbig blauer Ozean, alle acht Marker exakt übereinander. Es sah
 * aus wie "die Kacheln laden nicht" — tatsächlich luden alle Kacheln mit
 * HTTP 200 und zeigten korrekt offenes Meer.
 *
 * Die alte Prüfung lautete `Number.isFinite(Number(p.latitude))`. Sie hatte
 * ZWEI Löcher, und das zweite wurde erst gefährlich, als die Spalten NULL
 * erlaubten:
 *
 *   Number.isFinite(Number(0))     === true   // Null-Insel
 *   Number.isFinite(Number(null))  === true   // weil Number(null) === 0 (!)
 *
 * Beide Fälle stehen unten. Jeder Test hier wurde durch Sabotage rot gesehen,
 * bevor er eingecheckt wurde.
 */
describe('hatPosition', () => {
  it('erkennt eine echte Position', () => {
    expect(hatPosition({ latitude: 45.4154, longitude: 16.6309 })).toBe(true)
    expect(hatPosition({ latitude: -33.8688, longitude: 151.2093 })).toBe(true)
  })

  it('verwirft 0/0 — das ist ein Ersatzwert, keine Position', () => {
    expect(hatPosition({ latitude: 0, longitude: 0 })).toBe(false)
    expect(hatPosition({ latitude: 0.0, longitude: 0.0 })).toBe(false)
    expect(hatPosition({ latitude: '0', longitude: '0' })).toBe(false)
  })

  it('verwirft null und undefined — Number(null) ist 0, nicht NaN', () => {
    // Genau das ist die Falle: die naive Prüfung hätte hier `true` gesagt.
    expect(Number(null)).toBe(0)
    expect(Number.isFinite(Number(null))).toBe(true)

    expect(hatPosition({ latitude: null, longitude: null })).toBe(false)
    expect(hatPosition({ latitude: 45.4, longitude: null })).toBe(false)
    expect(hatPosition({ latitude: null, longitude: 16.6 })).toBe(false)
    expect(hatPosition({ latitude: undefined, longitude: undefined })).toBe(false)
    expect(hatPosition({})).toBe(false)
    expect(hatPosition(null)).toBe(false)
  })

  it('verwirft Unbrauchbares', () => {
    expect(hatPosition({ latitude: NaN, longitude: 5 })).toBe(false)
    expect(hatPosition({ latitude: 'abc', longitude: 'def' })).toBe(false)
    expect(hatPosition({ latitude: Infinity, longitude: 0 })).toBe(false)
  })

  it('verwirft Werte ausserhalb des gueltigen Bereichs', () => {
    expect(hatPosition({ latitude: 91, longitude: 0.5 })).toBe(false)
    expect(hatPosition({ latitude: -91, longitude: 0.5 })).toBe(false)
    expect(hatPosition({ latitude: 45, longitude: 181 })).toBe(false)
    expect(hatPosition({ latitude: 45, longitude: -181 })).toBe(false)
  })

  it('laesst eine Position knapp neben dem Nullpunkt gelten', () => {
    // Die Schranke darf nicht zu breit sein: 0.001 Grad sind rund 111 m.
    // Ein Ort im Golf von Guinea, der WIRKLICH dort liegt, ist damit ab
    // ~150 m vom Nullpunkt wieder gültig. Ohne diesen Test könnte jemand die
    // Schranke auf 1 Grad "abrunden" und still 110 km Küste ausblenden.
    expect(NULL_INSEL_SCHRANKE).toBeLessThanOrEqual(0.001)
    expect(hatPosition({ latitude: 0.0015, longitude: 0.0015 })).toBe(true)
  })

  it('nur EINE Koordinate am Nullpunkt ist gueltig', () => {
    // Der Äquator und der Nullmeridian sind bewohnt. Nur beides zugleich ist
    // der Ersatzwert.
    expect(hatPosition({ latitude: 0, longitude: 16.6309 })).toBe(true)
    expect(hatPosition({ latitude: 45.4154, longitude: 0 })).toBe(true)
  })
})
