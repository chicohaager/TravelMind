import { useParams, useNavigate } from 'react-router-dom'
import { Plus, Image, MapPin, Calendar, Star, Map as MapIcon, Edit2, Trash2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { diaryService, tripsService } from '@services/api'
import toast from 'react-hot-toast'
import { useState, useEffect, useCallback } from 'react'
import DiaryModal from '@components/DiaryModal'
import { useTranslation } from 'react-i18next'
import { X, ChevronLeft, ChevronRight } from 'lucide-react'

export default function Diary() {
  const { t } = useTranslation()
  const { tripId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState(null)
  const [editingEntry, setEditingEntry] = useState(null)
  const [expandedEntries, setExpandedEntries] = useState(new Set())
  const [lightbox, setLightbox] = useState({ open: false, photos: [], index: 0 })

  // Fetch all trips
  const { data: trips = [], isLoading: isLoadingTrips } = useQuery({
    queryKey: ['trips'],
    queryFn: async () => {
      const response = await tripsService.getAll()
      return response.data
    }
  })

  // Fetch diary entries from API (if tripId is provided)
  const { data: entries = [], isLoading: isLoadingEntries, error } = useQuery({
    queryKey: ['diary', tripId],
    queryFn: async () => {
      const response = await diaryService.getEntries(tripId)
      return response.data
    },
    enabled: !!tripId,
    onError: (error) => {
      console.error('Error loading diary entries:', error)
      toast.error(t('diary:errorLoadingEntries'))
    }
  })

  // Fetch all diary entries for all trips (when no tripId)
  const { data: allEntriesData = [], isLoading: isLoadingAllEntries } = useQuery({
    queryKey: ['allDiaryEntries'],
    queryFn: async () => {
      // Fetch diary entries for each trip
      const entriesPromises = trips.map(async (trip) => {
        try {
          const response = await diaryService.getEntries(trip.id)
          return {
            trip,
            entries: response.data
          }
        } catch (error) {
          return {
            trip,
            entries: []
          }
        }
      })
      const results = await Promise.all(entriesPromises)
      // Filter out trips with no entries
      return results.filter(r => r.entries.length > 0)
    },
    enabled: !tripId && trips.length > 0
  })

  const isLoading = tripId ? isLoadingEntries : (isLoadingTrips || isLoadingAllEntries)

  // Mutation for creating diary entries
  const createEntryMutation = useMutation({
    mutationFn: async (data) => {
      const response = await diaryService.create(tripId, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['diary', tripId] })
      queryClient.invalidateQueries({ queryKey: ['allDiaryEntries'] })
      toast.success(t('diary:createSuccess'))
      setIsModalOpen(false)
    },
    onError: (error) => {
      console.error('Error creating diary entry:', error)
      toast.error(t('tripDetail:addError'))
    }
  })

  const handleCreateEntry = async (data) => {
    return createEntryMutation.mutateAsync(data)
  }

  // Mutation for updating diary entries
  const updateEntryMutation = useMutation({
    mutationFn: async ({ entryId, data }) => {
      const response = await diaryService.update(entryId, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['diary', tripId] })
      queryClient.invalidateQueries({ queryKey: ['allDiaryEntries'] })
      toast.success(t('diary:updateSuccess'))
      setIsModalOpen(false)
      setEditingEntry(null)
    },
    onError: (error) => {
      console.error('Error updating diary entry:', error)
      toast.error(t('diary:updateError'))
    }
  })

  // Mutation for deleting diary entries
  const deleteEntryMutation = useMutation({
    mutationFn: async (entryId) => {
      await diaryService.delete(entryId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['diary', tripId] })
      queryClient.invalidateQueries({ queryKey: ['allDiaryEntries'] })
      toast.success(t('diary:deleteSuccess'))
    },
    onError: (error) => {
      console.error('Error deleting diary entry:', error)
      toast.error(t('diary:deleteError'))
    }
  })

  const handleUpdateEntry = async (data) => {
    return updateEntryMutation.mutateAsync({ entryId: editingEntry.id, data })
  }

  const handleDeleteEntry = async (entryId) => {
    if (window.confirm(t('diary:confirmDelete'))) {
      deleteEntryMutation.mutate(entryId)
    }
  }

  const openEditModal = (entry) => {
    setEditingEntry(entry)
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingEntry(null)
  }

  const moodEmojis = {
    'excited': '🤩',
    'happy': '😊',
    'relaxed': '😌',
    'adventurous': '🤠',
    'tired': '😴'
  }

  const toggleExpand = (entryId) => {
    setExpandedEntries(prev => {
      const newSet = new Set(prev)
      if (newSet.has(entryId)) {
        newSet.delete(entryId)
      } else {
        newSet.add(entryId)
      }
      return newSet
    })
  }

  const openEntryModal = (entry) => {
    setSelectedEntry(entry)
    setIsModalOpen(true)
  }

  const openLightbox = (photos, index) => {
    setLightbox({ open: true, photos, index })
  }

  const closeLightbox = () => {
    setLightbox({ open: false, photos: [], index: 0 })
  }

  const nextPhoto = () => {
    setLightbox(prev => ({
      ...prev,
      index: (prev.index + 1) % prev.photos.length
    }))
  }

  const prevPhoto = () => {
    setLightbox(prev => ({
      ...prev,
      index: (prev.index - 1 + prev.photos.length) % prev.photos.length
    }))
  }

  const getPhotoUrl = (photo) => {
    return photo.startsWith('http') ? photo : `${import.meta.env.VITE_API_URL}${photo}`
  }

  // Keyboard navigation for lightbox
  const handleKeyDown = useCallback((e) => {
    if (!lightbox.open) return
    if (e.key === 'Escape') closeLightbox()
    if (e.key === 'ArrowLeft') prevPhoto()
    if (e.key === 'ArrowRight') nextPhoto()
  }, [lightbox.open])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold mb-2">{t('diary:title')}</h1>
          <p className="text-gray-600 dark:text-gray-400">
            {tripId ? t('diary:captureMemories') : t('diary:allMemoriesInOnePlace')}
          </p>
        </div>
        {tripId && (
          <button
            className="btn btn-primary"
            onClick={() => setIsModalOpen(true)}
          >
            <Plus className="w-5 h-5" />
            {t('diary:newEntry')}
          </button>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="card text-center py-16">
          <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">{t('diary:loadingEntries')}</p>
        </div>
      )}

      {/* Show trips selector when no tripId */}
      {!tripId && !isLoading && trips.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {trips.map((trip) => (
            <motion.div
              key={trip.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={() => navigate(`/diary/${trip.id}`)}
              className="card cursor-pointer hover:shadow-lg transition-all"
            >
              <div className="flex items-start gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center text-white flex-shrink-0">
                  <MapIcon className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-lg mb-1">{trip.title}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {trip.destination}
                  </p>
                  {trip.start_date && trip.end_date && (
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Calendar className="w-3 h-3" />
                      {new Date(trip.start_date).toLocaleDateString('de-DE', { day: '2-digit', month: 'short' })}
                      {' - '}
                      {new Date(trip.end_date).toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Show all diary entries grouped by trip when no tripId */}
      {!tripId && !isLoading && allEntriesData.length > 0 && (
        <div className="space-y-8">
          {allEntriesData.map(({ trip, entries: tripEntries }) => (
            <motion.div
              key={trip.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              <div className="flex items-center justify-between">
                <div
                  onClick={() => navigate(`/trips/${trip.id}`)}
                  className="cursor-pointer hover:text-primary-500 transition-colors"
                >
                  <h2 className="text-2xl font-bold flex items-center gap-2">
                    <MapPin className="w-6 h-6" />
                    {trip.title}
                  </h2>
                  <p className="text-gray-600 dark:text-gray-400">{trip.destination}</p>
                </div>
                <button
                  onClick={() => navigate(`/diary/${trip.id}`)}
                  className="text-sm text-primary-500 hover:text-primary-600 font-medium"
                >
                  {t('common:showAll')}
                </button>
              </div>

              <div className="space-y-4">
                {tripEntries.slice(0, 3).map((entry, index) => (
                  <motion.div
                    key={entry.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.1 }}
                    onClick={() => navigate(`/diary/${trip.id}`)}
                    className="card hover:shadow-lg transition-shadow cursor-pointer"
                  >
                    <div className="flex gap-4">
                      <div className="relative z-10">
                        <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-full flex items-center justify-center text-white text-xl shadow-lg">
                          {moodEmojis[entry.mood] || '📝'}
                        </div>
                      </div>

                      <div className="flex-1">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <h3 className="text-xl font-bold mb-1">{entry.title}</h3>
                            <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                              <div className="flex items-center gap-1">
                                <Calendar className="w-4 h-4" />
                                {new Date(entry.entry_date).toLocaleDateString('de-DE', {
                                  day: '2-digit',
                                  month: 'long',
                                  year: 'numeric'
                                })}
                              </div>
                              {entry.location_name && (
                                <div className="flex items-center gap-1">
                                  <MapPin className="w-4 h-4" />
                                  {entry.location_name}
                                </div>
                              )}
                            </div>
                          </div>
                          {entry.rating && (
                            <div className="flex items-center gap-1">
                              {[...Array(entry.rating)].map((_, i) => (
                                <Star
                                  key={i}
                                  className="w-4 h-4 fill-yellow-400 text-yellow-400"
                                />
                              ))}
                            </div>
                          )}
                        </div>
                        <p className="text-gray-700 dark:text-gray-300 mb-3 line-clamp-2">
                          {entry.content}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                ))}
                {tripEntries.length > 3 && (
                  <div className="text-center text-sm text-gray-600 dark:text-gray-400">
                    {t('diary:moreEntries').replace('{count}', tripEntries.length - 3)}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Timeline for specific trip */}
      {tripId && !isLoading && (
      <div className="space-y-6">
        {entries.map((entry, index) => (
          <motion.div
            key={entry.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
            className="relative"
          >
            {/* Timeline Line */}
            {index < entries.length - 1 && (
              <div className="absolute left-6 top-16 w-0.5 h-full bg-gradient-to-b from-primary-500 to-secondary-500" />
            )}

            <div className="flex gap-4">
              {/* Timeline Dot */}
              <div className="relative z-10">
                <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-full flex items-center justify-center text-white text-xl shadow-lg">
                  {moodEmojis[entry.mood] || '📝'}
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 card hover:shadow-lg transition-shadow">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="text-xl font-bold mb-1">{entry.title}</h3>
                    <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {new Date(entry.entry_date).toLocaleDateString('de-DE', {
                          day: '2-digit',
                          month: 'long',
                          year: 'numeric'
                        })}
                      </div>
                      {entry.location_name && (
                        <div className="flex items-center gap-1">
                          <MapPin className="w-4 h-4" />
                          {entry.location_name}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {entry.rating && (
                      <div className="flex items-center gap-1 mr-2">
                        {[...Array(entry.rating)].map((_, i) => (
                          <Star
                            key={i}
                            className="w-4 h-4 fill-yellow-400 text-yellow-400"
                          />
                        ))}
                      </div>
                    )}
                    <button
                      onClick={() => openEditModal(entry)}
                      className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      title={t('common:edit')}
                    >
                      <Edit2 className="w-4 h-4 text-gray-500" />
                    </button>
                    <button
                      onClick={() => handleDeleteEntry(entry.id)}
                      className="p-2 rounded-full hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                      title={t('common:delete')}
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                </div>

                {/* Content - expandable */}
                <p className={`text-gray-700 dark:text-gray-300 mb-3 whitespace-pre-wrap ${expandedEntries.has(entry.id) ? '' : 'line-clamp-3'}`}>
                  {entry.content}
                </p>

                {/* Photos */}
                {entry.photos && entry.photos.length > 0 && (
                  <div className={`flex flex-wrap gap-2 mb-3`}>
                    {(expandedEntries.has(entry.id) ? entry.photos : entry.photos.slice(0, 3)).map((photo, i) => (
                      <img
                        key={i}
                        src={getPhotoUrl(photo)}
                        alt={`Photo ${i + 1}`}
                        onClick={() => openLightbox(entry.photos, i)}
                        className={`${expandedEntries.has(entry.id) ? 'w-32 h-32' : 'w-20 h-20'} object-cover rounded-lg cursor-pointer hover:opacity-80 transition-opacity`}
                      />
                    ))}
                    {!expandedEntries.has(entry.id) && entry.photos.length > 3 && (
                      <div
                        onClick={() => openLightbox(entry.photos, 3)}
                        className="w-20 h-20 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center text-sm text-gray-500 cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                      >
                        +{entry.photos.length - 3}
                      </div>
                    )}
                  </div>
                )}

                {/* Tags */}
                {expandedEntries.has(entry.id) && entry.tags && entry.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-3">
                    {entry.tags.map((tag, i) => (
                      <span key={i} className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-xs">
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}

                <button
                  onClick={() => toggleExpand(entry.id)}
                  className="text-sm text-primary-500 hover:text-primary-600 font-medium cursor-pointer"
                >
                  {expandedEntries.has(entry.id) ? t('diary:showLess') : t('diary:readMore')} {expandedEntries.has(entry.id) ? '↑' : '→'}
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
      )}

      {/* Empty State - No entries for specific trip */}
      {tripId && !isLoading && entries.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card text-center py-16"
        >
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <Image className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-xl font-semibold mb-2">{t('diary:noEntriesYetTitle')}</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {t('diary:startCapturingExperiences')}
          </p>
          <button
            className="btn btn-primary"
            onClick={() => setIsModalOpen(true)}
          >
            <Plus className="w-5 h-5" />
            {t('diary:createFirstEntry')}
          </button>
        </motion.div>
      )}

      {/* Empty State - No trips */}
      {!tripId && !isLoading && trips.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card text-center py-16"
        >
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <MapIcon className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-xl font-semibold mb-2">{t('diary:noTripsPlannedTitle')}</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {t('diary:createTripForDiary')}
          </p>
          <button
            onClick={() => navigate('/trips')}
            className="btn btn-primary"
          >
            <Plus className="w-5 h-5" />
            {t('trips:createTrip')}
          </button>
        </motion.div>
      )}

      {/* Empty State - No diary entries across all trips */}
      {!tripId && !isLoading && trips.length > 0 && allEntriesData.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card text-center py-16"
        >
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <Image className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-xl font-semibold mb-2">{t('diary:noDiaryEntriesTitle')}</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {t('diary:selectTripAndStart')}
          </p>
        </motion.div>
      )}

      {/* Lightbox Modal */}
      {lightbox.open && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={closeLightbox}
        >
          {/* Close Button */}
          <button
            onClick={closeLightbox}
            className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors z-10"
          >
            <X className="w-8 h-8" />
          </button>

          {/* Photo Counter */}
          <div className="absolute top-4 left-4 text-white text-sm">
            {lightbox.index + 1} / {lightbox.photos.length}
          </div>

          {/* Previous Button */}
          {lightbox.photos.length > 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); prevPhoto(); }}
              className="absolute left-4 text-white hover:text-gray-300 transition-colors p-2 rounded-full bg-black/50 hover:bg-black/70"
            >
              <ChevronLeft className="w-8 h-8" />
            </button>
          )}

          {/* Image */}
          <img
            src={getPhotoUrl(lightbox.photos[lightbox.index])}
            alt={`Photo ${lightbox.index + 1}`}
            onClick={(e) => e.stopPropagation()}
            className="max-h-[90vh] max-w-[90vw] object-contain"
          />

          {/* Next Button */}
          {lightbox.photos.length > 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); nextPhoto(); }}
              className="absolute right-4 text-white hover:text-gray-300 transition-colors p-2 rounded-full bg-black/50 hover:bg-black/70"
            >
              <ChevronRight className="w-8 h-8" />
            </button>
          )}

          {/* Thumbnails */}
          {lightbox.photos.length > 1 && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
              {lightbox.photos.map((photo, i) => (
                <img
                  key={i}
                  src={getPhotoUrl(photo)}
                  alt={`Thumbnail ${i + 1}`}
                  onClick={(e) => { e.stopPropagation(); setLightbox(prev => ({ ...prev, index: i })); }}
                  className={`w-12 h-12 object-cover rounded cursor-pointer transition-all ${
                    i === lightbox.index ? 'ring-2 ring-white opacity-100' : 'opacity-50 hover:opacity-75'
                  }`}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Diary Modal */}
      <DiaryModal
        isOpen={isModalOpen}
        onClose={closeModal}
        onSubmit={editingEntry ? handleUpdateEntry : handleCreateEntry}
        initialData={editingEntry}
        entryId={editingEntry?.id}
      />
    </div>
  )
}
