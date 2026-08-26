/**
 * Wächter: eine nur ortsgenaue Position darf auf der Karte nicht wie ein
 * exakter Fund aussehen.
 *
 * Am 2026-08-26 an 16 Orten einer echten Reise gemessen: 9 Positionen waren
 * Gemeindemittelpunkte — der Geocoder hatte die Sache nicht gefunden und war
 * auf den blossen Ortsnamen zurückgefallen. Auf der Karte war das nicht zu
 * sehen: „Aussichtspunkt Repušnica" (Dorfmitte) und „Terme Jezerčica" (echter
 * Fund) waren derselbe Punkt ohne Vorbehalt.
 *
 * Geprüft wird die QUELLE der Komponente, nicht ein gerendertes Bild: das
 * Popup steckt in react-leaflet und lässt sich in jsdom nicht ohne Weiteres
 * öffnen. Dafür ist jede Bedingung hier einzeln sabotierbar — und wurde es.
 */

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const hier = dirname(fileURLToPath(import.meta.url))
const karte = readFileSync(join(hier, '..', 'components', 'InteractiveMap.jsx'), 'utf8')

const SPRACHEN = ['de', 'en', 'es', 'fr']

describe('Vorbehalt bei ortsgenauen Positionen', () => {
  it('die Karte wertet position_nur_ort aus', () => {
    expect(karte).toMatch(/place\.position_nur_ort/)
  })

  it('nur ein ausdrückliches true löst den Hinweis aus', () => {
    // `position_nur_ort` ist DREIWERTIG: null heißt „ungeprüft". Ein
    // wahrheitswertiger Test (`place.position_nur_ort &&`) wäre für null
    // ebenfalls falsch — richtig, aber aus Versehen. Der strikte Vergleich
    // hält fest, dass die Dreiwertigkeit gemeint ist.
    expect(karte).toMatch(/place\.position_nur_ort === true/)
  })

  it('der Hinweis ist übersetzt und nicht fest verdrahtet', () => {
    expect(karte).toMatch(/t\('map:nurOrtsgenau'\)/)
  })

  it.each(SPRACHEN)('%s kennt den Schlüssel nurOrtsgenau', (sprache) => {
    const datei = join(hier, '..', 'locales', sprache, 'map.json')
    const texte = JSON.parse(readFileSync(datei, 'utf8'))
    expect(texte.nurOrtsgenau, `map.json fehlt der Schlüssel in ${sprache}`).toBeTruthy()
    // Gegenkontrolle: kein durchgereichter deutscher Text in den anderen drei.
    if (sprache !== 'de') {
      const de = JSON.parse(readFileSync(join(hier, '..', 'locales', 'de', 'map.json'), 'utf8'))
      expect(texte.nurOrtsgenau).not.toBe(de.nurOrtsgenau)
    }
  })
})
