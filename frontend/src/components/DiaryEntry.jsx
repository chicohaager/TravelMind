import { useState } from 'react'
import { Calendar, MapPin, Star, Tag, Smile, Meh, Frown, X, Edit, Trash2 } from 'lucide-react'
import { motion } from 'framer-motion'

const moodIcons = {
  happy: { icon: Smile, color: 'text-green-500', label: 'Glücklich' },
  neutral: { icon: Meh, color: 'text-yellow-500', label: 'Neutral' },
  sad: { icon: Frown, color: 'text-red-500', label: 'Traurig' }
}

export default function DiaryEntry({ entry, onEdit, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const [selectedPhoto, setSelectedPhoto] = useState(null)

  const MoodIcon = entry.mood && moodIcons[entry.mood]?.icon
  const moodColor = entry.mood && moodIcons[entry.mood]?.color

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card hover:shadow-lg transition-shadow"
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h3 className="text-xl font-bold mb-1">{entry.title}</h3>
          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
            {entry.entry_date && (
              <div className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {new Date(entry.entry_date).toLocaleDateString('de-DE', {
                  day: '2-digit',
                  month: 'long',
                  year: 'numeric'
                })}
              </div>
            )}
            {entry.location_name && (
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {entry.location_name}
              </div>
            )}
            {entry.mood && MoodIcon && (
              <div className={`flex items-center gap-1 ${moodColor}`}>
                <MoodIcon className="w-4 h-4" />
              </div>
            )}
            {entry.rating && (
              <div className="flex items-center gap-1">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={`w-4 h-4 ${
                      i < entry.rating
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'text-gray-300 dark:text-gray-600'
                    }`}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => onEdit(entry)}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Bearbeiten"
          >
            <Edit className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(entry.id)}
            className="p-2 hover:bg-red-100 dark:hover:bg-red-900 rounded-lg transition-colors"
            title="Löschen"
          >
            <Trash2 className="w-4 h-4 text-red-600" />
          </button>
        </div>
      </div>

      {/* Tags */}
      {entry.tags && entry.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {entry.tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-full"
            >
              <Tag className="w-3 h-3" />
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Content Preview/Full */}
      <div className={`prose dark:prose-invert max-w-none ${!expanded && 'line-clamp-3'}`}>
        {entry.content.split('\n').map((line, i) => (
          <p key={i} className="mb-2">
            {line}
          </p>
        ))}
      </div>

      {/* Expand Button */}
      {entry.content.length > 200 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-primary-500 hover:text-primary-600 text-sm font-medium mt-2"
        >
          {expanded ? 'Weniger anzeigen' : 'Mehr lesen...'}
        </button>
      )}

      {/* Photos */}
      {entry.photos && entry.photos.length > 0 && (
        <div className="grid grid-cols-3 gap-2 mt-4">
          {entry.photos.map((photo, i) => (
            <div
              key={i}
              onClick={() => setSelectedPhoto(photo)}
              className="cursor-pointer hover:opacity-80 transition-opacity"
            >
              <img
                src={photo}
                alt={`Foto ${i + 1}`}
                className="w-full h-24 object-cover rounded-lg"
              />
            </div>
          ))}
        </div>
      )}

      {/* Photo Lightbox */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedPhoto(null)}
        >
          <button
            onClick={() => setSelectedPhoto(null)}
            className="absolute top-4 right-4 p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
          >
            <X className="w-6 h-6 text-white" />
          </button>
          <img
            src={selectedPhoto}
            alt="Vergrößertes Foto"
            className="max-w-full max-h-full object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </motion.div>
  )
}
