import { Plus, MapPin, Calendar, Edit2, Trash2, Eye, Wifi, WifiOff } from 'lucide-react'
import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tripsService } from '@services/api'
import toast from 'react-hot-toast'
import { formatError } from '../utils/errorHandler'
import TripModal from '@components/TripModal'
import { useOfflineTrips, useOfflineMutation } from '@hooks/useOfflineStorage'
import indexedDB from '@services/indexedDB'
import { useTranslation } from 'react-i18next'
import { formatDate, formatCurrency } from '@/utils/format'

export default function Trips() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingTrip, setEditingTrip] = useState(null)
  const [deletingTrip, setDeletingTrip] = useState(null)
  const queryClient = useQueryClient()

  // Fetch trips from API with offline support
  const { data: trips = [], isLoading, isOffline, isCached } = useOfflineTrips({
    queryKey: ['trips'],
    queryFn: async () => {
      const response = await tripsService.getAll()
      return response.data
    }
  })

  // Create trip mutation
  const createTripMutation = useMutation({
    mutationFn: async (tripData) => {
      const response = await tripsService.create(tripData)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['trips'])
      setIsModalOpen(false)
      toast.success(t('trips:createSuccess'))
    },
    onError: (error) => {
      toast.error(formatError(error, t('trips:createError')))
      console.error(error)
    }
  })

  // Delete trip mutation
  const deleteTripMutation = useMutation({
    mutationFn: async (tripId) => {
      await tripsService.delete(tripId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['trips'])
      setDeletingTrip(null)
      toast.success(t('trips:deleteSuccess'))
    },
    onError: (error) => {
      toast.error(formatError(error, t('trips:deleteError')))
      console.error(error)
    }
  })

  // Update trip mutation
  const updateTripMutation = useMutation({
    mutationFn: async ({ id, data }) => {
      const response = await tripsService.update(id, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['trips'])
      setEditingTrip(null)
      setIsModalOpen(false)
      toast.success(t('trips:updateSuccess'))
    },
    onError: (error) => {
      toast.error(formatError(error, t('trips:updateError')))
      console.error(error)
    }
  })

  const handleCreateTrip = async (tripData) => {
    const result = await createTripMutation.mutateAsync(tripData)
    return result
  }

  const handleUpdateTrip = async (tripData) => {
    const result = await updateTripMutation.mutateAsync({ id: editingTrip.id, data: tripData })
    return result
  }

  const handleDeleteTrip = async (tripId) => {
    await deleteTripMutation.mutateAsync(tripId)
  }

  const openEditModal = (trip) => {
    setEditingTrip(trip)
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingTrip(null)
  }

  // Beispieldaten für Fallback
  const fallbackTrips = [
    {
      id: 1,
      title: 'Sommer in Portugal',
      destination: 'Lissabon',
      image: 'https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=800&auto=format&fit=crop',
      startDate: '2024-07-15',
      endDate: '2024-07-22',
      budget: 1200,
      currency: 'EUR',
      interests: ['Kultur', 'Essen', 'Fotografie']
    },
    {
      id: 2,
      title: 'Herbst in Japan',
      destination: 'Kyoto & Tokyo',
      image: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&auto=format&fit=crop',
      startDate: '2024-10-01',
      endDate: '2024-10-10',
      budget: 2500,
      currency: 'EUR',
      interests: ['Natur', 'Kultur', 'Fotografie']
    },
    {
      id: 3,
      title: 'Winterwanderung Alpen',
      destination: 'Innsbruck',
      image: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&auto=format&fit=crop',
      startDate: '2024-12-20',
      endDate: '2024-12-27',
      budget: 800,
      currency: 'EUR',
      interests: ['Natur', 'Sport', 'Fotografie']
    }
  ]

  const calculateDuration = (start, end) => {
    const days = Math.ceil((new Date(end) - new Date(start)) / (1000 * 60 * 60 * 24))
    return `${days} ${t('common:days')}`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold mb-2">{t('trips:title')}</h1>
          <p className="text-gray-600 dark:text-gray-400">
            {t('trips:manageAdventures')}
          </p>
          {isCached && (
            <div className="mt-2 flex items-center gap-2 text-sm">
              {isOffline ? (
                <span className="flex items-center gap-1 text-orange-600 dark:text-orange-400">
                  <WifiOff size={16} />
                  {t('trips:offlineMode')}
                </span>
              ) : (
                <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
                  <Wifi size={16} />
                  {t('trips:cachedUpdating')}
                </span>
              )}
            </div>
          )}
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="btn btn-primary"
        >
          <Plus className="w-5 h-5" />
          {t('trips:newTrip')}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="text-3xl font-bold text-primary-500 mb-1">
            {trips.length}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {t('trips:planned')}
          </div>
        </div>
        <div className="card">
          <div className="text-3xl font-bold text-secondary-500 mb-1">
            {trips.reduce((acc, trip) => {
              if (trip.start_date && trip.end_date) {
                const days = parseInt(calculateDuration(trip.start_date, trip.end_date))
                return acc + (isNaN(days) ? 0 : days)
              }
              return acc
            }, 0)}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {t('trips:totalDays')}
          </div>
        </div>
        <div className="card">
          <div className="text-3xl font-bold text-green-500 mb-1">
            {formatCurrency(trips.reduce((acc, trip) => acc + (trip.budget || 0), 0), trips[0]?.currency || 'EUR')}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {t('trips:totalBudget')}
          </div>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="card text-center py-16">
          <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">{t('trips:loading')}</p>
        </div>
      )}

      {/* Trips Grid */}
      {!isLoading && trips.length > 0 && (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {trips.map((trip, index) => (
          <motion.div
            key={trip.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
            onClick={() => navigate(`/trips/${trip.id}`)}
            className="card p-0 overflow-hidden group cursor-pointer hover:shadow-lg transition-shadow"
          >
            {/* Image */}
            <div className="relative h-48 overflow-hidden">
              {trip.cover_image ? (
                <img
                  src={trip.cover_image}
                  alt={trip.title}
                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                />
              ) : (
                <div className="w-full h-full bg-gradient-to-br from-primary-400 to-secondary-400 flex items-center justify-center">
                  <MapPin className="w-16 h-16 text-white/50" />
                </div>
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />

              {/* Action Buttons */}
              <div className="absolute top-3 right-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(`/trips/${trip.id}`)
                  }}
                  className="p-2 bg-white/90 hover:bg-white rounded-lg transition-colors"
                  title={t('trips:showDetails')}
                >
                  <Eye className="w-4 h-4 text-gray-700" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    openEditModal(trip)
                  }}
                  className="p-2 bg-white/90 hover:bg-white rounded-lg transition-colors"
                  title={t('common:edit')}
                >
                  <Edit2 className="w-4 h-4 text-gray-700" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setDeletingTrip(trip)
                  }}
                  className="p-2 bg-red-500/90 hover:bg-red-500 rounded-lg transition-colors"
                  title={t('common:delete')}
                >
                  <Trash2 className="w-4 h-4 text-white" />
                </button>
              </div>

              <div className="absolute bottom-3 left-3 text-white">
                <h3 className="text-xl font-bold mb-1">{trip.title}</h3>
                <div className="flex items-center gap-1 text-sm">
                  <MapPin className="w-4 h-4" />
                  {trip.destination}
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="p-4 space-y-3">
              {/* Dates */}
              {trip.start_date && trip.end_date ? (
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <Calendar className="w-4 h-4" />
                  <span>
                    {formatDate(trip.start_date, 'short').replace(/\/\d{4}/, '')}
                    {' - '}
                    {formatDate(trip.end_date, 'short')}
                  </span>
                  <span className="ml-auto badge badge-primary">
                    {calculateDuration(trip.start_date, trip.end_date)}
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <Calendar className="w-4 h-4" />
                  <span>{t('trips:dateNotSet')}</span>
                </div>
              )}

              {/* Interests */}
              {trip.interests && trip.interests.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {trip.interests.map((interest) => (
                    <span
                      key={interest}
                      className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-full"
                    >
                      {t(`interests.${interest}`, interest)}
                    </span>
                  ))}
                </div>
              )}

              {/* Budget */}
              <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {t('trips:budget')}
                  </span>
                  <span className="font-semibold text-green-600 dark:text-green-500">
                    {trip.budget ? formatCurrency(trip.budget, trip.currency || 'EUR') : t('trips:notSet')}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
      )}

      {/* Empty State */}
      {!isLoading && trips.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card text-center py-16"
        >
          <MapPin className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <h3 className="text-xl font-semibold mb-2">{t('trips:noTripsPlanned')}</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {t('trips:startFirstAdventure')}
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn btn-primary"
          >
            <Plus className="w-5 h-5" />
            {t('trips:createFirstTrip')}
          </button>
        </motion.div>
      )}

      {/* Trip Modal */}
      <TripModal
        isOpen={isModalOpen}
        onClose={closeModal}
        onSubmit={editingTrip ? handleUpdateTrip : handleCreateTrip}
        initialData={editingTrip}
        isEditing={!!editingTrip}
      />

      {/* Delete Confirmation Modal */}
      {deletingTrip && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setDeletingTrip(null)} />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full p-6"
          >
            <h3 className="text-xl font-bold mb-4">{t('trips:deleteQuestion')}</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {t('trips:deleteWarning').split('{title}').map((part, i, arr) => (
                i < arr.length - 1 ? (
                  <span key={i}>
                    {part}
                    <strong>{deletingTrip.title}</strong>
                  </span>
                ) : part
              ))}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeletingTrip(null)}
                className="btn btn-secondary flex-1"
              >
                {t('common:cancel')}
              </button>
              <button
                onClick={() => handleDeleteTrip(deletingTrip.id)}
                className="btn bg-red-500 hover:bg-red-600 text-white flex-1"
              >
                {t('common:delete')}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
