import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import resourcesToBackend from 'i18next-resources-to-backend'
import { initReactI18next } from 'react-i18next'

/**
 * Übersetzungen werden NACHGELADEN, nicht mitgeliefert.
 *
 * Bis 2026-08-25 standen hier 112 statische Importe — alle vier Sprachen mal
 * 28 Namensräume landeten dadurch im Hauptbündel. Gemessen: 143,9 KiB von
 * 227,0 KiB, also **63 % des Bündels**, das jeder Besucher lädt, bevor er
 * überhaupt weiß, welche Sprache er spricht.
 *
 * `import()` erzeugt pro Sprache und Namensraum einen eigenen Chunk, den Vite
 * getrennt ausliefert. Geladen wird nur, was die erkannte Sprache braucht.
 */

export const namespaces = [
  'common',
  'interests',
  'nav',
  'auth',
  'trips',
  'diary',
  'notifications',
  'gallery',
  'analytics',
  'places',
  'ai',
  'settings',
  'budget',
  'timeline',
  'errors',
  'success',
  'home',
  'tripDetail',
  'map',
  'routes',
  'recommendations',
  'placeLists',
  'profile',
  'admin',
  'offline',
  'transcribe',
  'notFound',
  'format',
]

export const languages = [
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
]

const unterstuetzt = languages.map((l) => l.code)

export const uebersetzungenBereit = i18n
  .use(
    resourcesToBackend((sprache, namensraum) => {
      // Vite kann diesen Ausdruck statisch auflösen, weil das Muster
      // buchstäblich dasteht — daraus wird pro Datei ein eigener Chunk.
      // Eine zusammengebaute Zeichenkette könnte es NICHT auflösen; dann
      // landete wieder alles im Hauptbündel oder gar nichts.
      return import(`./locales/${sprache}/${namensraum}.json`)
    })
  )
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',

    // KEIN festes `lng` hier.
    //
    // Bis 2026-08-25 stand hier `lng: 'en'`. Sobald i18next eine feste Sprache
    // bekommt, übergeht es den LanguageDetector vollständig — der war also
    // konfiguriert und ohne jede Wirkung. Folge: JEDER Nutzer sah Englisch,
    // auch bei `navigator.languages = ['de-DE','de',…]`.
    //
    // supportedLngs + load:'languageOnly' sorgen dafür, dass 'de-DE' auf 'de'
    // fällt statt auf den Fallback.
    supportedLngs: unterstuetzt,
    load: 'languageOnly',
    debug: false,

    defaultNS: 'common',
    ns: namespaces,
    partialBundledLanguages: true,

    interpolation: {
      escapeValue: false,
    },

    react: {
      // Ohne Suspense: die Anwendung rendert sofort und füllt die Texte nach.
      // Mit Suspense hinge der erste Bildschirm an den Übersetzungen, und ein
      // fehlgeschlagener Chunk führte zu einer weißen Seite statt zu
      // englischem Text.
      useSuspense: false,
    },

    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      lookupLocalStorage: 'i18nextLng',
      caches: ['localStorage'],
    },
  })

/**
 * `<html lang>` an die tatsächliche Sprache binden.
 *
 * In index.html stand fest `lang="de"`, und niemand hat es je aktualisiert. Am
 * 2026-08-25 in der Produktion gemessen: die Oberfläche stand auf Spanisch,
 * das Attribut weiter auf 'de'. Vorlesesoftware wählt danach ihre Aussprache.
 */
const spracheAmDokumentSetzen = (sprache) => {
  const nurSprache = String(sprache || 'en').split('-')[0]
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', nurSprache)
  }
}

spracheAmDokumentSetzen(i18n.resolvedLanguage || i18n.language)
i18n.on('languageChanged', spracheAmDokumentSetzen)

export default i18n
