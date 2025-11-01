import { useState, useEffect, useMemo } from 'react'
import { X, Calendar, MapPin, Star, Tag, Smile, Meh, Frown, Image, Upload } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { diaryService } from '@services/api'
import toast from 'react-hot-toast'
import AudioRecorder from './AudioRecorder'
import NativeCamera from './NativeCamera'
import { useTranslation } from 'react-i18next'

export default function DiaryModal({ isOpen, onClose, onSubmit, initialData = null, entryId = null }) {
  const { t } = useTranslation()

  const moodOptions = [
    { value: 'happy', icon: Smile, labelKey: 'diary.moodHappy', color: 'text-green-500' },
    { value: 'neutral', icon: Meh, labelKey: 'diary.moodNeutral', color: 'text-yellow-500' },
    { value: 'sad', icon: Frown, labelKey: 'diary.moodSad', color: 'text-red-500' }
  ]
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    entry_date: new Date().toISOString().split('T')[0],
    location_name: '',
    mood: '',
    rating: 0,
    tags: [],
    photos: []
  })

  const [newTag, setNewTag] = useState('')
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

  useEffect(() => {
    if (initialData) {
      setFormData({
        title: initialData.title || '',
        content: initialData.content || '',
        entry_date: initialData.entry_date
          ? new Date(initialData.entry_date).toISOString().split('T')[0]
          : new Date().toISOString().split('T')[0],
        location_name: initialData.location_name || '',
        mood: initialData.mood || '',
        rating: initialData.rating || 0,
        tags: initialData.tags || [],
        photos: initialData.photos || []
      })
    } else if (!isOpen) {
      // Reset form when modal closes
      setFormData({
        title: '',
        content: '',
        entry_date: new Date().toISOString().split('T')[0],
        location_name: '',
        mood: '',
        rating: 0,
        tags: [],
        photos: []
      })
      setSelectedFiles([])
    }
  }, [initialData, isOpen])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const addTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData((prev) => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()]
      }))
      setNewTag('')
    }
  }

  const removeTag = (tag) => {
    setFormData((prev) => ({
      ...prev,
      tags: prev.tags.filter((t) => t !== tag)
    }))
  }

  const handleTranscriptReceived = (text) => {
    // Append transcribed text to content
    setFormData((prev) => ({
      ...prev,
      content: prev.content ? prev.content + '\n\n' + text : text
    }))
    toast.success(t('diary.audioTranscribed'))
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

    const entryData = {
      ...formData,
      entry_date: formData.entry_date ? `${formData.entry_date}T00:00:00` : null,
      rating: formData.rating || null
    }

    try {
      // Submit entry data
      const result = await onSubmit(entryData)

      // Upload new photos if any
      if (selectedFiles.length > 0) {
        const savedEntryId = entryId || result?.data?.id || result?.id

        if (savedEntryId) {
          setUploadingPhoto(true)

          // Upload each photo
          for (const file of selectedFiles) {
            try {
              await diaryService.uploadPhoto(savedEntryId, file)
            } catch (error) {
              console.error('Error uploading photo:', error)
              toast.error(t('diary.photoUploadError').replace('{fileName}', file.name))
            }
          }

          setUploadingPhoto(false)
          toast.success(t('diary.photosUploaded').replace('{count}', selectedFiles.length))
        }
      }

      // Reset form
      setFormData({
        title: '',
        content: '',
        entry_date: new Date().toISOString().split('T')[0],
        location_name: '',
        mood: '',
        rating: 0,
        tags: [],
        photos: []
      })
      setSelectedFiles([])
    } catch (error) {
      console.error('Error submitting diary entry:', error)
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
            className="fixed inset-0 bg-black/50 z-40"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4"
          >
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[95vh] sm:max-h-[90vh] overflow-y-auto">
              {/* Header */}
              <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-3 sm:px-6 py-3 sm:py-4 flex justify-between items-center z-10">
                <h2 className="text-lg sm:text-2xl font-bold truncate pr-2">
                  {initialData ? t('diary.editEntry') : t('diary.newEntry')}
                </h2>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-3 sm:p-6 space-y-4 sm:space-y-6">
                {/* Title */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('diary.entryTitle')} *</label>
                  <input
                    type="text"
                    name="title"
                    value={formData.title}
                    onChange={handleChange}
                    placeholder={t('diary.titlePlaceholder')}
                    required
                    className="input"
                  />
                </div>

                {/* Date and Location */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      <Calendar className="w-4 h-4 inline mr-1" />
                      {t('diary.entryDate')}
                    </label>
                    <input
                      type="date"
                      name="entry_date"
                      value={formData.entry_date}
                      onChange={handleChange}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      <MapPin className="w-4 h-4 inline mr-1" />
                      {t('diary.location')}
                    </label>
                    <input
                      type="text"
                      name="location_name"
                      value={formData.location_name}
                      onChange={handleChange}
                      placeholder={t('diary.locationPlaceholder')}
                      className="input"
                    />
                  </div>
                </div>

                {/* Content */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('diary.content')} *</label>
                  <textarea
                    name="content"
                    value={formData.content}
                    onChange={handleChange}
                    placeholder={t('diary.entryPlaceholder')}
                    rows={8}
                    required
                    className="input"
                  />

                  {/* Audio Recording */}
                  <div className="mt-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <label className="block text-sm font-medium mb-3">{t('diary.voiceInputLabel')}</label>
                    <AudioRecorder onTranscriptReceived={handleTranscriptReceived} />
                  </div>
                </div>

                {/* Mood */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('diary.mood')}</label>
                  <div className="flex gap-4">
                    {moodOptions.map((mood) => (
                      <button
                        key={mood.value}
                        type="button"
                        onClick={() =>
                          setFormData((prev) => ({
                            ...prev,
                            mood: prev.mood === mood.value ? '' : mood.value
                          }))
                        }
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg border-2 transition-colors ${
                          formData.mood === mood.value
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <mood.icon className={`w-5 h-5 ${mood.color}`} />
                        <span className="text-sm">{t(mood.labelKey)}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Rating */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('diary.rating')}</label>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() =>
                          setFormData((prev) => ({
                            ...prev,
                            rating: prev.rating === star ? 0 : star
                          }))
                        }
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

                {/* Tags */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    <Tag className="w-4 h-4 inline mr-1" />
                    {t('diary.tags')}
                  </label>

                  {/* Selected Tags */}
                  {formData.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {formData.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-sm"
                        >
                          {tag}
                          <button
                            type="button"
                            onClick={() => removeTag(tag)}
                            className="hover:text-red-600"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Add Tag */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newTag}
                      onChange={(e) => setNewTag(e.target.value)}
                      placeholder={t('diary.addTagPlaceholder')}
                      className="input flex-1"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          addTag()
                        }
                      }}
                    />
                    <button type="button" onClick={addTag} className="btn btn-secondary">
                      {t('common.add')}
                    </button>
                  </div>
                </div>

                {/* Photos */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    <Image className="w-4 h-4 inline mr-1" />
                    {t('diary.photos')}
                  </label>

                  {/* Existing Photos */}
                  {formData.photos && formData.photos.length > 0 && (
                    <div className="grid grid-cols-3 gap-2 mb-3">
                      {formData.photos.map((photoUrl, index) => (
                        <div key={index} className="relative group">
                          <img
                            src={photoUrl}
                            alt={t('diary.photoLabel').replace('{index}', index + 1)}
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
                            alt={`${t('diary.newPhotoLabel')} ${index + 1}`}
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
                            {t('diary.newPhotoLabel')}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* File Input */}
                  <label className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors">
                    <Upload className="w-5 h-5 text-gray-500" />
                    <span className="text-sm text-gray-600">{t('diary.selectPhotos')}</span>
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
                    {t('diary.fileTypesInfo')}
                  </p>
                </div>

                {/* Buttons */}
                <div className="flex gap-3 pt-4">
                  <button type="button" onClick={onClose} className="btn btn-secondary flex-1">
                    {t('common.cancel')}
                  </button>
                  <button type="submit" className="btn btn-primary flex-1">
                    {initialData ? t('diary.saveEntry') : t('diary.createEntryButton')}
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
