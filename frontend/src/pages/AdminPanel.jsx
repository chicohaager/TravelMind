import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Users, Search, Shield, UserX, Edit2, Trash2, Check, X,
  TrendingUp, MapPin, Book, Calendar, Settings, UserPlus, Lock, Unlock
} from 'lucide-react'
import { adminService } from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'

export default function AdminPanel() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [users, setUsers] = useState([])
  const [stats, setStats] = useState(null)
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterActive, setFilterActive] = useState(null)
  const [editingUser, setEditingUser] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [showCreateUser, setShowCreateUser] = useState(false)
  const [newUserData, setNewUserData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: ''
  })

  useEffect(() => {
    // Check if user is admin
    if (!user?.is_superuser) {
      toast.error(t('admin:noPermission'))
      navigate('/')
      return
    }

    loadData()
  }, [user, navigate])

  const loadData = async () => {
    setLoading(true)
    try {
      const [usersRes, statsRes, settingsRes] = await Promise.all([
        adminService.getUsers({ search: searchTerm, is_active: filterActive }),
        adminService.getStats(),
        adminService.getSettings()
      ])
      setUsers(usersRes.data)
      setStats(statsRes.data)

      // Convert settings array to object for easier access
      const settingsObj = {}
      settingsRes.data.forEach(setting => {
        settingsObj[setting.key] = setting
      })
      setSettings(settingsObj)
    } catch (error) {
      toast.error(t('admin:errorLoadingData'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      if (user?.is_superuser) {
        loadData()
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [searchTerm, filterActive])

  const handleUpdateUser = async (userId, data) => {
    try {
      await adminService.updateUser(userId, data)
      toast.success(t('admin:userUpdated'))
      setEditingUser(null)
      loadData()
    } catch (error) {
      const message = error.response?.data?.detail || t('admin:errorUpdating')
      toast.error(message)
    }
  }

  const handleDeleteUser = async (userId) => {
    try {
      await adminService.deleteUser(userId)
      toast.success(t('admin:userDeleted'))
      setDeleteConfirm(null)
      loadData()
    } catch (error) {
      const message = error.response?.data?.detail || t('admin:errorDeleting')
      toast.error(message)
    }
  }

  const handleToggleActive = async (userId, currentStatus) => {
    try {
      await adminService.updateUser(userId, { is_active: !currentStatus })
      toast.success(currentStatus ? t('admin:userDeactivated') : t('admin:userActivated'))
      loadData()
    } catch (error) {
      toast.error(t('admin:errorUpdating'))
    }
  }

  const handleToggleAdmin = async (userId, currentStatus) => {
    try {
      await adminService.updateUser(userId, { is_superuser: !currentStatus })
      toast.success(currentStatus ? t('admin:adminRightsRemoved') : t('admin:adminRightsGranted'))
      loadData()
    } catch (error) {
      const message = error.response?.data?.detail || t('admin:errorUpdating')
      toast.error(message)
    }
  }

  const handleToggleRegistration = async () => {
    try {
      const response = await adminService.toggleRegistration()
      toast.success(response.data.message)
      loadData()
    } catch (error) {
      toast.error(t('admin:errorChangingRegistration'))
    }
  }

  const handleCreateUser = async (e) => {
    e.preventDefault()

    if (newUserData.password.length < 8) {
      toast.error(t('admin:passwordMinLength'))
      return
    }

    try {
      await adminService.createUser(newUserData)
      toast.success(t('admin:userCreated'))
      setShowCreateUser(false)
      setNewUserData({ username: '', email: '', password: '', full_name: '' })
      loadData()
    } catch (error) {
      const message = error.response?.data?.detail || t('admin:errorCreatingUser')
      toast.error(message)
    }
  }

  const handleUpdateMaxUsers = async (value) => {
    try {
      await adminService.updateSetting('max_users', {
        value: value.toString(),
        value_type: 'integer'
      })
      toast.success(t('admin:userLimitUpdated'))
      loadData()
    } catch (error) {
      toast.error(t('admin:errorUpdatingLimit'))
    }
  }

  const handleFixPlaceCoordinates = async () => {
    const loadingToast = toast.loading(t('admin:geocodingPlaces'))
    try {
      const response = await adminService.fixPlaceCoordinates()
      toast.dismiss(loadingToast)
      const { fixed_count, total_found, failed_count } = response.data

      if (fixed_count > 0) {
        toast.success(t('admin:placesGeocoded').replace('{fixed_count}', fixed_count).replace('{total_found}', total_found))
      } else if (total_found === 0) {
        toast.success(t('admin:noPlacesNeedGeocode'))
      } else {
        toast.error(t('admin:geocodingFailed').replace('{failed_count}', failed_count))
      }
    } catch (error) {
      toast.dismiss(loadingToast)
      const message = error.response?.data?.detail || t('admin:errorGeocoding')
      toast.error(message)
    }
  }

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold mb-2">{t('admin:title')}</h1>
        <p className="text-gray-600 dark:text-gray-400">
          {t('admin:systemManagement')}
        </p>
      </motion.div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="card"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 dark:bg-primary-900 rounded-lg">
                <Users className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">{t('admin:users')}</p>
                <p className="text-2xl font-bold">{stats.total_users}</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="card"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">{t('admin:active')}</p>
                <p className="text-2xl font-bold">{stats.active_users}</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="card"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <MapPin className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">{t('admin:trips')}</p>
                <p className="text-2xl font-bold">{stats.total_trips}</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="card"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                <Book className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">{t('admin:entries')}</p>
                <p className="text-2xl font-bold">{stats.total_diary_entries}</p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="card"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 dark:bg-orange-900 rounded-lg">
                <Calendar className="w-5 h-5 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">{t('admin:places')}</p>
                <p className="text-2xl font-bold">{stats.total_places}</p>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Settings Management */}
      {settings && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="card mb-8"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Settings className="w-6 h-6" />
              {t('admin:systemSettings')}
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Registration Toggle */}
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {settings.registration_open?.value === 'true' ? (
                    <Unlock className="w-5 h-5 text-green-600 dark:text-green-400" />
                  ) : (
                    <Lock className="w-5 h-5 text-red-600 dark:text-red-400" />
                  )}
                  <h3 className="font-semibold">{t('admin:registration')}</h3>
                </div>
                <button
                  onClick={handleToggleRegistration}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    settings.registration_open?.value === 'true'
                      ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-800'
                      : 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-800'
                  }`}
                >
                  {settings.registration_open?.value === 'true' ? t('admin:open') : t('admin:closed')}
                </button>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {settings.registration_open?.description || t('admin:registrationDescription')}
              </p>
            </div>

            {/* Max Users Setting */}
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  <h3 className="font-semibold">{t('admin:userLimit')}</h3>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="0"
                    value={settings.max_users?.value || '0'}
                    onChange={(e) => handleUpdateMaxUsers(e.target.value)}
                    className="input w-24 text-center"
                  />
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {t('admin:currentUsers').replace('{count}', stats?.total_users || 0)} {settings.max_users?.value > 0 ? `/ ${settings.max_users.value}` : `(${t('admin:unlimited')})`}
              </p>
            </div>

            {/* Create User Button */}
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <button
                onClick={() => setShowCreateUser(true)}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                <UserPlus className="w-5 h-5" />
                {t('admin:createNewUser')}
              </button>
            </div>

            {/* Fix Place Coordinates Button */}
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <button
                onClick={handleFixPlaceCoordinates}
                className="btn-outline w-full flex items-center justify-center gap-2"
              >
                <MapPin className="w-5 h-5" />
                {t('admin:geocodePlaces')}
              </button>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
                {t('admin:geocodePlacesDescription')}
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* User Management */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="card"
      >
        <h2 className="text-xl font-bold mb-6">{t('admin:userManagement')}</h2>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={t('admin:searchPlaceholder')}
              className="input w-full pl-10"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setFilterActive(null)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterActive === null
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              {t('admin:all')}
            </button>
            <button
              onClick={() => setFilterActive(true)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterActive === true
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              {t('admin:activeFilter')}
            </button>
            <button
              onClick={() => setFilterActive(false)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterActive === false
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              {t('admin:inactiveFilter')}
            </button>
          </div>
        </div>

        {/* Users Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th className="text-left py-3 px-4 font-semibold text-sm">{t('admin:user')}</th>
                <th className="text-left py-3 px-4 font-semibold text-sm">{t('admin:email')}</th>
                <th className="text-center py-3 px-4 font-semibold text-sm">{t('admin:status')}</th>
                <th className="text-center py-3 px-4 font-semibold text-sm">{t('admin:statistics')}</th>
                <th className="text-right py-3 px-4 font-semibold text-sm">{t('admin:actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      {u.avatar_url ? (
                        <img
                          src={u.avatar_url}
                          alt={u.username}
                          className="w-10 h-10 rounded-full object-cover"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-primary-200 dark:bg-primary-800 flex items-center justify-center">
                          <span className="font-semibold text-primary-700 dark:text-primary-300">
                            {u.username[0].toUpperCase()}
                          </span>
                        </div>
                      )}
                      <div>
                        <p className="font-medium">{u.username}</p>
                        {u.full_name && (
                          <p className="text-sm text-gray-600 dark:text-gray-400">{u.full_name}</p>
                        )}
                      </div>
                    </div>
                  </td>

                  <td className="py-3 px-4">
                    <p className="text-sm">{u.email}</p>
                  </td>

                  <td className="py-3 px-4">
                    <div className="flex items-center justify-center gap-2">
                      {u.is_active ? (
                        <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 text-xs font-medium rounded-full">
                          {t('admin:active')}
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 text-xs font-medium rounded-full">
                          {t('admin:inactive')}
                        </span>
                      )}
                      {u.is_superuser && (
                        <span className="px-2 py-1 bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 text-xs font-medium rounded-full">
                          {t('admin:admin')}
                        </span>
                      )}
                    </div>
                  </td>

                  <td className="py-3 px-4">
                    <div className="flex items-center justify-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                      <div className="flex items-center gap-1">
                        <MapPin className="w-4 h-4" />
                        <span>{u.trip_count || 0}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Book className="w-4 h-4" />
                        <span>{u.diary_count || 0}</span>
                      </div>
                    </div>
                  </td>

                  <td className="py-3 px-4">
                    <div className="flex items-center justify-end gap-2">
                      {/* Toggle Active */}
                      <button
                        onClick={() => handleToggleActive(u.id, u.is_active)}
                        className={`p-1.5 rounded-lg transition-colors ${
                          u.is_active
                            ? 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-800'
                            : 'bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-800'
                        }`}
                        title={u.is_active ? t('admin:deactivate') : t('admin:activate')}
                      >
                        {u.is_active ? <Check className="w-4 h-4" /> : <UserX className="w-4 h-4" />}
                      </button>

                      {/* Toggle Admin */}
                      {u.id !== user.id && (
                        <button
                          onClick={() => handleToggleAdmin(u.id, u.is_superuser)}
                          className={`p-1.5 rounded-lg transition-colors ${
                            u.is_superuser
                              ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400 hover:bg-primary-200 dark:hover:bg-primary-800'
                              : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                          }`}
                          title={u.is_superuser ? t('admin:removeAdmin') : t('admin:makeAdmin')}
                        >
                          <Shield className="w-4 h-4" />
                        </button>
                      )}

                      {/* Delete */}
                      {u.id !== user.id && (
                        <button
                          onClick={() => setDeleteConfirm(u.id)}
                          className="p-1.5 rounded-lg bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-800 transition-colors"
                          title={t('admin:delete')}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {users.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              {t('admin:noUsersFound')}
            </div>
          )}
        </div>
      </motion.div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-md w-full"
          >
            <h3 className="text-xl font-bold mb-4">{t('admin:deleteUser')}</h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {t('admin:deleteUserConfirm')}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="btn-outline flex-1"
              >
                {t('admin:cancel')}
              </button>
              <button
                onClick={() => handleDeleteUser(deleteConfirm)}
                className="btn bg-red-600 hover:bg-red-700 text-white flex-1"
              >
                {t('admin:delete')}
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Create User Modal */}
      {showCreateUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-md w-full"
          >
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <UserPlus className="w-6 h-6" />
              {t('admin:createNewUser')}
            </h3>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">{t('admin:username')} *</label>
                <input
                  type="text"
                  value={newUserData.username}
                  onChange={(e) => setNewUserData({ ...newUserData, username: e.target.value })}
                  className="input w-full"
                  required
                  minLength={3}
                  placeholder={t('admin:usernamePlaceholder')}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">{t('admin:email')} *</label>
                <input
                  type="email"
                  value={newUserData.email}
                  onChange={(e) => setNewUserData({ ...newUserData, email: e.target.value })}
                  className="input w-full"
                  required
                  placeholder={t('admin:emailPlaceholder')}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">{t('admin:password')} *</label>
                <input
                  type="password"
                  value={newUserData.password}
                  onChange={(e) => setNewUserData({ ...newUserData, password: e.target.value })}
                  className="input w-full"
                  required
                  minLength={8}
                  placeholder={t('admin:passwordMinChars')}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">{t('admin:fullName')}</label>
                <input
                  type="text"
                  value={newUserData.full_name}
                  onChange={(e) => setNewUserData({ ...newUserData, full_name: e.target.value })}
                  className="input w-full"
                  placeholder={t('admin:fullNamePlaceholder')}
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateUser(false)
                    setNewUserData({ username: '', email: '', password: '', full_name: '' })
                  }}
                  className="btn-outline flex-1"
                >
                  {t('admin:cancel')}
                </button>
                <button
                  type="submit"
                  className="btn-primary flex-1"
                >
                  {t('admin:create')}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  )
}
