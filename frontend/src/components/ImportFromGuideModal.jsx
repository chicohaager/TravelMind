import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Link as LinkIcon, Search, CheckCircle, Circle, Loader, AlertCircle,
  MapPin, Globe, Info
} from 'lucide-react'
import { placesService } from '@/services/api'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'

const CATEGORY_ICONS = {
  restaurant: '🍽️',
  attraction: '🎯',
  beach: '🏖️',
  hotel: '🏨',
  viewpoint: '👁️',
  museum: '🏛️',
  park: '🌳',
  shopping: '🛍️',
  nightlife: '🎉',
  other: '📍'
}

export default function ImportFromGuideModal({ isOpen, onClose, tripId, destination, onImportComplete }) {
  const { t } = useTranslation()
  const [searchDestination, setSearchDestination] = useState(destination || '')
  const [loading, setLoading] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [importing, setImporting] = useState(false)
  const [extractedPlaces, setExtractedPlaces] = useState([])
  const [selectedPlaces, setSelectedPlaces] = useState(new Set())
  const [error, setError] = useState('')
  const [sourcesSearched, setSourcesSearched] = useState([])

  const handleSearch = async () => {
    if (!searchDestination.trim()) {
      setError(t('places:pleaseEnterDestination'))
      return
    }

    setParsing(true)
    setError('')
    setExtractedPlaces([])
    setSelectedPlaces(new Set())
    setSourcesSearched([])

    try {
      const response = await placesService.searchGuides(tripId, searchDestination)

      if (response.data.success) {
        setExtractedPlaces(response.data.places)
        setSourcesSearched(response.data.sources_searched || [])
        // Auto-select all places
        setSelectedPlaces(new Set(response.data.places.map((_, i) => i)))

        if (response.data.places.length === 0) {
          toast(t('places:noPlacesFound'), { icon: '🤷' })
        } else {
          const sourceText = response.data.sources_searched?.length
            ? ` ${t('places:from')} ${response.data.sources_searched.join(', ')}`
            : ''
          toast.success(t('places:placesFound', { count: response.data.places.length }) + sourceText + '!')
        }
      } else {
        setError(response.data.error || t('places:errorSearching'))
        toast.error(t('places:errorLoadingPlaces'))
      }
    } catch (err) {
      const message = err.response?.data?.detail || t('places:errorLoading')
      setError(message)
      toast.error(message)
    } finally {
      setParsing(false)
    }
  }

  const togglePlace = (index) => {
    const newSelected = new Set(selectedPlaces)
    if (newSelected.has(index)) {
      newSelected.delete(index)
    } else {
      newSelected.add(index)
    }
    setSelectedPlaces(newSelected)
  }

  const toggleAll = () => {
    if (selectedPlaces.size === extractedPlaces.length) {
      setSelectedPlaces(new Set())
    } else {
      setSelectedPlaces(new Set(extractedPlaces.map((_, i) => i)))
    }
  }

  const handleImport = async () => {
    if (selectedPlaces.size === 0) {
      toast.error(t('places:selectAtLeastOne'))
      return
    }

    setImporting(true)

    try {
      // Convert extracted places to PlaceCreate format
      const placesToImport = Array.from(selectedPlaces).map(index => {
        const place = extractedPlaces[index]
        return {
          name: place.name,
          description: place.description || '',
          address: place.address || null,
          latitude: place.latitude || 0,
          longitude: place.longitude || 0,
          category: place.category || 'other',
          visit_date: null,
          visited: false,
          website: null,
          phone: null,
          cost: null,
          currency: 'EUR',
          rating: null,
          notes: null,
          photos: []
        }
      })

      await placesService.importPlacesBulk(tripId, placesToImport)

      toast.success(t('places:placesImported').replace('{count}', selectedPlaces.size))
      onImportComplete?.()
      handleClose()
    } catch (err) {
      const message = err.response?.data?.detail || t('places:errorImporting')
      toast.error(message)
    } finally {
      setImporting(false)
    }
  }

  const handleClose = () => {
    setSearchDestination(destination || '')
    setExtractedPlaces([])
    setSelectedPlaces(new Set())
    setError('')
    setParsing(false)
    setImporting(false)
    setSourcesSearched([])
    onClose()
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col relative"
        >
          {/* Header */}
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold flex items-center gap-2">
                  <Globe className="w-6 h-6 text-primary-600" />
                  {t('places:importGuideTitle')}
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  {t('places:importGuideSubtitle')}
                </p>
              </div>
              <button
                onClick={handleClose}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content - Scrollable */}
          <div className="flex-1 overflow-y-auto p-6" style={{ minHeight: 0 }}>
            {/* Destination Search */}
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">
                {t('places:destinationLabel')}
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    value={searchDestination}
                    onChange={(e) => setSearchDestination(e.target.value)}
                    placeholder={t('places:destinationPlaceholder')}
                    className="input pl-10 w-full"
                    disabled={parsing || importing}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  />
                </div>
                <button
                  onClick={handleSearch}
                  disabled={parsing || importing || !searchDestination.trim()}
                  className="btn-primary flex items-center gap-2 px-6"
                >
                  {parsing ? (
                    <>
                      <Loader className="w-5 h-5 animate-spin" />
                      {t('places:searching')}
                    </>
                  ) : (
                    <>
                      <Search className="w-5 h-5" />
                      {t('places:searchButton')}
                    </>
                  )}
                </button>
              </div>

              {error && (
                <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                </div>
              )}

              {/* Info Box */}
              <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <div className="flex items-start gap-2">
                  <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-blue-600 dark:text-blue-400">
                    <p className="font-medium mb-1">{t('places:howItWorks')}</p>
                    <ul className="list-disc list-inside space-y-0.5 text-xs">
                      <li>{t('places:howItWorksStep1')}</li>
                      <li>{t('places:howItWorksStep2')}</li>
                      <li>{t('places:howItWorksStep3')}</li>
                      <li>{t('places:howItWorksStep4')}</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Sources Searched */}
              {sourcesSearched.length > 0 && (
                <div className="mt-3 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <Globe className="w-4 h-4" />
                  <span>{t('places:sourcesSearched')} {sourcesSearched.join(', ')}</span>
                </div>
              )}
            </div>

            {/* Extracted Places */}
            {extractedPlaces.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">
                    {t('places:foundPlaces').replace('{count}', extractedPlaces.length)}
                  </h3>
                  <button
                    onClick={toggleAll}
                    className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                  >
                    {selectedPlaces.size === extractedPlaces.length ? t('places:deselectAll') : t('places:selectAll')}
                  </button>
                </div>

                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {extractedPlaces.map((place, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      onClick={() => togglePlace(index)}
                      className={`p-4 rounded-lg border-2 transition-all cursor-pointer ${
                        selectedPlaces.has(index)
                          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">
                          {selectedPlaces.has(index) ? (
                            <CheckCircle className="w-5 h-5 text-primary-600" />
                          ) : (
                            <Circle className="w-5 h-5 text-gray-400" />
                          )}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-start gap-2">
                            <span className="text-xl">{CATEGORY_ICONS[place.category] || '📍'}</span>
                            <div className="flex-1">
                              <h4 className="font-semibold">{place.name}</h4>
                              {place.description && (
                                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                                  {place.description}
                                </p>
                              )}
                              {place.address && (
                                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1 flex items-center gap-1">
                                  <MapPin className="w-3 h-3" />
                                  {place.address}
                                </p>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-2 mt-2">
                            <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs font-medium">
                              {place.category}
                            </span>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

            {parsing && (
              <div className="text-center py-12">
                <Loader className="w-12 h-12 animate-spin mx-auto text-primary-600" />
                <p className="mt-4 text-gray-600 dark:text-gray-400">
                  {t('places:searchingGuides')}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                  {t('places:searchingGuidesInfo')}
                </p>
              </div>
            )}
          </div>

          {/* Footer - Fixed at Bottom */}
          {extractedPlaces.length > 0 && (
            <div className="flex-shrink-0 p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {t('places:selectedCountPrefix')} <strong>{selectedPlaces.size}</strong> {t('places:selectedCountMiddle')} <strong>{extractedPlaces.length}</strong> {t('places:selectedCountSuffix')}
                </p>

                <div className="flex gap-2">
                  <button
                    onClick={handleClose}
                    className="btn-outline"
                    disabled={importing}
                  >
                    {t('common:cancel')}
                  </button>
                  <button
                    onClick={handleImport}
                    disabled={selectedPlaces.size === 0 || importing}
                    className="btn-primary flex items-center gap-2"
                  >
                    {importing ? (
                      <>
                        <Loader className="w-5 h-5 animate-spin" />
                        {t('places:importing')}
                      </>
                    ) : (
                      <>
                        <CheckCircle className="w-5 h-5" />
                        {t('places:importButton').replace('{count}', selectedPlaces.size)}
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
