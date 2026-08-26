import { describe, it, expect } from 'vitest'
import i18n from '../i18n'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname, basename, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * Wächter für zwei i18n-Fehlerklassen, die beide am 2026-08-25 in der laufenden
 * Produktion gefunden wurden — und die beide unsichtbar waren, weil ein Fallback
 * etwas Plausibles anzeigte statt laut zu scheitern.
 *
 *  1. Namensraum mit PUNKT statt DOPPELPUNKT:  t('interests.culture', 'culture')
 *     i18next sucht dann den Schlüssel "interests.culture" im Standard-Namensraum
 *     'common', findet ihn nicht und gibt den Fallback zurück. Auf dem Bildschirm
 *     stand "+ culture" statt "+ Kultur" — in einer deutschen Oberfläche, während
 *     die Übersetzung in allen vier Sprachen danebenlag und nur unerreichbar war.
 *
 *  2. Auseinanderlaufende Sprachdateien: es und fr fehlten je 7 Schlüssel und
 *     trugen 15 ungenutzte. Spanische und französische Nutzer sahen an diesen
 *     Stellen englischen Fallback-Text mitten in ihrer Oberfläche.
 *
 * Beide Prüfungen können rot UND grün werden — jede hat unten eine
 * Positivkontrolle, die belegt, dass sie überhaupt anschlägt.
 */

const hier = dirname(fileURLToPath(import.meta.url))
const srcVerzeichnis = join(hier, '..')
const localesVerzeichnis = join(srcVerzeichnis, 'locales')

const REFERENZSPRACHE = 'de'

function dateienRekursiv(verzeichnis, endungen) {
  const treffer = []
  for (const eintrag of readdirSync(verzeichnis)) {
    const pfad = join(verzeichnis, eintrag)
    if (statSync(pfad).isDirectory()) {
      if (eintrag === 'locales' || eintrag === 'node_modules') continue
      treffer.push(...dateienRekursiv(pfad, endungen))
    } else if (endungen.some((e) => eintrag.endsWith(e))) {
      treffer.push(pfad)
    }
  }
  return treffer
}

function flach(objekt, praefix = '') {
  const raus = []
  for (const [schluessel, wert] of Object.entries(objekt)) {
    const pfad = praefix ? `${praefix}.${schluessel}` : schluessel
    if (wert && typeof wert === 'object' && !Array.isArray(wert)) {
      raus.push(...flach(wert, pfad))
    } else {
      raus.push(pfad)
    }
  }
  return raus
}

function schluesselDerSprache(sprache) {
  const menge = new Set()
  const verzeichnis = join(localesVerzeichnis, sprache)
  for (const datei of readdirSync(verzeichnis).filter((d) => d.endsWith('.json'))) {
    const namensraum = basename(datei, '.json')
    const inhalt = JSON.parse(readFileSync(join(verzeichnis, datei), 'utf8'))
    for (const schluessel of flach(inhalt)) menge.add(`${namensraum}:${schluessel}`)
  }
  return menge
}

const sprachen = readdirSync(localesVerzeichnis).filter((e) =>
  statSync(join(localesVerzeichnis, e)).isDirectory()
)
const namensraeume = readdirSync(join(localesVerzeichnis, REFERENZSPRACHE))
  .filter((d) => d.endsWith('.json'))
  .map((d) => basename(d, '.json'))

/**
 * Findet t('<namensraum>.…') — also den Namensraum, der faelschlich mit einem
 * Punkt statt einem Doppelpunkt angesprochen wird.
 */
function namensraumMitPunkt(quelltext) {
  const alternativen = namensraeume.join('|')
  const muster = new RegExp(`\\bt\\(\\s*[\`'"]\\s*(${alternativen})\\.`, 'g')
  return [...quelltext.matchAll(muster)].map((m) => m[0])
}

describe('i18n: Sprachdateien decken sich', () => {
  const referenz = schluesselDerSprache(REFERENZSPRACHE)

  it(`findet mehr als eine Sprache und eine nicht-leere Referenz (${REFERENZSPRACHE})`, () => {
    expect(sprachen.length).toBeGreaterThan(1)
    expect(referenz.size).toBeGreaterThan(100)
  })

  for (const sprache of sprachen.filter((s) => s !== REFERENZSPRACHE)) {
    it(`${sprache} hat genau dieselben Schlüssel wie ${REFERENZSPRACHE}`, () => {
      const eigene = schluesselDerSprache(sprache)
      const fehlend = [...referenz].filter((k) => !eigene.has(k)).sort()
      const ueberzaehlig = [...eigene].filter((k) => !referenz.has(k)).sort()
      expect({ fehlend, ueberzaehlig }).toEqual({ fehlend: [], ueberzaehlig: [] })
    })
  }

  it('Positivkontrolle: ein entfernter Schlüssel würde auffallen', () => {
    // Belegt, dass der Vergleich oben ueberhaupt anschlagen kann.
    const kuenstlich = new Set(referenz)
    const einer = [...referenz][0]
    kuenstlich.delete(einer)
    const fehlend = [...referenz].filter((k) => !kuenstlich.has(k))
    expect(fehlend).toEqual([einer])
  })
})

describe('i18n: Namensräume werden mit Doppelpunkt angesprochen', () => {
  const quellDateien = dateienRekursiv(srcVerzeichnis, ['.jsx', '.js']).filter(
    (p) => !p.endsWith('.test.js') && !p.endsWith('.test.jsx')
  )

  it('findet überhaupt Quelldateien', () => {
    expect(quellDateien.length).toBeGreaterThan(20)
  })

  it('kein t() spricht einen Namensraum mit einem Punkt an', () => {
    const treffer = []
    for (const pfad of quellDateien) {
      for (const stelle of namensraumMitPunkt(readFileSync(pfad, 'utf8'))) {
        treffer.push(`${relative(srcVerzeichnis, pfad)}: ${stelle}`)
      }
    }
    expect(treffer).toEqual([])
  })

  it('Positivkontrolle: der Scanner erkennt einen künstlichen Verstoß', () => {
    const beispiel = 'const x = t(`interests.${interest}`, interest)'
    expect(namensraumMitPunkt(beispiel).length).toBe(1)
    // Gegenkontrolle: die richtige Schreibweise darf NICHT anschlagen
    const richtig = 'const x = t(`interests:${interest}`, interest)'
    expect(namensraumMitPunkt(richtig)).toEqual([])
  })
})

describe('i18n: kein Namensraum mit Punkt, auch nicht in einer Variablen', () => {
  /*
   * Erweiterung vom 2026-08-25, nachdem drei Bildschirmfotos mit rohen
   * Schlüsseln geschickt hat: `diary.moodHappy` im Stimmungswähler,
   * `budget.categories.other` in der Kategorieliste.
   *
   * Der Scanner darüber prüft `t('…')`-Aufrufe. Diese Stellen sahen anders
   * aus — der Schlüssel lag in einer Eigenschaft:
   *
   *     { value: 'happy', labelKey: 'diary.moodHappy' }   …   t(mood.labelKey)
   *
   * Der Aufruf war sauber, die Zeichenkette nicht. 18 Fundstellen in 5
   * Dateien, alle live sichtbar. Der Wächter war grün und blind.
   *
   * Deshalb sucht diese Prüfung die ZEICHENKETTE, wo immer sie steht: ein
   * Literal, das mit einem echten Namensraum plus Punkt beginnt.
   */
  const namensraeume = readdirSync(localesVerzeichnis + '/' + REFERENZSPRACHE)
    .filter((d) => d.endsWith('.json'))
    .map((d) => basename(d, '.json'))

  const punktMuster = new RegExp(`['"\`](${namensraeume.join('|')})\\.([A-Za-z0-9_.]+)['"\`]`, 'g')

  const quellen = dateienRekursiv(srcVerzeichnis, ['.js', '.jsx']).filter(
    (d) => !/\.(test|spec)\.jsx?$/.test(basename(d))
  )

  it('findet überhaupt Namensräume und Quelldateien', () => {
    expect(namensraeume.length).toBeGreaterThan(20)
    expect(quellen.length).toBeGreaterThan(20)
  })

  it('keine Zeichenkette spricht einen Namensraum mit Punkt an', () => {
    const verstoesse = []
    for (const datei of quellen) {
      const zeilen = readFileSync(datei, 'utf8').split('\n')
      zeilen.forEach((zeile, i) => {
        for (const treffer of zeile.matchAll(punktMuster)) {
          verstoesse.push(`${relative(srcVerzeichnis, datei)}:${i + 1}  ${treffer[0]}`)
        }
      })
    }
    expect(verstoesse).toEqual([])
  })

  it('Positivkontrolle: der Scanner erkennt die Form aus dem Fehlerbild', () => {
    const kuenstlich = "  { value: 'happy', labelKey: 'diary.moodHappy' },"
    expect([...kuenstlich.matchAll(punktMuster)].length).toBe(1)
  })

  it('Gegenkontrolle: die Doppelpunkt-Form löst NICHT aus', () => {
    const sauber = "  { value: 'happy', labelKey: 'diary:moodHappy' },"
    expect([...sauber.matchAll(punktMuster)].length).toBe(0)
  })
})

describe('i18n: <html lang> folgt der Sprache', () => {
  // In index.html stand fest lang="de". Am 2026-08-25 in der Produktion
  // gemessen: Oberfläche auf Spanisch, Attribut weiter auf 'de'.
  for (const sprache of ['de', 'en', 'es', 'fr']) {
    it(`setzt lang="${sprache}", wenn auf '${sprache}' gewechselt wird`, async () => {
      await i18n.changeLanguage(sprache)
      expect(document.documentElement.getAttribute('lang')).toBe(sprache)
    })
  }

  it('schneidet die Region ab: "de-DE" ergibt lang="de"', async () => {
    await i18n.changeLanguage('de-DE')
    expect(document.documentElement.getAttribute('lang')).toBe('de')
  })
})

describe('i18n: keine fest verdrahteten Locales im Quelltext', () => {
  // format.js ist die EINZIGE Stelle, an der eine konkrete Locale stehen darf —
  // dort steht die Zuordnung Sprache -> Locale. Ueberall sonst ist ein
  // 'de-DE' oder 'en-US' im Code eine Sprache, die jemand vergessen hat:
  // Bis 2026-08-25 stand in TripDetail `toLocaleString('de-DE')` und in
  // Transcribe dasselbe — spanische und franzoesische Nutzer bekamen dort
  // deutsche Formatierung.
  const erlaubt = ['utils/format.js', 'utils/format.test.js', 'test/i18n-integrity.test.js']
  const localeMuster = /['"`][a-z]{2}-[A-Z]{2}['"`]/

  const quellDateien = dateienRekursiv(srcVerzeichnis, ['.jsx', '.js'])

  it('findet überhaupt Quelldateien', () => {
    expect(quellDateien.length).toBeGreaterThan(20)
  })

  it('keine Datei ausser format.js nennt eine konkrete Locale', () => {
    const treffer = []
    for (const pfad of quellDateien) {
      const kurz = relative(srcVerzeichnis, pfad)
      if (erlaubt.some((e) => kurz.endsWith(e))) continue
      readFileSync(pfad, 'utf8')
        .split('\n')
        .forEach((zeile, i) => {
          // Kommentare zaehlen nicht — dort steht die Begruendung.
          if (zeile.trim().startsWith('//') || zeile.trim().startsWith('*')) return
          if (localeMuster.test(zeile)) treffer.push(`${kurz}:${i + 1}: ${zeile.trim()}`)
        })
    }
    expect(treffer).toEqual([])
  })

  it('Positivkontrolle: der Scanner erkennt eine künstliche Locale', () => {
    expect(localeMuster.test("new Date().toLocaleString('de-DE')")).toBe(true)
    expect(localeMuster.test('const x = aktuelleLocale()')).toBe(false)
  })
})

/**
 * Vierter Wächter, ergänzt am 2026-08-25.
 *
 * Die drei Prüfungen oben decken FALSCH ANGESPROCHENE und FEHLENDE
 * Übersetzungen ab. Sie sehen die dritte Fehlerklasse nicht: einen Text, der
 * gar nicht erst durch `t()` läuft.
 *
 * Gefunden wurde sie an einem Eintrag in der Seitenleiste — `name:
 * 'Transcription'` stand fest im Quelltext und war deshalb in JEDER Sprache
 * englisch, während `transcribe:title` in allen vier Sprachen danebenlag. Der
 * anschließende Scan über alle Komponenten fand 25 weitere Stellen derselben
 * Art, darunter drei fest DEUTSCHE (`label: 'Glücklich'`) — ein englischer
 * Nutzer hätte dort deutsche Wörter gesehen.
 *
 * Grep allein hätte das nicht gefunden: gesucht werden muss die Form
 * `eigenschaft: 'Grossbuchstabe…'`, nicht ein bestimmtes Wort.
 */
describe('i18n: keine fest verdrahteten Beschriftungen in Komponenten', () => {
  // Eigennamen. Marken werden nicht übersetzt — diese Ausnahme nennt WERTE,
  // nicht Dateien, und ist damit enger als die Regel: ein neues englisches
  // Wort in derselben Datei schlägt weiterhin an.
  const EIGENNAMEN = new Set(['WhatsApp', 'Telegram', 'X / Twitter', 'Facebook'])

  // pages/Home.jsx enthält Beispieldaten und ist NICHT erreichbar: die Route
  // "/" leitet auf /trips um. Die Ausnahme hängt an genau dieser Tatsache —
  // der Test darunter wird rot, sobald sie nicht mehr gilt.
  const UNERREICHBAR = 'pages/Home.jsx'

  const beschriftung = /\b(name|label|title)\s*:\s*'([A-Z][^']{2,40})'/g

  function verstoesse(dateien) {
    const raus = []
    for (const datei of dateien) {
      const rel = relative(srcVerzeichnis, datei)
      // Testdateien sieht kein Nutzer. Die Ausnahme haengt am DATEINAMEN,
      // nicht am Verzeichnis: Komponententests liegen neben ihrer
      // Komponente (src/contexts/AuthContext.test.jsx), und eine
      // Verzeichnisregel haette sie uebersehen.
      if (rel.startsWith('test/') || /\.(test|spec)\.jsx?$/.test(rel)) continue
      if (rel === UNERREICHBAR) continue
      const zeilen = readFileSync(datei, 'utf8').split('\n')
      zeilen.forEach((zeile, i) => {
        for (const treffer of zeile.matchAll(beschriftung)) {
          if (EIGENNAMEN.has(treffer[2])) continue
          raus.push(`${rel}:${i + 1}  ${treffer[1]}: '${treffer[2]}'`)
        }
      })
    }
    return raus
  }

  const jsxDateien = dateienRekursiv(srcVerzeichnis, ['.jsx'])

  it('findet überhaupt Quelldateien', () => {
    expect(jsxDateien.length).toBeGreaterThan(20)
  })

  it('keine Komponente trägt eine feste Beschriftung im Quelltext', () => {
    expect(verstoesse(jsxDateien)).toEqual([])
  })

  it('Positivkontrolle: der Scanner erkennt einen künstlichen Verstoß', () => {
    const kuenstlich = "  { name: 'Transcription', href: '/transcribe' },"
    expect([...kuenstlich.matchAll(beschriftung)].length).toBe(1)
  })

  it('Gegenkontrolle: ein t()-Aufruf löst NICHT aus', () => {
    const sauber = "  { name: t('nav:transcribe'), href: '/transcribe' },"
    expect([...sauber.matchAll(beschriftung)].length).toBe(0)
  })

  it('die Ausnahme für Home.jsx gilt nur, solange die Seite unerreichbar ist', () => {
    const app = readFileSync(join(srcVerzeichnis, 'App.jsx'), 'utf8')
    // Wird Home je angeschlossen, muss die Ausnahme oben verschwinden.
    expect(app).toMatch(/<Route index element=\{<Navigate to="\/trips" replace \/>\} \/>/)
  })
})
