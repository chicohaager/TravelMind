import { useState, useEffect } from 'react'
import { X, Calendar, Clock } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'

export default function AddToTimelineModal({ isOpen, onClose, onSubmit, places, tripStartDate, tripEndDate }) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    place_id: '',
    day_date: '',
    start_time: '',
    end_time: '',
    duration_minutes: '',
    notes: ''
  })

  useEffect(() => {
    if (!isOpen) {
      // Reset form when modal closes
      setFormData({
        place_id: '',
        day_date: '',
        start_time: '',
        end_time: '',
        duration_minutes: '',
        notes: ''
      })
    } else if (tripStartDate && !formData.day_date) {
      // Set default date to trip start date
      setFormData((prev) => ({ ...prev, day_date: tripStartDate }))
    }
  }, [isOpen, tripStartDate])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    const data = {
      place_id: parseInt(formData.place_id),
      day_date: formData.day_date,
      start_time: formData.start_time || null,
      end_time: formData.end_time || null,
      duration_minutes: formData.duration_minutes ? parseInt(formData.duration_minutes) : null,
      notes: formData.notes || null,
      order: 0
    }

    await onSubmit(data)

    // Reset form
    setFormData({
      place_id: '',
      day_date: tripStartDate || '',
      start_time: '',
      end_time: '',
      duration_minutes: '',
      notes: ''
    })
  }

  if (!isOpen) return null

  // Filter places that haven't been added to timeline yet (optional - could allow duplicates)
  const availablePlaces = places || []

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full">
              {/* Header */}
              <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-between items-center">
                <h2 className="text-xl font-bold">{t('timeline:addToTimeline')}</h2>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                {/* Place Selection */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('timeline:placeLabel')} *</label>
                  <select
                    name="place_id"
                    value={formData.place_id}
                    onChange={handleChange}
                    required
                    className="input"
                  >
                    <option value="">{t('timeline:placePlaceholder')}</option>
                    {availablePlaces.map((place) => (
                      <option key={place.id} value={place.id}>
                        {place.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Date */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    <Calendar className="w-4 h-4 inline mr-1" />
                    {t('timeline:dayLabel')} *
                  </label>
                  <input
                    type="date"
                    name="day_date"
                    value={formData.day_date}
                    onChange={handleChange}
                    min={tripStartDate}
                    max={tripEndDate}
                    required
                    className="input"
                  />
                </div>

                {/* Time Range */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      <Clock className="w-4 h-4 inline mr-1" />
                      {t('timeline:startTime')}
                    </label>
                    <input
                      type="time"
                      name="start_time"
                      value={formData.start_time}
                      onChange={handleChange}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('timeline:endTime')}</label>
                    <input
                      type="time"
                      name="end_time"
                      value={formData.end_time}
                      onChange={handleChange}
                      className="input"
                    />
                  </div>
                </div>

                {/* Duration */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('timeline:duration')}</label>
                  <input
                    type="number"
                    name="duration_minutes"
                    value={formData.duration_minutes}
                    onChange={handleChange}
                    placeholder={t('timeline:durationPlaceholder')}
                    min="0"
                    className="input"
                  />
                </div>

                {/* Notes */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('timeline:notesLabel')}</label>
                  <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    placeholder={t('timeline:notesPlaceholder')}
                    rows={2}
                    className="input"
                  />
                </div>

                {/* Buttons */}
                <div className="flex gap-3 pt-2">
                  <button type="button" onClick={onClose} className="btn btn-secondary flex-1">
                    {t('common:cancel')}
                  </button>
                  <button type="submit" className="btn btn-primary flex-1">
                    {t('timeline:addButton')}
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
