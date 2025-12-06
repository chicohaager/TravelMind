import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { MapPin, Calendar, DollarSign, Users, Edit, Trash2, ArrowLeft, BookOpen, Plus, Download, FileText, Globe, Clock, Map as MapIcon, Sparkles, Check, X } from 'lucide-react'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tripsService, participantsService, diaryService, placesService } from '@services/api'
import toast from 'react-hot-toast'
import { formatError } from '../utils/errorHandler'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { useState } from 'react'
import { clsx } from 'clsx'
import DiaryEntry from '@components/DiaryEntry'
import DiaryModal from '@components/DiaryModal'
import PlaceCard from '@components/PlaceCard'
import PlaceModal from '@components/PlaceModal'
import TimelineView from '@components/TimelineView'
import BudgetView from '@components/BudgetView'
import ParticipantsManager from '@components/ParticipantsManager'
import ImportFromGuideModal from '@components/ImportFromGuideModal'
import RecommendationsView from '@components/RecommendationsView'
import PlaceListsSection from '@components/PlaceListsSection'
import PlaceDetailModal from '@components/PlaceDetailModal'
import { useTranslation } from 'react-i18next'

// Fix Leaflet icon issue
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

const INTEREST_KEYS = [
  'culture',
  'nature',
  'food',
  'photography',
  'sports',
  'history',
  'beach',
  'cityTrip',
  'adventure',
  'relaxation',
  'shopping',
  'nightlife',
  'architecture',
  'music',
  'art'
]

export default function TripDetail() {
  const { t } = useTranslation()

  const tabs = [
    { id: 'overview', name: t('tripDetail:overview'), icon: MapIcon },
    { id: 'recommendations', name: t('tripDetail:recommendations'), icon: Sparkles },
    { id: 'places', name: t('tripDetail:places'), icon: MapPin },
    { id: 'diary', name: t('tripDetail:diary'), icon: BookOpen },
    { id: 'timeline', name: t('tripDetail:timeline'), icon: Clock },
    { id: 'budget', name: t('tripDetail:budget'), icon: DollarSign },
    { id: 'participants', name: t('tripDetail:participants'), icon: Users },
  ]

  const AVAILABLE_INTERESTS = INTEREST_KEYS.map(key => t(`tripDetail.${key}`))
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get('tab') || 'overview'

  const [isDiaryModalOpen, setIsDiaryModalOpen] = useState(false)
  const [editingEntry, setEditingEntry] = useState(null)
  const [isPlaceModalOpen, setIsPlaceModalOpen] = useState(false)
  const [editingPlace, setEditingPlace] = useState(null)
  const [isImportModalOpen, setIsImportModalOpen] = useState(false)
  const [isEditingInterests, setIsEditingInterests] = useState(false)
  const [selectedInterests, setSelectedInterests] = useState([])
  const [selectedPlace, setSelectedPlace] = useState(null)
  const [isPlaceDetailOpen, setIsPlaceDetailOpen] = useState(false)

  const setActiveTab = (tabId) => {
    setSearchParams({ tab: tabId })
  }

  // Fetch trip data
  const { data: trip, isLoading, error } = useQuery({
    queryKey: ['trip', id],
    queryFn: async () => {
      const response = await tripsService.getById(id)
      return response.data
    }
  })

  // Fetch participants
  const { data: participants = [] } = useQuery({
    queryKey: ['participants', id],
    queryFn: async () => {
      const response = await participantsService.getParticipants(id)
      return response.data
    },
    enabled: !!id
  })

  // Fetch diary entries
  const { data: diaryEntries = [] } = useQuery({
    queryKey: ['diary', id],
    queryFn: async () => {
      const response = await diaryService.getEntries(id)
      return response.data
    },
    enabled: !!id
  })

  // Fetch places
  const { data: places = [] } = useQuery({
    queryKey: ['places', id],
    queryFn: async () => {
      const response = await placesService.getPlaces(id)
      return response.data
    },
    enabled: !!id
  })

  // Create place mutation
  const createPlaceMutation = useMutation({
    mutationFn: async (data) => {
      const response = await placesService.create(id, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['places', id])
      setIsPlaceModalOpen(false)
      toast.success(t('tripDetail:placeAdded'))
    },
    onError: () => {
      toast.error(t('tripDetail:addError'))
    }
  })

  // Update place mutation
  const updatePlaceMutation = useMutation({
    mutationFn: async ({ placeId, data }) => {
      const response = await placesService.update(placeId, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['places', id])
      setIsPlaceModalOpen(false)
      setEditingPlace(null)
      toast.success(t('tripDetail:placeUpdated'))
    },
    onError: () => {
      toast.error(t('tripDetail:updateError'))
    }
  })

  // Delete place mutation
  const deletePlaceMutation = useMutation({
    mutationFn: async (placeId) => {
      await placesService.delete(placeId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['places', id])
      toast.success(t('tripDetail:placeDeleted'))
    },
    onError: () => {
      toast.error(t('tripDetail:deleteError'))
    }
  })

  // Toggle visited mutation
  const toggleVisitedMutation = useMutation({
    mutationFn: async ({ placeId, visited }) => {
      await placesService.markVisited(placeId, visited)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['places', id])
    }
  })

  // Create diary entry mutation
  const createDiaryMutation = useMutation({
    mutationFn: async (data) => {
      const response = await diaryService.create(id, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['diary', id])
      setIsDiaryModalOpen(false)
      toast.success(t('tripDetail:entryCreated'))
    },
    onError: () => {
      toast.error(t('tripDetail:addError'))
    }
  })

  // Update diary entry mutation
  const updateDiaryMutation = useMutation({
    mutationFn: async ({ entryId, data }) => {
      const response = await diaryService.update(entryId, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['diary', id])
      setIsDiaryModalOpen(false)
      setEditingEntry(null)
      toast.success(t('tripDetail:entryUpdated'))
    },
    onError: () => {
      toast.error(t('tripDetail:updateError'))
    }
  })

  // Delete diary entry mutation
  const deleteDiaryMutation = useMutation({
    mutationFn: async (entryId) => {
      await diaryService.delete(entryId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['diary', id])
      toast.success(t('tripDetail:entryDeleted'))
    },
    onError: () => {
      toast.error(t('tripDetail:deleteError'))
    }
  })

  // Handler functions for places
  const handlePlaceSubmit = async (data) => {
    if (editingPlace) {
      await updatePlaceMutation.mutateAsync({ placeId: editingPlace.id, data })
    } else {
      await createPlaceMutation.mutateAsync(data)
    }
  }

  const handleEditPlace = (place) => {
    setEditingPlace(place)
    setIsPlaceModalOpen(true)
  }

  const handleDeletePlace = async (placeId) => {
    if (confirm(t('tripDetail:deletePlace'))) {
      await deletePlaceMutation.mutateAsync(placeId)
    }
  }

  const handleToggleVisited = async (placeId, visited) => {
    await toggleVisitedMutation.mutateAsync({ placeId, visited })
  }

  const handlePlaceClick = (place) => {
    setSelectedPlace(place)
    setIsPlaceDetailOpen(true)
  }

  // Handler functions for diary
  const handleDiarySubmit = async (data) => {
    if (editingEntry) {
      await updateDiaryMutation.mutateAsync({ entryId: editingEntry.id, data })
    } else {
      await createDiaryMutation.mutateAsync(data)
    }
  }

  const handleEditEntry = (entry) => {
    setEditingEntry(entry)
    setIsDiaryModalOpen(true)
  }

  const handleDeleteEntry = async (entryId) => {
    if (confirm(t('tripDetail:deleteEntry'))) {
      await deleteDiaryMutation.mutateAsync(entryId)
    }
  }

  // Export handlers
  const handleExportMarkdown = async () => {
    try {
      const response = await diaryService.exportMarkdown(id)
      const blob = new Blob([response.data], { type: 'text/markdown' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${trip.title.replace(/ /g, '_')}_tagebuch.md`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast.success(t('tripDetail:markdownDownloaded'))
    } catch (error) {
      toast.error(formatError(error, t('tripDetail:exportError')))
    }
  }

  const handleExportPdf = async () => {
    try {
      const response = await diaryService.exportPdf(id)
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${trip.title.replace(/ /g, '_')}_tagebuch.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast.success(t('tripDetail:pdfDownloaded'))
    } catch (error) {
      toast.error(formatError(error, t('tripDetail:exportError')))
    }
  }

  // Interests handlers
  const handleEditInterests = () => {
    setSelectedInterests(trip.interests || [])
    setIsEditingInterests(true)
  }

  const handleCancelEditInterests = () => {
    setIsEditingInterests(false)
    setSelectedInterests([])
  }

  const handleToggleInterest = (interest) => {
    setSelectedInterests(prev =>
      prev.includes(interest)
        ? prev.filter(i => i !== interest)
        : [...prev, interest]
    )
  }

  const handleSaveInterests = async () => {
    await updateTripMutation.mutateAsync({ interests: selectedInterests })
    setIsEditingInterests(false)
  }

  // Update trip mutation
  const updateTripMutation = useMutation({
    mutationFn: async (data) => {
      const response = await tripsService.update(id, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['trip', id])
      toast.success(t('tripDetail:tripUpdated'))
    },
    onError: () => {
      toast.error(t('tripDetail:updateError'))
    }
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async () => {
      await tripsService.delete(id)
    },
    onSuccess: () => {
      toast.success(t('tripDetail:tripDeleted'))
      navigate('/trips')
    },
    onError: () => {
      toast.error(t('tripDetail:deleteError'))
    }
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full"></div>
      </div>
    )
  }

  if (error || !trip) {
    return (
      <div className="text-center py-16">
        <h2 className="text-2xl font-bold mb-4">{t('tripDetail:tripNotFound')}</h2>
        <button onClick={() => navigate('/trips')} className="btn btn-primary">
          {t('tripDetail:backToTrips')}
        </button>
      </div>
    )
  }

  const mapCenter = trip.latitude && trip.longitude
    ? [trip.latitude, trip.longitude]
    : [51.1657, 10.4515] // Germany center as fallback

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => navigate('/trips')}
        className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-primary-500 transition-colors"
      >
        <ArrowLeft className="w-5 h-5" />
        {t('tripDetail:backToTrips')}
      </button>

      {/* Hero Image */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="relative h-64 md:h-80 rounded-2xl overflow-hidden"
      >
        {trip.cover_image ? (
          <img
            src={trip.cover_image}
            alt={trip.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-primary-400 to-secondary-400 flex items-center justify-center">
            <MapPin className="w-24 h-24 text-white/50" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
        <div className="absolute bottom-6 left-6 text-white">
          <h1 className="text-4xl md:text-5xl font-bold mb-2">{trip.title}</h1>
          <div className="flex items-center gap-2 text-lg">
            <MapPin className="w-5 h-5" />
            {trip.destination}
          </div>
        </div>
        <div className="absolute top-6 right-6 flex gap-2">
          <button
            onClick={() => navigate(`/trips/${trip.id}/edit`)}
            className="bg-white/90 hover:bg-white p-3 rounded-lg transition-colors"
          >
            <Edit className="w-5 h-5 text-gray-700" />
          </button>
          <button
            onClick={() => deleteMutation.mutate()}
            className="bg-red-500/90 hover:bg-red-500 p-3 rounded-lg transition-colors"
          >
            <Trash2 className="w-5 h-5 text-white" />
          </button>
        </div>
      </motion.div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
              <Calendar className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Zeitraum</div>
              <div className="font-semibold">
                {trip.start_date && trip.end_date ? (
                  <>
                    {new Date(trip.start_date).toLocaleDateString('de-DE', { day: '2-digit', month: 'short' })}
                    {' - '}
                    {new Date(trip.end_date).toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' })}
                  </>
                ) : (
                  t('common:notSet')
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400">Budget</div>
              <div className="font-semibold">
                {trip.budget ? `${trip.budget.toLocaleString('de-DE')} ${trip.currency}` : t('common:notSet')}
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
              <Users className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="flex-1">
              <div className="text-sm text-gray-600 dark:text-gray-400">{t('tripDetail:participants')}</div>
              <div className="font-semibold">{participants.length || t('common:none')}</div>
            </div>
          </div>
          {/* Participant Avatars */}
          {participants.length > 0 && (
            <div className="flex -space-x-2 mt-3">
              {participants.slice(0, 5).map((participant) => (
                participant.photo_url ? (
                  <img
                    key={participant.id}
                    src={participant.photo_url}
                    alt={participant.name}
                    title={participant.name}
                    className="w-8 h-8 rounded-full border-2 border-white dark:border-gray-800 object-cover"
                  />
                ) : (
                  <div
                    key={participant.id}
                    title={participant.name}
                    className="w-8 h-8 rounded-full border-2 border-white dark:border-gray-800 bg-primary-200 dark:bg-primary-700 flex items-center justify-center text-xs font-semibold text-primary-700 dark:text-primary-200"
                  >
                    {participant.name.charAt(0).toUpperCase()}
                  </div>
                )
              ))}
              {participants.length > 5 && (
                <div className="w-8 h-8 rounded-full border-2 border-white dark:border-gray-800 bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-semibold">
                  +{participants.length - 5}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-4 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  'flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm whitespace-nowrap transition-colors',
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:border-gray-300'
                )}
              >
                <Icon className="w-4 h-4" />
                {tab.name}
              </button>
            )
          })}
        </nav>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <>
              {/* Description */}
              {trip.description && (
                <div className="card">
                  <h2 className="text-2xl font-bold mb-4">Beschreibung</h2>
                  <p className="text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-wrap">
                    {trip.description}
                  </p>
                </div>
              )}

              {/* Interests */}
              <div className="card">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-2xl font-bold">Interessen</h2>
                  {!isEditingInterests && (
                    <button
                      onClick={handleEditInterests}
                      className="btn-outline btn-sm flex items-center gap-2"
                    >
                      <Edit className="w-4 h-4" />
                      {t('tripDetail:editInterests')}
                    </button>
                  )}
                </div>

                {isEditingInterests ? (
                  <>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                      {t('tripDetail:selectInterestsPrompt')}
                    </p>
                    <div className="flex flex-wrap gap-2 mb-4">
                      {AVAILABLE_INTERESTS.map((interest) => {
                        const isSelected = selectedInterests.includes(interest)
                        return (
                          <button
                            key={interest}
                            onClick={() => handleToggleInterest(interest)}
                            className={clsx(
                              'px-3 py-2 rounded-full text-sm font-medium transition-all',
                              'border-2 flex items-center gap-1.5',
                              isSelected
                                ? 'bg-primary-500 border-primary-500 text-white hover:bg-primary-600'
                                : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-primary-400'
                            )}
                          >
                            {isSelected && <Check className="w-4 h-4" />}
                            {t(`interests.${interest}`, interest)}
                          </button>
                        )
                      })}
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={handleSaveInterests}
                        disabled={updateTripMutation.isPending}
                        className="btn-primary btn-sm flex items-center gap-2"
                      >
                        <Check className="w-4 h-4" />
                        {t('tripDetail:saveInterests')}
                      </button>
                      <button
                        onClick={handleCancelEditInterests}
                        disabled={updateTripMutation.isPending}
                        className="btn-outline btn-sm flex items-center gap-2"
                      >
                        <X className="w-4 h-4" />
                        {t('common:cancel')}
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {trip.interests && trip.interests.length > 0 ? (
                      trip.interests.map((interest) => (
                        <span
                          key={interest}
                          className="badge badge-primary"
                        >
                          {t(`interests.${interest}`, interest)}
                        </span>
                      ))
                    ) : (
                      <p className="text-gray-600 dark:text-gray-400 text-sm">
                        {t('tripDetail:noInterestsYet')}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </>
          )}

          {/* Recommendations Tab */}
          {activeTab === 'recommendations' && (
            <RecommendationsView
              tripId={id}
              trip={trip}
              places={places}
            />
          )}

          {/* Participants Tab */}
          {activeTab === 'participants' && (
            <div className="card">
              <h2 className="text-2xl font-bold mb-4">Teilnehmer</h2>
              <ParticipantsManager tripId={id} participants={participants} isEditing={true} />
            </div>
          )}

          {/* Diary Tab */}
          {activeTab === 'diary' && (
          <div className="card">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold flex items-center gap-2">
                <BookOpen className="w-6 h-6" />
                Reisetagebuch
              </h2>
              <div className="flex gap-2">
                {diaryEntries.length > 0 && (
                  <>
                    <button
                      onClick={handleExportMarkdown}
                      className="btn btn-secondary btn-sm"
                      title="Als Markdown exportieren"
                    >
                      <FileText className="w-4 h-4" />
                      Markdown
                    </button>
                    <button
                      onClick={handleExportPdf}
                      className="btn btn-secondary btn-sm"
                      title="Als PDF exportieren"
                    >
                      <Download className="w-4 h-4" />
                      PDF
                    </button>
                  </>
                )}
                <button
                  onClick={() => {
                    setEditingEntry(null)
                    setIsDiaryModalOpen(true)
                  }}
                  className="btn btn-primary btn-sm"
                >
                  <Plus className="w-4 h-4" />
                  Eintrag hinzufügen
                </button>
              </div>
            </div>

            {diaryEntries.length > 0 ? (
              <div className="space-y-4">
                {diaryEntries.map((entry) => (
                  <DiaryEntry
                    key={entry.id}
                    entry={entry}
                    onEdit={handleEditEntry}
                    onDelete={handleDeleteEntry}
                  />
                ))}
              </div>
            ) : (
              <p className="text-gray-600 dark:text-gray-400 text-center py-8">
                {t('tripDetail:noDiaryEntriesYet')}
              </p>
            )}
          </div>
          )}

          {/* Places Tab - With Custom Lists */}
          {activeTab === 'places' && (
          <div className="space-y-4">
            {/* Header with Actions */}
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold flex items-center gap-2">
                <MapPin className="w-6 h-6" />
                Orte & Aktivitäten
                {places.length > 0 && (
                  <span className="text-sm font-normal text-gray-600 dark:text-gray-400">
                    ({places.length})
                  </span>
                )}
              </h2>
              <div className="flex gap-2">
                <button
                  onClick={() => setIsImportModalOpen(true)}
                  className="btn btn-outline btn-sm flex items-center gap-2"
                >
                  <Globe className="w-4 h-4" />
                  <span className="hidden sm:inline">Aus Reiseführer</span>
                </button>
                <button
                  onClick={() => {
                    setEditingPlace(null)
                    setIsPlaceModalOpen(true)
                  }}
                  className="btn btn-primary btn-sm"
                >
                  <Plus className="w-4 h-4" />
                  Ort hinzufügen
                </button>
              </div>
            </div>

            {/* Custom Place Lists Section */}
            <PlaceListsSection
              tripId={id}
              places={places}
              onEditPlace={handleEditPlace}
              onDeletePlace={handleDeletePlace}
              onToggleVisited={handleToggleVisited}
              onPlaceClick={handlePlaceClick}
            />

            {/* Map View */}
            <div className="card h-[70vh] min-h-[500px]">
              <h3 className="text-lg font-bold mb-3">{t('map:title')}</h3>
              <div className="h-[calc(100%-2.5rem)] rounded-lg overflow-hidden">
                <MapContainer
                  center={mapCenter}
                  zoom={places.length > 0 ? 12 : (trip.latitude && trip.longitude ? 10 : 6)}
                  style={{ height: '100%', width: '100%' }}
                  scrollWheelZoom={true}
                  className="rounded-lg"
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  {/* Trip Destination Marker */}
                  {trip.latitude && trip.longitude && (
                    <Marker position={[trip.latitude, trip.longitude]}>
                      <Popup>
                        <div className="text-center">
                          <strong>{trip.destination}</strong>
                          <br />
                          <span className="text-xs text-gray-600">Reiseziel</span>
                        </div>
                      </Popup>
                    </Marker>
                  )}

                  {/* Place Markers */}
                  {places
                    .filter(place => place.latitude && place.longitude && place.latitude !== 0 && place.longitude !== 0)
                    .map((place) => (
                      <Marker
                        key={place.id}
                        position={[place.latitude, place.longitude]}
                      >
                        <Popup>
                          <div className="min-w-[200px]">
                            <h3 className="font-bold mb-1">{place.name}</h3>
                            {place.category && (
                              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                                {place.category}
                              </span>
                            )}
                            {place.description && (
                              <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                                {place.description}
                              </p>
                            )}
                            {place.address && (
                              <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
                                <MapPin className="w-3 h-3" />
                                {place.address}
                              </p>
                            )}
                          </div>
                        </Popup>
                      </Marker>
                    ))}
                </MapContainer>
              </div>
            </div>
          </div>
          )}

          {/* Timeline Tab */}
          {activeTab === 'timeline' && (
          <TimelineView
            tripId={id}
            places={places}
            tripStartDate={trip.start_date}
            tripEndDate={trip.end_date}
          />
          )}

          {/* Budget Tab */}
          {activeTab === 'budget' && (
          <BudgetView
            tripId={id}
            participants={participants}
          />
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Map */}
          <div className="card">
            <h3 className="text-lg font-bold mb-3">Karte</h3>
            <div className="h-64 rounded-lg overflow-hidden">
              <MapContainer
                center={mapCenter}
                zoom={trip.latitude && trip.longitude ? 10 : 6}
                style={{ height: '100%', width: '100%' }}
                scrollWheelZoom={false}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {trip.latitude && trip.longitude && (
                  <Marker position={[trip.latitude, trip.longitude]}>
                    <Popup>{trip.destination}</Popup>
                  </Marker>
                )}
              </MapContainer>
            </div>
            <button
              onClick={() => navigate(`/trips/${id}/map`)}
              className="btn btn-primary w-full mt-3 flex items-center justify-center gap-2"
            >
              <MapIcon className="w-4 h-4" />
              Interaktive Karte & Routen
            </button>
          </div>

          {/* Stats */}
          <div className="card">
            <h3 className="text-lg font-bold mb-3">Statistiken</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Orte</span>
                <span className="font-semibold">{places.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Besucht</span>
                <span className="font-semibold">
                  {places.filter(p => p.visited).length} / {places.length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Tagebucheinträge</span>
                <span className="font-semibold">{diaryEntries.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Fotos</span>
                <span className="font-semibold">
                  {diaryEntries.reduce((acc, entry) => acc + (entry.photos?.length || 0), 0)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Place Modal */}
      <PlaceModal
        isOpen={isPlaceModalOpen}
        onClose={() => {
          setIsPlaceModalOpen(false)
          setEditingPlace(null)
        }}
        onSubmit={handlePlaceSubmit}
        initialData={editingPlace}
        tripDestination={trip?.destination}
      />

      {/* Diary Modal */}
      <DiaryModal
        isOpen={isDiaryModalOpen}
        onClose={() => {
          setIsDiaryModalOpen(false)
          setEditingEntry(null)
        }}
        onSubmit={handleDiarySubmit}
        initialData={editingEntry}
        entryId={editingEntry?.id}
      />

      {/* Import from Guide Modal */}
      <ImportFromGuideModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        tripId={id}
        destination={trip?.destination || ''}
        onImportComplete={() => {
          queryClient.invalidateQueries(['places', id])
        }}
      />

      {/* Place Detail Modal */}
      <PlaceDetailModal
        place={selectedPlace}
        isOpen={isPlaceDetailOpen}
        onClose={() => {
          setIsPlaceDetailOpen(false)
          setSelectedPlace(null)
        }}
      />
    </div>
  )
}
