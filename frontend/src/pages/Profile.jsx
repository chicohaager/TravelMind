import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { User, Mail, Calendar, Edit2, Camera, Save, X } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { usersService } from '@/services/api'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'

export default function Profile() {
  const { t } = useTranslation()
  const { user, loadUser } = useAuth()
  const [isEditing, setIsEditing] = useState(false)
  const [loading, setLoading] = useState(false)
  const fileInputRef = useRef(null)

  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    bio: user?.bio || '',
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      await usersService.updateProfile(formData)
      await loadUser()
      toast.success(t('profile:profileUpdated'))
      setIsEditing(false)
    } catch (error) {
      const message = error.response?.data?.detail || t('profile:updateError')
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  const handleAvatarUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error(t('profile:fileTooLarge'))
      return
    }

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    if (!allowedTypes.includes(file.type)) {
      toast.error(t('settings:onlyImageFiles'))
      return
    }

    setLoading(true)

    try {
      await usersService.uploadAvatar(file)
      await loadUser()
      toast.success(t('profile:avatarUploaded'))
    } catch (error) {
      const message = error.response?.data?.detail || t('profile:uploadError')
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('de-DE', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold mb-2">{t('profile:myProfile')}</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Verwalte deine persönlichen Informationen
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Avatar Card */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-1"
        >
          <div className="card text-center">
            <div className="relative inline-block">
              {user.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.username}
                  className="w-32 h-32 rounded-full mx-auto object-cover border-4 border-primary-100 dark:border-primary-900"
                />
              ) : (
                <div className="w-32 h-32 rounded-full mx-auto bg-gradient-to-br from-primary-400 to-secondary-400 flex items-center justify-center border-4 border-primary-100 dark:border-primary-900">
                  <User className="w-16 h-16 text-white" />
                </div>
              )}

              {/* Camera Button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                className="absolute bottom-0 right-0 bg-primary-600 hover:bg-primary-700 text-white rounded-full p-2 shadow-lg transition-colors disabled:opacity-50"
              >
                <Camera className="w-4 h-4" />
              </button>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleAvatarUpload}
                className="hidden"
              />
            </div>

            <h2 className="text-xl font-bold mt-4">{user.username}</h2>
            {user.full_name && (
              <p className="text-gray-600 dark:text-gray-400">{user.full_name}</p>
            )}

            {user.is_superuser && (
              <span className="inline-block mt-2 px-3 py-1 bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200 rounded-full text-sm font-medium">
                Admin
              </span>
            )}

            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400">
              <div className="flex items-center justify-center gap-2">
                <Calendar className="w-4 h-4" />
                <span>Mitglied seit {formatDate(user.created_at)}</span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Profile Info Card */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-2"
        >
          <div className="card">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold">{t('profile:profileInformation')}</h3>

              {!isEditing ? (
                <button
                  onClick={() => {
                    setFormData({
                      full_name: user.full_name || '',
                      email: user.email || '',
                      bio: user.bio || '',
                    })
                    setIsEditing(true)
                  }}
                  className="btn-outline flex items-center gap-2"
                >
                  <Edit2 className="w-4 h-4" />
                  Bearbeiten
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => setIsEditing(false)}
                    className="btn-outline flex items-center gap-2"
                    disabled={loading}
                  >
                    <X className="w-4 h-4" />
                    Abbrechen
                  </button>
                  <button
                    onClick={handleSubmit}
                    className="btn-primary flex items-center gap-2"
                    disabled={loading}
                  >
                    <Save className="w-4 h-4" />
                    {t('common:save')}
                  </button>
                </div>
              )}
            </div>

            {!isEditing ? (
              // View Mode
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t('profile:username')}
                  </label>
                  <div className="flex items-center gap-2 text-gray-900 dark:text-gray-100">
                    <User className="w-4 h-4 text-gray-400" />
                    {user.username}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    E-Mail
                  </label>
                  <div className="flex items-center gap-2 text-gray-900 dark:text-gray-100">
                    <Mail className="w-4 h-4 text-gray-400" />
                    {user.email}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Vollständiger Name
                  </label>
                  <div className="text-gray-900 dark:text-gray-100">
                    {user.full_name || <span className="text-gray-400 italic">{t('profile:notSpecified')}</span>}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Über mich
                  </label>
                  <div className="text-gray-900 dark:text-gray-100">
                    {user.bio || <span className="text-gray-400 italic">{t('profile:noDescription')}</span>}
                  </div>
                </div>
              </div>
            ) : (
              // Edit Mode
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Vollständiger Name
                  </label>
                  <input
                    type="text"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    className="input w-full"
                    placeholder="Max Mustermann"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    E-Mail
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="input w-full"
                    placeholder="max@example.com"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Über mich
                  </label>
                  <textarea
                    value={formData.bio}
                    onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                    className="input w-full"
                    rows="4"
                    maxLength="500"
                    placeholder="Erzähle etwas über dich..."
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    {formData.bio?.length || 0} / 500 Zeichen
                  </p>
                </div>
              </form>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
