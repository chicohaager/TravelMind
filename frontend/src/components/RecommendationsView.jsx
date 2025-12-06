import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles, MapPin, Clock, DollarSign, Plus, Loader,
  AlertCircle, RefreshCw, CheckCircle, Info, Star, ExternalLink
} from 'lucide-react'
import { aiService, placesService } from '@/services/api'
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

const CATEGORY_COLORS = {
  restaurant: 'bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-300',
  attraction: 'bg-purple-100 text-purple-700 dark:bg-purple-900/20 dark:text-purple-300',
  beach: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/20 dark:text-cyan-300',
  hotel: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/20 dark:text-indigo-300',
  viewpoint: 'bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300',
  museum: 'bg-slate-100 text-slate-700 dark:bg-slate-900/20 dark:text-slate-300',
  park: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300',
  shopping: 'bg-pink-100 text-pink-700 dark:bg-pink-900/20 dark:text-pink-300',
  nightlife: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/20 dark:text-fuchsia-300',
  other: 'bg-gray-100 text-gray-700 dark:bg-gray-900/20 dark:text-gray-300'
}

// Generate a placeholder image URL based on category
const getPlaceholderImage = (category, name) => {
  // Use Picsum with seeded random images based on name hash
  const seed = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  const imageId = 100 + (seed % 900) // Random ID between 100-999
  return `https://picsum.photos/seed/${imageId}/400/300`
}

export default function RecommendationsView({ tripId, trip, places = [] }) {
  const { t } = useTranslation()
  const [addingPlaceId, setAddingPlaceId] = useState(null)
  const [selectedRecommendations, setSelectedRecommendations] = useState([])
  const [isAddingMultiple, setIsAddingMultiple] = useState(false)

  // Fetch recommendations
  const {
    data: recommendationsData,
    isLoading,
    error,
    refetch,
    isRefetching
  } = useQuery({
    queryKey: ['recommendations', tripId],
    queryFn: async () => {
      const existingPlaceNames = places.map(p => p.name)

      const response = await aiService.getPersonalizedRecommendations({
        destination: trip.destination,
        interests: trip.interests || [],
        existing_places: existingPlaceNames,
        budget: trip.budget,
        duration: trip.start_date && trip.end_date
          ? Math.ceil((new Date(trip.end_date) - new Date(trip.start_date)) / (1000 * 60 * 60 * 24))
          : null,
        currency: trip.currency || 'EUR'
      })

      return response.data
    },
    enabled: !!trip
  })

  const recommendations = recommendationsData?.recommendations || []

  const toggleSelection = (recName) => {
    setSelectedRecommendations(prev =>
      prev.includes(recName)
        ? prev.filter(name => name !== recName)
        : [...prev, recName]
    )
  }

  const toggleSelectAll = () => {
    if (selectedRecommendations.length === recommendations.length) {
      setSelectedRecommendations([])
    } else {
      setSelectedRecommendations(recommendations.map(rec => rec.name))
    }
  }

  const handleAddSelectedPlaces = async () => {
    if (selectedRecommendations.length === 0) {
      toast.error(t('recommendations:noRecommendationsSelected'))
      return
    }

    setIsAddingMultiple(true)

    try {
      const selectedRecs = recommendations.filter(rec => selectedRecommendations.includes(rec.name))

      for (const rec of selectedRecs) {
        await placesService.create(tripId, {
          name: rec.name,
          description: rec.description,
          category: rec.category,
          latitude: 0,
          longitude: 0,
          visited: false,
          cost: rec.estimated_cost,
          currency: trip.currency || 'EUR',
          notes: `${t('recommendations:aiRecommendation')}: ${rec.reason}`,
          image_url: getPlaceholderImage(rec.category, rec.name),
          tags: [rec.category],
          photos: []
        })
      }

      toast.success(t('recommendations:recommendationsAdded', { count: selectedRecommendations.length }))
      setSelectedRecommendations([])
      setTimeout(() => refetch(), 500)
    } catch (err) {
      toast.error(t('recommendations:errorAdding'))
    } finally {
      setIsAddingMultiple(false)
    }
  }

  const handleAddPlace = async (recommendation) => {
    setAddingPlaceId(recommendation.name)

    try {
      await placesService.create(tripId, {
        name: recommendation.name,
        description: recommendation.description,
        category: recommendation.category,
        latitude: 0,
        longitude: 0,
        visited: false,
        cost: recommendation.estimated_cost,
        currency: trip.currency || 'EUR',
        notes: `${t('recommendations:aiRecommendation')}: ${recommendation.reason}`,
        image_url: getPlaceholderImage(recommendation.category, recommendation.name),
        tags: [recommendation.category],
        photos: []
      })

      toast.success(t('recommendations:placeAdded', { name: recommendation.name }))
      setTimeout(() => refetch(), 500)
    } catch (err) {
      toast.error(t('recommendations:errorAdding'))
    } finally {
      setAddingPlaceId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader className="w-12 h-12 animate-spin mx-auto text-primary-600 mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              {t('recommendations:analyzingTrip')}
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">{t('recommendations:errorLoading')}</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {t('recommendations:recommendationsCouldNotBeLoaded')}
            </p>
            <button onClick={() => refetch()} className="btn-primary">
              {t('recommendations:tryAgain')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2 mb-2">
              <Sparkles className="w-6 h-6 text-primary-600" />
              {t('recommendations:personalizedRecommendations')}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t('recommendations:basedOnInterests')}
            </p>
          </div>
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="btn-outline btn-sm flex items-center gap-2 rounded-full"
          >
            <RefreshCw className={`w-4 h-4 ${isRefetching ? 'animate-spin' : ''}`} />
            {t('recommendations:refresh')}
          </button>
        </div>

        {/* Selection Controls */}
        {recommendations.length > 0 && (
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={toggleSelectAll}
              className="btn-outline btn-sm flex items-center gap-2 rounded-full"
            >
              <CheckCircle className="w-4 h-4" />
              {selectedRecommendations.length === recommendations.length ? t('recommendations:deselectAll') : t('recommendations:selectAll')}
            </button>

            {selectedRecommendations.length > 0 && (
              <button
                onClick={handleAddSelectedPlaces}
                disabled={isAddingMultiple}
                className="btn-primary btn-sm flex items-center gap-2 rounded-full"
              >
                {isAddingMultiple ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    {t('recommendations:addingCount', { count: selectedRecommendations.length })}
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    {t('recommendations:addSelectedCount', { count: selectedRecommendations.length })}
                  </>
                )}
              </button>
            )}

            {selectedRecommendations.length > 0 && (
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {t('recommendations:selectedOfTotal', { selected: selectedRecommendations.length, total: recommendations.length })}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Recommendations List - Wanderlog Style */}
      {recommendations.length > 0 ? (
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {recommendations.map((rec, index) => (
              <motion.div
                key={rec.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: index * 0.03 }}
                className={`group relative flex gap-3 p-3 bg-white dark:bg-gray-800 border rounded-xl transition-all hover:shadow-md ${
                  selectedRecommendations.includes(rec.name)
                    ? 'border-primary-500 ring-2 ring-primary-200 dark:ring-primary-800'
                    : 'border-gray-200 dark:border-gray-700 hover:border-primary-300'
                }`}
              >
                {/* Checkbox */}
                <div className="flex-shrink-0 pt-1">
                  <input
                    type="checkbox"
                    checked={selectedRecommendations.includes(rec.name)}
                    onChange={() => toggleSelection(rec.name)}
                    className="w-5 h-5 rounded border-2 border-gray-300 text-primary-600 focus:ring-2 focus:ring-primary-500 cursor-pointer"
                  />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <h3 className="font-semibold text-base truncate">{rec.name}</h3>
                    {rec.external_rating && (
                      <div className="flex items-center gap-1 text-sm text-amber-600 dark:text-amber-400 flex-shrink-0">
                        <Star className="w-4 h-4 fill-current" />
                        <span className="font-medium">{rec.external_rating}</span>
                      </div>
                    )}
                  </div>

                  <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-2">
                    {rec.description}
                  </p>

                  {/* Tags & Info */}
                  <div className="flex flex-wrap gap-2 mb-2">
                    {rec.category && (
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLORS[rec.category] || CATEGORY_COLORS.other}`}>
                        <span>{CATEGORY_ICONS[rec.category] || '📍'}</span>
                        {t(`places.categories.${rec.category}`, rec.category)}
                      </span>
                    )}
                    {rec.best_time && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300 rounded-full text-xs font-medium">
                        <Clock className="w-3 h-3" />
                        {rec.best_time}
                      </span>
                    )}
                    {rec.estimated_cost > 0 && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300 rounded-full text-xs font-medium">
                        <DollarSign className="w-3 h-3" />
                        ~{rec.estimated_cost} {trip.currency || 'EUR'}
                      </span>
                    )}
                  </div>

                  {/* Reason */}
                  {rec.reason && (
                    <div className="text-xs text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 px-2 py-1 rounded inline-block">
                      💡 {rec.reason}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex-shrink-0 flex flex-col gap-2">
                  {rec.google_maps_link && (
                    <a
                      href={rec.google_maps_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-gray-600 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      title={t('recommendations:openInGoogleMaps')}
                    >
                      <MapPin className="w-5 h-5" />
                    </a>
                  )}
                  <button
                    onClick={() => handleAddPlace(rec)}
                    disabled={addingPlaceId === rec.name}
                    className="p-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title={t('recommendations:addToTrip')}
                  >
                    {addingPlaceId === rec.name ? (
                      <Loader className="w-5 h-5 animate-spin" />
                    ) : (
                      <Plus className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      ) : (
        <div className="text-center py-12 card">
          <Sparkles className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">{t('recommendations:noRecommendationsAvailable')}</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {t('recommendations:addInterestsAndPlaces')}
          </p>
        </div>
      )}
    </div>
  )
}
