import { useState, useEffect, useRef, useMemo } from 'react'
import { X, MapPin, Star, Calendar, DollarSign, Sparkles, Lightbulb, Image, Upload } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import { tripsService, aiService, placesService } from '@services/api'
import toast from 'react-hot-toast'
import NativeCamera from './NativeCamera'
import { useTranslation } from 'react-i18next'

export default function PlaceModal({ isOpen, onClose, onSubmit, initialData = null, tripDestination, placeId = null }) {
  const { t } = useTranslation()

  const categories = [
    { value: 'sight', labelKey: 'places.categories.sight', icon: '🏛️' },
    { value: 'restaurant', labelKey: 'places.categories.restaurant', icon: '🍽️' },
    { value: 'hotel', labelKey: 'places.categories.hotel', icon: '🏨' },
    { value: 'activity', labelKey: 'places.categories.activity', icon: '🎯' },
    { value: 'shopping', labelKey: 'places.categories.shopping', icon: '🛍️' },
    { value: 'transport', labelKey: 'places.categories.transport', icon: '🚌' }
  ]
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    address: '',
    latitude: 0,
    longitude: 0,
    category: 'sight',
    visit_date: '',
    visited: false,
    website: '',
    phone: '',
    cost: '',
    currency: 'EUR',
    rating: 0,
    notes: '',
    photos: []
  })
  const [aiSuggestions, setAiSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [uploadingPhoto, setUploadingPhoto] = useState(false)

  // Create preview URLs with automatic cleanup
  const previewUrls = useMemo(() => {
    return selectedFiles.map(file => URL.createObjectURL(file))
  }, [selectedFiles])

  // Cleanup blob URLs on unmount or when files change
  useEffect(() => {
    return () => {
      previewUrls.forEach(url => URL.revokeObjectURL(url))
    }
  }, [previewUrls])

  // Geocoding mutation
  const geocodeMutation = useMutation({
    mutationFn: async (location) => {
      const response = await tripsService.geocode(location)
      return response.data
    },
    onSuccess: (data) => {
      setFormData((prev) => ({
        ...prev,
        latitude: data.latitude,
        longitude: data.longitude,
        address: prev.address || data.display_name
      }))
      toast.success(t('places:coordinatesFound'))
    },
    onError: () => {
      toast.error(t('places:coordinatesNotFound'))
    }
  })

  // AI suggestions mutation
  const aiSuggestionsMutation = useMutation({
    mutationFn: async ({ destination, category }) => {
      const categoryMap = {
        'sight': 'sights',
        'restaurant': 'restaurants',
        'activity': 'activities',
        'hotel': 'restaurants',
        'shopping': 'activities',
        'transport': 'activities'
      }
      const response = await aiService.localTips(destination, categoryMap[category] || 'all')
      return response.data
    },
    onSuccess: (data) => {
      if (data.tips && Array.isArray(data.tips)) {
        setAiSuggestions(data.tips)
        setShowSuggestions(true)
        toast.success(t('places:aiSuggestionsLoaded').replace('{count}', data.tips.length))
      } else {
        toast.error(t('places:noSuggestionsFound'))
      }
    },
    onError: () => {
      toast.error(t('places:aiSuggestionsError'))
    }
  })

  useEffect(() => {
    if (initialData) {
      setFormData({
        name: initialData.name || '',
        description: initialData.description || '',
        address: initialData.address || '',
        latitude: initialData.latitude || 0,
        longitude: initialData.longitude || 0,
        category: initialData.category || 'sight',
        visit_date: initialData.visit_date
          ? new Date(initialData.visit_date).toISOString().split('T')[0]
          : '',
        visited: initialData.visited || false,
        website: initialData.website || '',
        phone: initialData.phone || '',
        cost: initialData.cost || '',
        currency: initialData.currency || 'EUR',
        rating: initialData.rating || 0,
        notes: initialData.notes || ''
      })
    } else if (!isOpen) {
      // Reset form
      setFormData({
        name: '',
        description: '',
        address: '',
        latitude: 0,
        longitude: 0,
        category: 'sight',
        visit_date: '',
        visited: false,
        website: '',
        phone: '',
        cost: '',
        currency: 'EUR',
        rating: 0,
        notes: ''
      })
    }
  }, [initialData, isOpen])

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const handleGeocode = () => {
    const location = formData.name + (formData.address ? ', ' + formData.address : '') + (tripDestination ? ', ' + tripDestination : '')
    if (location.trim()) {
      geocodeMutation.mutate(location.trim())
    }
  }

  const handleAiSuggestions = () => {
    if (!tripDestination) {
      toast.error(t('places:noDestination'))
      return
    }
    aiSuggestionsMutation.mutate({
      destination: tripDestination,
      category: formData.category
    })
  }

  const handleSelectSuggestion = (suggestion) => {
    setFormData((prev) => ({
      ...prev,
      name: suggestion.name || prev.name,
      description: suggestion.description || prev.description,
      address: suggestion.location || prev.address,
      latitude: suggestion.coordinates?.lat || prev.latitude,
      longitude: suggestion.coordinates?.lng || prev.longitude,
      notes: suggestion.insider_tip || prev.notes
    }))
    setShowSuggestions(false)
    toast.success(t('places:suggestionApplied'))
  }

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files)
    if (files.length > 0) {
      setSelectedFiles((prev) => [...prev, ...files])
    }
  }

  const removeSelectedFile = (index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const removeExistingPhoto = (photoUrl) => {
    setFormData((prev) => ({
      ...prev,
      photos: prev.photos.filter((p) => p !== photoUrl)
    }))
  }

  const handleCameraPhoto = (photoData) => {
    setSelectedFiles((prev) => [...prev, photoData.file])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    const placeData = {
      ...formData,
      latitude: parseFloat(formData.latitude) || 0,
      longitude: parseFloat(formData.longitude) || 0,
      cost: formData.cost ? parseFloat(formData.cost) : null,
      visit_date: formData.visit_date ? `${formData.visit_date}T00:00:00` : null,
      rating: formData.rating || null
    }

    try {
      // Submit place data
      const result = await onSubmit(placeData)

      // Upload new photos if any
      if (selectedFiles.length > 0) {
        const savedPlaceId = placeId || result?.data?.id || result?.id

        if (savedPlaceId) {
          setUploadingPhoto(true)

          // Upload each photo
          for (const file of selectedFiles) {
            try {
              await placesService.uploadPhoto(savedPlaceId, file)
            } catch (error) {
              console.error('Error uploading photo:', error)
              toast.error(t('places:photoUploadError').replace('{fileName}', file.name))
            }
          }

          setUploadingPhoto(false)
          toast.success(t('places:photosUploaded').replace('{count}', selectedFiles.length))
        }
      }

      // Reset form
      setFormData({
        name: '',
        description: '',
        address: '',
        latitude: 0,
        longitude: 0,
        category: 'sight',
        visit_date: '',
        visited: false,
        website: '',
        phone: '',
        cost: '',
        currency: 'EUR',
        rating: 0,
        notes: '',
        photos: []
      })
      setSelectedFiles([])
    } catch (error) {
      console.error('Error submitting place:', error)
      setUploadingPhoto(false)
    }
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
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9998]"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-[9998] flex items-center justify-center p-2 sm:p-4 pointer-events-none"
          >
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[95vh] sm:max-h-[90vh] overflow-y-auto pointer-events-auto">
              {/* Header */}
              <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-3 sm:px-6 py-3 sm:py-4 flex justify-between items-center z-10">
                <h2 className="text-lg sm:text-2xl font-bold truncate pr-2">
                  {initialData ? t('places:editPlace') : t('places:newPlace')}
                </h2>
                <div className="flex gap-2">
                  {!initialData && tripDestination && (
                    <button
                      type="button"
                      onClick={handleAiSuggestions}
                      disabled={aiSuggestionsMutation.isPending}
                      className="btn btn-secondary"
                      title={t('places:aiSuggestionsButton')}
                    >
                      {aiSuggestionsMutation.isPending ? (
                        <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
                      ) : (
                        <>
                          <Lightbulb className="w-4 h-4" />
                          <span className="hidden sm:inline ml-2">{t('places:aiSuggestionsButton')}</span>
                        </>
                      )}
                    </button>
                  )}
                  <button
                    onClick={onClose}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>
              </div>

              {/* AI Suggestions Panel */}
              {showSuggestions && aiSuggestions.length > 0 && (
                <div className="p-6 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="font-bold text-lg flex items-center gap-2">
                      <Lightbulb className="w-5 h-5 text-blue-600" />
                      {t('places:aiSuggestionsTitle').replace('{destination}', tripDestination)}
                    </h3>
                    <button
                      type="button"
                      onClick={() => setShowSuggestions(false)}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      {t('places:hideButton')}
                    </button>
                  </div>
                  <div className="grid grid-cols-1 gap-3 max-h-60 overflow-y-auto">
                    {aiSuggestions.slice(0, 5).map((suggestion, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                        onClick={() => handleSelectSuggestion(suggestion)}
                      >
                        <div className="font-semibold text-sm">{suggestion.name}</div>
                        <div className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2 mt-1">
                          {suggestion.description || suggestion.why_special}
                        </div>
                        {suggestion.insider_tip && (
                          <div className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                            💡 {suggestion.insider_tip}
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-6 space-y-6">
                {/* Name & Category */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('places:placeName')} *</label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      placeholder={t('places:namePlaceholder')}
                      required
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('places:categoryLabel')}</label>
                    <select name="category" value={formData.category} onChange={handleChange} className="input">
                      {categories.map((cat) => (
                        <option key={cat.value} value={cat.value}>
                          {cat.icon} {t(cat.labelKey)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('places:descriptionLabel')}</label>
                  <textarea
                    name="description"
                    value={formData.description}
                    onChange={handleChange}
                    placeholder={t('places:descriptionPlaceholder')}
                    rows={3}
                    className="input"
                  />
                </div>

                {/* Address & Geocode */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    <MapPin className="w-4 h-4 inline mr-1" />
                    {t('places:addressLabel')}
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      name="address"
                      value={formData.address}
                      onChange={handleChange}
                      placeholder={t('places:addressPlaceholder')}
                      className="input flex-1"
                    />
                    <button
                      type="button"
                      onClick={handleGeocode}
                      disabled={geocodeMutation.isPending}
                      className="btn btn-secondary"
                      title={t('places:findCoordinatesTitle')}
                    >
                      {geocodeMutation.isPending ? (
                        <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
                      ) : (
                        <Sparkles className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Coordinates */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('places:latitude')}</label>
                    <input
                      type="number"
                      name="latitude"
                      value={formData.latitude}
                      onChange={handleChange}
                      step="0.000001"
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('places:longitude')}</label>
                    <input
                      type="number"
                      name="longitude"
                      value={formData.longitude}
                      onChange={handleChange}
                      step="0.000001"
                      className="input"
                    />
                  </div>
                </div>

                {/* Date & Cost */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      <Calendar className="w-4 h-4 inline mr-1" />
                      {t('places:visitDateLabel')}
                    </label>
                    <input
                      type="date"
                      name="visit_date"
                      value={formData.visit_date}
                      onChange={handleChange}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      <DollarSign className="w-4 h-4 inline mr-1" />
                      {t('places:costLabel')}
                    </label>
                    <input
                      type="number"
                      name="cost"
                      value={formData.cost}
                      onChange={handleChange}
                      placeholder="0"
                      step="0.01"
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('places:currencyLabel')}</label>
                    <select name="currency" value={formData.currency} onChange={handleChange} className="input">
                      <option value="EUR">EUR (€)</option>
                      <option value="USD">USD ($)</option>
                      <option value="GBP">GBP (£)</option>
                    </select>
                  </div>
                </div>

                {/* Rating */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('places:ratingLabel')}</label>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setFormData((prev) => ({ ...prev, rating: prev.rating === star ? 0 : star }))}
                        className="transition-colors"
                      >
                        <Star
                          className={`w-8 h-8 ${
                            star <= formData.rating
                              ? 'fill-yellow-400 text-yellow-400'
                              : 'text-gray-300 dark:text-gray-600 hover:text-yellow-300'
                          }`}
                        />
                      </button>
                    ))}
                  </div>
                </div>

                {/* Website & Phone */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('places:websiteLabel')}</label>
                    <input
                      type="url"
                      name="website"
                      value={formData.website}
                      onChange={handleChange}
                      placeholder={t('places:websitePlaceholder')}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('places:phoneLabel')}</label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      placeholder={t('places:phonePlaceholder')}
                      className="input"
                    />
                  </div>
                </div>

                {/* Notes */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('places:notesLabel')}</label>
                  <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    placeholder={t('places:notesPlaceholder')}
                    rows={2}
                    className="input"
                  />
                </div>

                {/* Photos */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    <Image className="w-4 h-4 inline mr-1" />
                    {t('places:photos')}
                  </label>

                  {/* Existing Photos */}
                  {formData.photos && formData.photos.length > 0 && (
                    <div className="grid grid-cols-3 gap-2 mb-3">
                      {formData.photos.map((photoUrl, index) => (
                        <div key={index} className="relative group">
                          <img
                            src={photoUrl}
                            alt={t('places:photoLabel').replace('{index}', index + 1)}
                            className="w-full h-24 object-cover rounded-lg"
                          />
                          <button
                            type="button"
                            onClick={() => removeExistingPhoto(photoUrl)}
                            className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Selected Files Preview */}
                  {selectedFiles.length > 0 && (
                    <div className="grid grid-cols-3 gap-2 mb-3">
                      {selectedFiles.map((file, index) => (
                        <div key={index} className="relative group">
                          <img
                            src={previewUrls[index]}
                            alt={`${t('places:newPhotoLabel')} ${index + 1}`}
                            className="w-full h-24 object-cover rounded-lg border-2 border-blue-500"
                          />
                          <button
                            type="button"
                            onClick={() => removeSelectedFile(index)}
                            className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <X className="w-4 h-4" />
                          </button>
                          <span className="absolute bottom-1 left-1 px-2 py-1 bg-blue-500 text-white text-xs rounded">
                            {t('places:newPhotoLabel')}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* File Input */}
                  <label className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors">
                    <Upload className="w-5 h-5 text-gray-500" />
                    <span className="text-sm text-gray-600">{t('places:selectPhotos')}</span>
                    <input
                      type="file"
                      accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
                      multiple
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                  </label>

                  {/* Native Camera */}
                  <div className="mt-3">
                    <NativeCamera
                      onPhotoTaken={handleCameraPhoto}
                      disabled={uploadingPhoto}
                    />
                  </div>

                  <p className="text-xs text-gray-500 mt-2">
                    {t('places:fileTypesInfo')}
                  </p>
                </div>

                {/* Visited Checkbox */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    name="visited"
                    checked={formData.visited}
                    onChange={handleChange}
                    className="w-4 h-4 rounded border-gray-300"
                  />
                  <label className="text-sm font-medium">{t('places:alreadyVisited')}</label>
                </div>

                {/* Buttons */}
                <div className="flex gap-3 pt-4">
                  <button type="button" onClick={onClose} className="btn btn-secondary flex-1">
                    {t('common:cancel')}
                  </button>
                  <button type="submit" className="btn btn-primary flex-1">
                    {initialData ? t('places:savePlace') : t('places:addPlace')}
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
