import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

// English namespaces
import enCommon from './locales/en/common.json'
import enInterests from './locales/en/interests.json'
import enNav from './locales/en/nav.json'
import enAuth from './locales/en/auth.json'
import enTrips from './locales/en/trips.json'
import enDiary from './locales/en/diary.json'
import enPlaces from './locales/en/places.json'
import enAi from './locales/en/ai.json'
import enSettings from './locales/en/settings.json'
import enBudget from './locales/en/budget.json'
import enTimeline from './locales/en/timeline.json'
import enErrors from './locales/en/errors.json'
import enSuccess from './locales/en/success.json'
import enHome from './locales/en/home.json'
import enTripDetail from './locales/en/tripDetail.json'
import enMap from './locales/en/map.json'
import enRoutes from './locales/en/routes.json'
import enRecommendations from './locales/en/recommendations.json'
import enPlaceLists from './locales/en/placeLists.json'
import enProfile from './locales/en/profile.json'
import enAdmin from './locales/en/admin.json'
import enOffline from './locales/en/offline.json'
import enTranscribe from './locales/en/transcribe.json'
import enNotFound from './locales/en/notFound.json'
import enFormat from './locales/en/format.json'

// German namespaces
import deCommon from './locales/de/common.json'
import deInterests from './locales/de/interests.json'
import deNav from './locales/de/nav.json'
import deAuth from './locales/de/auth.json'
import deTrips from './locales/de/trips.json'
import deDiary from './locales/de/diary.json'
import dePlaces from './locales/de/places.json'
import deAi from './locales/de/ai.json'
import deSettings from './locales/de/settings.json'
import deBudget from './locales/de/budget.json'
import deTimeline from './locales/de/timeline.json'
import deErrors from './locales/de/errors.json'
import deSuccess from './locales/de/success.json'
import deHome from './locales/de/home.json'
import deTripDetail from './locales/de/tripDetail.json'
import deMap from './locales/de/map.json'
import deRoutes from './locales/de/routes.json'
import deRecommendations from './locales/de/recommendations.json'
import dePlaceLists from './locales/de/placeLists.json'
import deProfile from './locales/de/profile.json'
import deAdmin from './locales/de/admin.json'
import deOffline from './locales/de/offline.json'
import deTranscribe from './locales/de/transcribe.json'
import deNotFound from './locales/de/notFound.json'
import deFormat from './locales/de/format.json'

// French namespaces
import frCommon from './locales/fr/common.json'
import frInterests from './locales/fr/interests.json'
import frNav from './locales/fr/nav.json'
import frAuth from './locales/fr/auth.json'
import frTrips from './locales/fr/trips.json'
import frDiary from './locales/fr/diary.json'
import frPlaces from './locales/fr/places.json'
import frAi from './locales/fr/ai.json'
import frSettings from './locales/fr/settings.json'
import frBudget from './locales/fr/budget.json'
import frTimeline from './locales/fr/timeline.json'
import frErrors from './locales/fr/errors.json'
import frSuccess from './locales/fr/success.json'
import frHome from './locales/fr/home.json'
import frTripDetail from './locales/fr/tripDetail.json'
import frMap from './locales/fr/map.json'
import frRoutes from './locales/fr/routes.json'
import frRecommendations from './locales/fr/recommendations.json'
import frPlaceLists from './locales/fr/placeLists.json'
import frProfile from './locales/fr/profile.json'
import frAdmin from './locales/fr/admin.json'
import frOffline from './locales/fr/offline.json'
import frTranscribe from './locales/fr/transcribe.json'
import frNotFound from './locales/fr/notFound.json'
import frFormat from './locales/fr/format.json'

// Spanish namespaces
import esCommon from './locales/es/common.json'
import esInterests from './locales/es/interests.json'
import esNav from './locales/es/nav.json'
import esAuth from './locales/es/auth.json'
import esTrips from './locales/es/trips.json'
import esDiary from './locales/es/diary.json'
import esPlaces from './locales/es/places.json'
import esAi from './locales/es/ai.json'
import esSettings from './locales/es/settings.json'
import esBudget from './locales/es/budget.json'
import esTimeline from './locales/es/timeline.json'
import esErrors from './locales/es/errors.json'
import esSuccess from './locales/es/success.json'
import esHome from './locales/es/home.json'
import esTripDetail from './locales/es/tripDetail.json'
import esMap from './locales/es/map.json'
import esRoutes from './locales/es/routes.json'
import esRecommendations from './locales/es/recommendations.json'
import esPlaceLists from './locales/es/placeLists.json'
import esProfile from './locales/es/profile.json'
import esAdmin from './locales/es/admin.json'
import esOffline from './locales/es/offline.json'
import esTranscribe from './locales/es/transcribe.json'
import esNotFound from './locales/es/notFound.json'
import esFormat from './locales/es/format.json'

// All available namespaces
export const namespaces = [
  'common',
  'interests',
  'nav',
  'auth',
  'trips',
  'diary',
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
  'format'
]

// Available languages
export const languages = [
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'es', name: 'Español', flag: '🇪🇸' }
]

const resources = {
  en: {
    common: enCommon,
    interests: enInterests,
    nav: enNav,
    auth: enAuth,
    trips: enTrips,
    diary: enDiary,
    places: enPlaces,
    ai: enAi,
    settings: enSettings,
    budget: enBudget,
    timeline: enTimeline,
    errors: enErrors,
    success: enSuccess,
    home: enHome,
    tripDetail: enTripDetail,
    map: enMap,
    routes: enRoutes,
    recommendations: enRecommendations,
    placeLists: enPlaceLists,
    profile: enProfile,
    admin: enAdmin,
    offline: enOffline,
    transcribe: enTranscribe,
    notFound: enNotFound,
    format: enFormat
  },
  de: {
    common: deCommon,
    interests: deInterests,
    nav: deNav,
    auth: deAuth,
    trips: deTrips,
    diary: deDiary,
    places: dePlaces,
    ai: deAi,
    settings: deSettings,
    budget: deBudget,
    timeline: deTimeline,
    errors: deErrors,
    success: deSuccess,
    home: deHome,
    tripDetail: deTripDetail,
    map: deMap,
    routes: deRoutes,
    recommendations: deRecommendations,
    placeLists: dePlaceLists,
    profile: deProfile,
    admin: deAdmin,
    offline: deOffline,
    transcribe: deTranscribe,
    notFound: deNotFound,
    format: deFormat
  },
  fr: {
    common: frCommon,
    interests: frInterests,
    nav: frNav,
    auth: frAuth,
    trips: frTrips,
    diary: frDiary,
    places: frPlaces,
    ai: frAi,
    settings: frSettings,
    budget: frBudget,
    timeline: frTimeline,
    errors: frErrors,
    success: frSuccess,
    home: frHome,
    tripDetail: frTripDetail,
    map: frMap,
    routes: frRoutes,
    recommendations: frRecommendations,
    placeLists: frPlaceLists,
    profile: frProfile,
    admin: frAdmin,
    offline: frOffline,
    transcribe: frTranscribe,
    notFound: frNotFound,
    format: frFormat
  },
  es: {
    common: esCommon,
    interests: esInterests,
    nav: esNav,
    auth: esAuth,
    trips: esTrips,
    diary: esDiary,
    places: esPlaces,
    ai: esAi,
    settings: esSettings,
    budget: esBudget,
    timeline: esTimeline,
    errors: esErrors,
    success: esSuccess,
    home: esHome,
    tripDetail: esTripDetail,
    map: esMap,
    routes: esRoutes,
    recommendations: esRecommendations,
    placeLists: esPlaceLists,
    profile: esProfile,
    admin: esAdmin,
    offline: esOffline,
    transcribe: esTranscribe,
    notFound: esNotFound,
    format: esFormat
  }
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    lng: 'en',
    debug: false,

    // Default namespace
    defaultNS: 'common',

    // Namespaces to load
    ns: namespaces,

    interpolation: {
      escapeValue: false
    },

    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      lookupLocalStorage: 'i18nextLng',
      caches: ['localStorage'],
    }
  })

export default i18n
