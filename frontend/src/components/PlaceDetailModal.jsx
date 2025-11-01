import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, MapPin, Star, Clock, Phone, Globe, ExternalLink,
  Calendar, DollarSign, Info, MessageSquare, Image as ImageIcon,
  Plus
} from 'lucide-react'
import { clsx } from 'clsx'
import { useTranslation } from 'react-i18next'

export default function PlaceDetailModal({ place, isOpen, onClose, onAddToTrip }) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState('about')

  const TABS = [
    { id: 'about', labelKey: 'places.tabAbout', icon: Info },
    { id: 'photos', labelKey: 'places.tabPhotos', icon: ImageIcon },
  ]

  if (!isOpen || !place) return null

  const hasExternalLinks = place.external_links && Object.keys(place.external_links).length > 0

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-40"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-4 md:inset-auto md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-full md:max-w-2xl md:max-h-[90vh] bg-white dark:bg-gray-800 rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
          >
            {/* Header Image */}
            {place.image_url && (
              <div className="relative h-48 bg-gray-200 dark:bg-gray-700 flex-shrink-0">
                <img
                  src={place.image_url}
                  alt={place.name}
                  className="w-full h-full object-cover"
                />
                <button
                  onClick={onClose}
                  className="absolute top-4 right-4 p-2 bg-white/90 hover:bg-white dark:bg-gray-900/90 dark:hover:bg-gray-900 rounded-full transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            )}

            {/* Close button if no image */}
            {!place.image_url && (
              <button
                onClick={onClose}
                className="absolute top-4 right-4 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors z-10"
              >
                <X className="w-5 h-5" />
              </button>
            )}

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              <div className="p-6">
                {/* Title and Rating */}
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <h2 className="text-2xl font-bold mb-2">{place.name}</h2>
                    {place.category && (
                      <span className="inline-block px-3 py-1 bg-primary-100 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300 rounded-full text-sm font-medium">
                        {place.category}
                      </span>
                    )}
                  </div>
                  {(place.external_rating || place.rating) && (
                    <div className="flex items-center gap-2 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 rounded-lg">
                      <Star className="w-5 h-5 text-amber-500 fill-current" />
                      <div>
                        <div className="font-bold text-lg text-amber-700 dark:text-amber-400">
                          {place.external_rating || place.rating}
                        </div>
                        {place.external_reviews_count && (
                          <div className="text-xs text-amber-600 dark:text-amber-500">
                            ({place.external_reviews_count.toLocaleString()})
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Tabs */}
                <div className="border-b border-gray-200 dark:border-gray-700 mb-4">
                  <nav className="flex gap-4">
                    {TABS.map((tab) => {
                      const Icon = tab.icon
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={clsx(
                            'flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors',
                            activeTab === tab.id
                              ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                              : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                          )}
                        >
                          <Icon className="w-4 h-4" />
                          {t(tab.labelKey)}
                        </button>
                      )
                    })}
                  </nav>
                </div>

                {/* About Tab */}
                {activeTab === 'about' && (
                  <div className="space-y-4">
                    {/* Description */}
                    {place.description && (
                      <div>
                        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                          {place.description}
                        </p>
                      </div>
                    )}

                    {/* Info Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {place.address && (
                        <div className="flex items-start gap-3">
                          <MapPin className="w-5 h-5 text-gray-600 dark:text-gray-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                              {t('places.addressField')}
                            </div>
                            <div className="text-sm">{place.address}</div>
                          </div>
                        </div>
                      )}

                      {place.opening_hours && (
                        <div className="flex items-start gap-3">
                          <Clock className="w-5 h-5 text-gray-600 dark:text-gray-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                              {t('places.openingHours')}
                            </div>
                            <div className="text-sm whitespace-pre-line">{place.opening_hours}</div>
                          </div>
                        </div>
                      )}

                      {place.phone && (
                        <div className="flex items-start gap-3">
                          <Phone className="w-5 h-5 text-gray-600 dark:text-gray-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                              {t('places.phoneField')}
                            </div>
                            <a
                              href={`tel:${place.phone}`}
                              className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
                            >
                              {place.phone}
                            </a>
                          </div>
                        </div>
                      )}

                      {place.website && (
                        <div className="flex items-start gap-3">
                          <Globe className="w-5 h-5 text-gray-600 dark:text-gray-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                              {t('places.websiteField')}
                            </div>
                            <a
                              href={place.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
                            >
                              {t('places.visitWebsite')}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        </div>
                      )}

                      {place.cost && (
                        <div className="flex items-start gap-3">
                          <DollarSign className="w-5 h-5 text-gray-600 dark:text-gray-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                              {t('places.costField')}
                            </div>
                            <div className="text-sm">
                              {place.cost} {place.currency || 'EUR'}
                            </div>
                          </div>
                        </div>
                      )}

                      {place.visit_date && (
                        <div className="flex items-start gap-3">
                          <Calendar className="w-5 h-5 text-gray-600 dark:text-gray-400 flex-shrink-0 mt-0.5" />
                          <div>
                            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
                              {t('places.visitDateField')}
                            </div>
                            <div className="text-sm">
                              {new Date(place.visit_date).toLocaleDateString('de-DE', {
                                weekday: 'long',
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric'
                              })}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* External Links */}
                    {hasExternalLinks && (
                      <div>
                        <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
                          {t('places.openIn')}
                        </h3>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(place.external_links).map(([service, url]) => (
                            <a
                              key={service}
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-2 px-3 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg text-sm font-medium transition-colors"
                            >
                              {service}
                              <ExternalLink className="w-4 h-4" />
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Notes */}
                    {place.notes && (
                      <div className="bg-primary-50 dark:bg-primary-900/20 p-4 rounded-lg">
                        <div className="text-sm font-medium text-primary-900 dark:text-primary-100 mb-1">
                          💡 {t('places.notesField')}
                        </div>
                        <p className="text-sm text-primary-800 dark:text-primary-200">
                          {place.notes}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Photos Tab */}
                {activeTab === 'photos' && (
                  <div>
                    {place.photos && place.photos.length > 0 ? (
                      <div className="grid grid-cols-2 gap-4">
                        {place.photos.map((photo, index) => (
                          <img
                            key={index}
                            src={photo}
                            alt={t('places.photoAlt').replace('{name}', place.name).replace('{index}', index + 1)}
                            className="w-full h-48 object-cover rounded-lg"
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-12">
                        <ImageIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                        <p className="text-gray-600 dark:text-gray-400">
                          {t('places.noPhotosYet')}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Footer with Action Button */}
            {onAddToTrip && (
              <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
                <button
                  onClick={() => {
                    onAddToTrip(place)
                    onClose()
                  }}
                  className="w-full btn-primary flex items-center justify-center gap-2"
                >
                  <Plus className="w-5 h-5" />
                  {t('places.addToTrip')}
                </button>
              </div>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
