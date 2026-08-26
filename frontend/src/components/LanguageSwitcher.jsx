import { useTranslation } from 'react-i18next'
import { Languages } from 'lucide-react'
import { languages } from '../i18n'

export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation()

  // Ohne Region vergleichen. Seit die Spracherkennung aktiv ist, steht in
  // i18n.language 'de-DE' — ein Vergleich gegen 'de' findet dann keinen
  // Eintrag und die Flagge fiel stumm auf den Globus zurueck.
  const aktuelleSprache = (i18n.resolvedLanguage || i18n.language || 'en').split('-')[0]

  const changeLanguage = (langCode) => {
    i18n.changeLanguage(langCode)
  }

  return (
    <div className="relative group">
      <button
        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        title={t('common:changeLanguage')}
        aria-label={t('common:changeLanguage')}
      >
        <Languages className="w-5 h-5" />
        <span className="text-sm font-medium hidden sm:inline">
          {languages.find((lang) => lang.code === aktuelleSprache)?.flag || '🌐'}
        </span>
      </button>

      {/* Dropdown */}
      <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
        {languages.map((lang) => (
          <button
            key={lang.code}
            onClick={() => changeLanguage(lang.code)}
            className={`w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors first:rounded-t-lg last:rounded-b-lg ${
              i18n.language === lang.code
                ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                : ''
            }`}
          >
            <span className="text-xl">{lang.flag}</span>
            <span className="text-sm font-medium">{lang.name}</span>
            {i18n.language === lang.code && <span className="ml-auto text-primary-500">✓</span>}
          </button>
        ))}
      </div>
    </div>
  )
}
