import { Clock, MapPin, Trash2, GripVertical } from 'lucide-react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

const categoryIcons = {
  sight: '🏛️',
  restaurant: '🍽️',
  hotel: '🏨',
  activity: '🎯',
  shopping: '🛍️',
  transport: '🚌'
}

export default function TimelineEntryCard({ entry, onDelete, dragHandleProps }) {
  const { t } = useTranslation()
  const formatTime = (timeStr) => {
    if (!timeStr) return null
    return new Date(`2000-01-01T${timeStr}`).toLocaleTimeString('de-DE', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 hover:shadow-md transition-shadow group"
    >
      <div className="flex gap-3">
        {/* Drag Handle */}
        <div
          {...dragHandleProps}
          className="flex-shrink-0 cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <GripVertical className="w-5 h-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <h4 className="font-semibold text-sm flex items-center gap-1.5">
                {entry.place_category && (
                  <span className="text-base">{categoryIcons[entry.place_category]}</span>
                )}
                {entry.place_name}
              </h4>

              <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-gray-600 dark:text-gray-400">
                {entry.start_time && (
                  <div className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>
                      {formatTime(entry.start_time)}
                      {entry.end_time && ` - ${formatTime(entry.end_time)}`}
                    </span>
                  </div>
                )}

                {entry.duration_minutes && (
                  <div className="flex items-center gap-1">
                    <span className="font-medium">{entry.duration_minutes} {t('timeline.minutes')}</span>
                  </div>
                )}
              </div>

              {entry.notes && (
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{entry.notes}</p>
              )}
            </div>

            {/* Delete Button */}
            <button
              onClick={() => onDelete(entry.id)}
              className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-100 dark:hover:bg-red-900 rounded transition-all"
              title={t('timeline.removeFromTimeline')}
            >
              <Trash2 className="w-4 h-4 text-red-600" />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
