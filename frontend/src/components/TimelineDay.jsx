import { useState } from 'react'
import { Calendar, Clock, Sparkles, ChevronDown, ChevronUp } from 'lucide-react'
import { motion, Reorder, AnimatePresence } from 'framer-motion'
import TimelineEntryCard from './TimelineEntryCard'

export default function TimelineDay({ day, onReorder, onDeleteEntry, onOptimize, isExpanded, onToggleExpand }) {
  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('de-DE', {
      weekday: 'long',
      day: '2-digit',
      month: 'long'
    })
  }

  const formatDuration = (minutes) => {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    if (hours === 0) return `${mins} Min`
    if (mins === 0) return `${hours} Std`
    return `${hours} Std ${mins} Min`
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-xl shadow-md overflow-hidden"
    >
      {/* Day Header */}
      <div
        className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4 cursor-pointer"
        onClick={onToggleExpand}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Calendar className="w-5 h-5" />
            <div>
              <h3 className="font-bold text-lg">{formatDate(day.day_date)}</h3>
              <div className="flex items-center gap-3 text-sm opacity-90 mt-1">
                <span>{day.entries.length} Orte</span>
                {day.total_duration_minutes > 0 && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {formatDuration(day.total_duration_minutes)}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {day.entries.length > 1 && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onOptimize(day.day_date)
                }}
                className="px-3 py-1.5 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5"
                title="Route optimieren"
              >
                <Sparkles className="w-4 h-4" />
                Optimieren
              </button>
            )}
            {isExpanded ? (
              <ChevronUp className="w-5 h-5" />
            ) : (
              <ChevronDown className="w-5 h-5" />
            )}
          </div>
        </div>
      </div>

      {/* Entries */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="p-4">
              {day.entries.length === 0 ? (
                <p className="text-center text-gray-500 dark:text-gray-400 py-8">
                  Keine Einträge für diesen Tag
                </p>
              ) : (
                <Reorder.Group
                  axis="y"
                  values={day.entries}
                  onReorder={onReorder}
                  className="space-y-2"
                >
                  {day.entries.map((entry) => (
                    <Reorder.Item key={entry.id} value={entry}>
                      <TimelineEntryCard
                        entry={entry}
                        onDelete={onDeleteEntry}
                        dragHandleProps={{}}
                      />
                    </Reorder.Item>
                  ))}
                </Reorder.Group>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
