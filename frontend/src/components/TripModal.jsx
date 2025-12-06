import { useState, useEffect } from 'react'
import { X, Upload, Image as ImageIcon, Sparkles, MapPin as MapPinIcon } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation, useQuery } from '@tanstack/react-query'
import { tripsService, aiService, participantsService } from '@services/api'
import toast from 'react-hot-toast'
import ParticipantsManager from './ParticipantsManager'
import { useTranslation } from 'react-i18next'

export default function TripModal({ isOpen, onClose, onSubmit, initialData = null, isEditing = false }) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    title: '',
    destination: '',
    description: '',
    start_date: '',
    end_date: '',
    interests: [],
    budget: '',
    currency: 'EUR',
    latitude: null,
    longitude: null
  })

  const [selectedImage, setSelectedImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)

  // Fetch participants when editing
  const { data: participants = [] } = useQuery({
    queryKey: ['participants', initialData?.id],
    queryFn: async () => {
      if (!initialData?.id) return []
      const response = await participantsService.getParticipants(initialData.id)
      return response.data
    },
    enabled: isEditing && !!initialData?.id
  })

  // Load initial data when editing
  useEffect(() => {
    if (initialData && isEditing) {
      setFormData({
        title: initialData.title || '',
        destination: initialData.destination || '',
        description: initialData.description || '',
        start_date: initialData.start_date ? initialData.start_date.split('T')[0] : '',
        end_date: initialData.end_date ? initialData.end_date.split('T')[0] : '',
        interests: initialData.interests || [],
        budget: initialData.budget || '',
        currency: initialData.currency || 'EUR',
        latitude: initialData.latitude || null,
        longitude: initialData.longitude || null
      })
      // Set existing image preview if available
      if (initialData.cover_image) {
        setImagePreview(initialData.cover_image)
      }
    } else if (!isOpen) {
      // Reset form when modal closes
      setFormData({
        title: '',
        destination: '',
        description: '',
        start_date: '',
        end_date: '',
        interests: [],
        budget: '',
        currency: 'EUR',
        latitude: null,
        longitude: null
      })
      setSelectedImage(null)
      setImagePreview(null)
    }
  }, [initialData, isEditing, isOpen])

  const [newInterest, setNewInterest] = useState('')

  // Upload image mutation
  const uploadImageMutation = useMutation({
    mutationFn: async ({ tripId, file }) => {
      const response = await tripsService.uploadImage(tripId, file)
      return response.data
    },
    onSuccess: () => {
      toast.success(t('trips:imageUploaded'))
    },
    onError: (error) => {
      toast.error(t('trips:imageUploadError'))
      console.error(error)
    }
  })

  // AI Suggestions mutation
  const aiSuggestionsMutation = useMutation({
    mutationFn: async (destination) => {
      const response = await aiService.getTripSuggestions(destination)
      return response.data
    },
    onSuccess: (data) => {
      // Apply AI suggestions to form
      setFormData(prev => ({
        ...prev,
        title: data.title || prev.title,
        description: data.description || prev.description,
        interests: data.interests || prev.interests,
        budget: data.budget_min ? Math.round((data.budget_min + data.budget_max) / 2) : prev.budget,
        currency: data.currency || prev.currency
      }))
      toast.success(t('trips:aiSuggestionsLoaded'))
    },
    onError: (error) => {
      toast.error(t('trips:aiSuggestionsError'))
      console.error(error)
    }
  })

  // Geocoding mutation
  const geocodeMutation = useMutation({
    mutationFn: async (destination) => {
      const response = await tripsService.geocode(destination)
      return response.data
    },
    onSuccess: (data) => {
      // Apply coordinates to form
      setFormData(prev => ({
        ...prev,
        latitude: data.latitude,
        longitude: data.longitude
      }))
      toast.success(t('trips:coordinatesFound').replace('{name}', data.display_name))
    },
    onError: (error) => {
      toast.error(t('trips:coordinatesNotFound'))
      console.error(error)
    }
  })

  const handleAiSuggestions = async () => {
    if (!formData.destination) {
      toast.error(t('trips:enterDestinationFirst'))
      return
    }

    try {
      // Get AI suggestions
      await aiSuggestionsMutation.mutateAsync(formData.destination)

      // Also geocode the destination
      geocodeMutation.mutate(formData.destination)
    } catch (error) {
      // Error already handled by onError callback
      console.error('AI suggestions error:', error)
    }
  }

  const handleGeocode = () => {
    if (!formData.destination) {
      toast.error(t('trips:enterDestinationFirst'))
      return
    }
    geocodeMutation.mutate(formData.destination)
  }

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file type
      const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
      if (!allowedTypes.includes(file.type)) {
        toast.error(t('trips:onlyImagesAllowed'))
        return
      }

      // Validate file size (10MB)
      if (file.size > 10 * 1024 * 1024) {
        toast.error(t('trips:imageTooLarge'))
        return
      }

      setSelectedImage(file)

      // Create preview
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const removeImage = () => {
    setSelectedImage(null)
    setImagePreview(null)
  }

  const interestSuggestions = [
    'culture',
    'nature',
    'food',
    'photography',
    'sports',
    'history',
    'beach',
    'cityTrip',
    'adventure',
    'relaxation'
  ]

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const addInterest = (interest) => {
    if (!formData.interests.includes(interest)) {
      setFormData(prev => ({
        ...prev,
        interests: [...prev.interests, interest]
      }))
    }
  }

  const removeInterest = (interest) => {
    setFormData(prev => ({
      ...prev,
      interests: prev.interests.filter(i => i !== interest)
    }))
  }

  const handleAddCustomInterest = () => {
    if (newInterest.trim() && !formData.interests.includes(newInterest.trim())) {
      addInterest(newInterest.trim())
      setNewInterest('')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    // Prepare data for API
    const tripData = {
      ...formData,
      budget: formData.budget ? parseFloat(formData.budget) : null,
      start_date: formData.start_date ? `${formData.start_date}T00:00:00` : null,
      end_date: formData.end_date ? `${formData.end_date}T00:00:00` : null,
      latitude: formData.latitude,
      longitude: formData.longitude
    }

    // Submit trip data
    const result = await onSubmit(tripData)

    // Upload image if one was selected and we have a new image file
    const tripId = isEditing ? initialData?.id : result?.id
    if (selectedImage && tripId) {
      await uploadImageMutation.mutateAsync({ tripId, file: selectedImage })
    }

    // Reset form
    setFormData({
      title: '',
      destination: '',
      description: '',
      start_date: '',
      end_date: '',
      interests: [],
      budget: '',
      currency: 'EUR'
    })
    setSelectedImage(null)
    setImagePreview(null)
  }

  if (!isOpen) return null

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
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              {/* Header */}
              <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-between items-center">
                <h2 className="text-2xl font-bold">
                  {isEditing ? t('trips:editTrip') : t('trips:planNewTrip')}
                </h2>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-6 space-y-6">
                {/* Title */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    {t('trips:tripTitle')} *
                  </label>
                  <input
                    type="text"
                    name="title"
                    value={formData.title}
                    onChange={handleChange}
                    placeholder={t('trips:tripTitlePlaceholder')}
                    required
                    className="input"
                  />
                </div>

                {/* Destination */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    {t('trips:destinationLabel')} *
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      name="destination"
                      value={formData.destination}
                      onChange={handleChange}
                      onBlur={handleGeocode}
                      placeholder={t('trips:destinationPlaceholder')}
                      required
                      className="input flex-1"
                    />
                    <button
                      type="button"
                      onClick={handleGeocode}
                      disabled={geocodeMutation.isPending || !formData.destination}
                      className="btn btn-secondary"
                      title={t('trips:findOnMapTooltip')}
                    >
                      {geocodeMutation.isPending ? (
                        <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
                      ) : (
                        <MapPinIcon className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleAiSuggestions}
                      disabled={aiSuggestionsMutation.isPending || !formData.destination}
                      className="btn btn-secondary whitespace-nowrap"
                      title={t('trips:getAiSuggestionsTooltip')}
                    >
                      {aiSuggestionsMutation.isPending ? (
                        <>
                          <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
                          {t('trips:loadingAi')}
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" />
                          {t('trips:aiTips')}
                        </>
                      )}
                    </button>
                  </div>
                  {formData.latitude && formData.longitude && (
                    <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                      📍 {t('trips:coordinatesLabel')}: {formData.latitude.toFixed(4)}, {formData.longitude.toFixed(4)}
                    </div>
                  )}
                </div>

                {/* Cover Image Upload */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    {t('trips:coverImage')}
                  </label>

                  {imagePreview ? (
                    <div className="relative">
                      <img
                        src={imagePreview}
                        alt={t('trips:preview')}
                        className="w-full h-48 object-cover rounded-lg"
                      />
                      <button
                        type="button"
                        onClick={removeImage}
                        className="absolute top-2 right-2 p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center w-full h-48 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-primary-500 dark:hover:border-primary-400 transition-colors bg-gray-50 dark:bg-gray-700/50">
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <Upload className="w-10 h-10 mb-3 text-gray-400" />
                        <p className="mb-2 text-sm text-gray-500 dark:text-gray-400">
                          <span className="font-semibold">{t('trips:clickToUpload')}</span> {t('trips:orDragDrop')}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {t('trips:fileTypes')}
                        </p>
                      </div>
                      <input
                        type="file"
                        className="hidden"
                        accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
                        onChange={handleImageSelect}
                      />
                    </label>
                  )}
                </div>

                {/* Dates */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      {t('trips:startDateLabel')}
                    </label>
                    <input
                      type="date"
                      name="start_date"
                      value={formData.start_date}
                      onChange={handleChange}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      {t('trips:endDateLabel')}
                    </label>
                    <input
                      type="date"
                      name="end_date"
                      value={formData.end_date}
                      onChange={handleChange}
                      className="input"
                    />
                  </div>
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    {t('trips:descriptionLabel')}
                  </label>
                  <textarea
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    placeholder={t('trips:descriptionPlaceholder')}
                    rows={3}
                    className="input"
                  />
                </div>

                {/* Interests */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    {t('trips:interestsLabel')}
                  </label>

                  {/* Selected Interests */}
                  {formData.interests.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {formData.interests.map((interest) => (
                        <span
                          key={interest}
                          className="inline-flex items-center gap-1 px-3 py-1 bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200 rounded-full text-sm"
                        >
                          {t(`interests.${interest}`, interest)}
                          <button
                            type="button"
                            onClick={() => removeInterest(interest)}
                            className="hover:text-primary-600"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Suggestion Buttons */}
                  <div className="flex flex-wrap gap-2 mb-3">
                    {interestSuggestions
                      .filter(s => !formData.interests.includes(s))
                      .map((interest) => (
                        <button
                          key={interest}
                          type="button"
                          onClick={() => addInterest(interest)}
                          className="px-3 py-1 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-full text-sm transition-colors"
                        >
                          + {t(`interests.${interest}`, interest)}
                        </button>
                      ))}
                  </div>

                  {/* Custom Interest Input */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newInterest}
                      onChange={(e) => setNewInterest(e.target.value)}
                      placeholder={t('trips:addCustomInterest')}
                      className="input flex-1"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          handleAddCustomInterest()
                        }
                      }}
                    />
                    <button
                      type="button"
                      onClick={handleAddCustomInterest}
                      className="btn btn-secondary"
                    >
                      {t('trips:addButton')}
                    </button>
                  </div>
                </div>

                {/* Budget */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="col-span-2">
                    <label className="block text-sm font-medium mb-2">
                      {t('trips:budgetLabel')}
                    </label>
                    <input
                      type="number"
                      name="budget"
                      value={formData.budget}
                      onChange={handleChange}
                      placeholder="1000"
                      min="0"
                      step="10"
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      {t('trips:currencyLabel')}
                    </label>
                    <select
                      name="currency"
                      value={formData.currency}
                      onChange={handleChange}
                      className="input"
                    >
                      <option value="EUR">EUR (€)</option>
                      <option value="USD">USD ($)</option>
                      <option value="GBP">GBP (£)</option>
                      <option value="CHF">CHF (Fr)</option>
                      <option value="JPY">JPY (¥)</option>
                    </select>
                  </div>
                </div>

                {/* Participants */}
                {isEditing && initialData?.id && (
                  <ParticipantsManager
                    tripId={initialData.id}
                    participants={participants}
                    isEditing={isEditing}
                  />
                )}

                {/* Buttons */}
                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={onClose}
                    className="btn btn-secondary flex-1"
                  >
                    {t('common:cancel')}
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary flex-1"
                  >
                    {isEditing ? t('trips:saveChanges') : t('trips:createTrip')}
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
