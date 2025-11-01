import { MapPin, Star, Check, Calendar, DollarSign, Edit, Trash2, ExternalLink } from 'lucide-react'
import { motion } from 'framer-motion'
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
  sight: '🏛️',
  activity: '⚡',
  transport: '🚗',
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
  sight: 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300',
  activity: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300',
  transport: 'bg-gray-100 text-gray-700 dark:bg-gray-900/20 dark:text-gray-300',
  other: 'bg-gray-100 text-gray-700 dark:bg-gray-900/20 dark:text-gray-300'
}

// Generate a placeholder image URL from Unsplash based on category
const getPlaceholderImage = (category, name) => {
  const categoryKeywords = {
    restaurant: 'food,restaurant',
    attraction: 'landmark,tourist',
    beach: 'beach,ocean',
    hotel: 'hotel,resort',
    viewpoint: 'mountain,landscape',
    museum: 'museum,art',
    park: 'park,nature',
    shopping: 'shopping,market',
    nightlife: 'nightlife,city',
    sight: 'landmark,monument',
    activity: 'adventure,outdoor',
    transport: 'transportation,travel',
    other: 'travel,destination'
  }
  const keywords = categoryKeywords[category] || 'travel'
  return `https://source.unsplash.com/400x300/?${keywords}`
}

export default function PlaceCard({ place, onEdit, onDelete, onToggleVisited, onClick }) {
  const { t } = useTranslation()
  const categoryClass = CATEGORY_COLORS[place.category] || CATEGORY_COLORS.other

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={() => onClick && onClick(place)}
      className={`group relative flex gap-3 p-3 bg-white dark:bg-gray-800 border rounded-xl transition-all hover:shadow-md ${
        place.visited
          ? 'border-green-500 ring-2 ring-green-200 dark:ring-green-800 opacity-90'
          : 'border-gray-200 dark:border-gray-700 hover:border-primary-300'
      } ${onClick ? 'cursor-pointer' : ''}`}
    >
      {/* Visited Checkbox */}
      <div className="flex-shrink-0 pt-1">
        <button
          onClick={(e) => {
            e.stopPropagation()
            onToggleVisited(place.id, !place.visited)
          }}
          className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
            place.visited
              ? 'bg-green-500 border-green-500 text-white'
              : 'border-gray-300 dark:border-gray-600 hover:border-green-500'
          }`}
        >
          {place.visited && <Check className="w-4 h-4" />}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2 mb-1">
          <h3 className={`font-semibold text-base truncate ${place.visited ? 'line-through opacity-75' : ''}`}>
            {place.name}
          </h3>
          {(place.rating || place.external_rating) && (
            <div className="flex items-center gap-1 text-sm text-amber-600 dark:text-amber-400 flex-shrink-0">
              <Star className="w-4 h-4 fill-current" />
              <span className="font-medium">{place.external_rating || place.rating}</span>
            </div>
          )}
        </div>

        {place.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-2">
            {place.description}
          </p>
        )}

        {/* Tags & Info */}
        <div className="flex flex-wrap gap-2 mb-2">
          {place.category && (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${categoryClass}`}>
              <span>{CATEGORY_ICONS[place.category] || '📍'}</span>
              {place.category}
            </span>
          )}
          {place.visit_date && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300 rounded-full text-xs font-medium">
              <Calendar className="w-3 h-3" />
              {new Date(place.visit_date).toLocaleDateString('de-DE', {
                day: '2-digit',
                month: 'short'
              })}
            </span>
          )}
          {place.cost && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300 rounded-full text-xs font-medium">
              <DollarSign className="w-3 h-3" />
              {place.cost} {place.currency}
            </span>
          )}
        </div>

        {/* Address */}
        {place.address && (
          <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
            <MapPin className="w-3 h-3" />
            <span className="truncate">{place.address}</span>
          </div>
        )}

        {/* Notes - Only show if present */}
        {place.notes && (
          <div className="mt-2 text-xs text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 px-2 py-1 rounded inline-block">
            💡 {place.notes}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex-shrink-0 flex flex-col gap-2">
        {place.website && (
          <a
            href={place.website}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="p-2 text-gray-600 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title={t('places.openWebsite')}
          >
            <ExternalLink className="w-5 h-5" />
          </a>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation()
            onEdit(place)
          }}
          className="p-2 text-gray-600 hover:text-primary-600 dark:text-gray-400 dark:hover:text-primary-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          title={t('places.editPlace')}
        >
          <Edit className="w-5 h-5" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(place.id)
          }}
          className="p-2 text-gray-600 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/20 transition-colors"
          title={t('places.deletePlace')}
        >
          <Trash2 className="w-5 h-5" />
        </button>
      </div>
    </motion.div>
  )
}
