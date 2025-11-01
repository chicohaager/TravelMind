import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { UserPlus, Loader, Lock, AlertCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { authService } from '@/services/api'
import { useTranslation } from 'react-i18next'

export default function Register() {
  const navigate = useNavigate()
  const { register, isAuthenticated } = useAuth()
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [registrationStatus, setRegistrationStatus] = useState(null)
  const [checkingStatus, setCheckingStatus] = useState(true)

  // Check registration status
  useEffect(() => {
    const checkRegistrationStatus = async () => {
      try {
        const response = await authService.getRegistrationStatus()
        setRegistrationStatus(response.data)
      } catch (error) {
        console.error('Failed to check registration status:', error)
      } finally {
        setCheckingStatus(false)
      }
    }

    checkRegistrationStatus()
  }, [])

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/trips', { replace: true })
    }
  }, [isAuthenticated, navigate])

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    // Validate passwords match
    if (formData.password !== formData.confirmPassword) {
      setError(t('auth.passwordsDoNotMatch'))
      return
    }

    // Validate password length
    if (formData.password.length < 8) {
      setError(t('auth.passwordTooShort'))
      return
    }

    setLoading(true)

    const success = await register(
      formData.username,
      formData.email,
      formData.password,
      formData.fullName
    )

    if (success) {
      navigate('/trips')
    }

    setLoading(false)
  }

  // Show loading while checking status
  if (checkingStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  // Show closed message if registration is closed
  const isRegistrationClosed = registrationStatus && !registrationStatus.registration_open

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-secondary-50 dark:from-gray-900 dark:to-gray-800 px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="card p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
              className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 ${
                isRegistrationClosed
                  ? 'bg-gradient-to-br from-red-500 to-orange-500'
                  : 'bg-gradient-to-br from-primary-500 to-secondary-500'
              }`}
            >
              {isRegistrationClosed ? (
                <Lock className="w-8 h-8 text-white" />
              ) : (
                <UserPlus className="w-8 h-8 text-white" />
              )}
            </motion.div>
            <h1 className="text-3xl font-bold mb-2">
              {isRegistrationClosed ? t('auth.registrationClosed') : t('auth.createYourAccount')}
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              {isRegistrationClosed
                ? registrationStatus.message
                : `${t('auth.startYourJourney')} ${registrationStatus?.app_name || 'TravelMind'}`}
            </p>
          </div>

          {/* Closed Message */}
          {isRegistrationClosed ? (
            <div className="space-y-4">
              <div className="p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-orange-600 dark:text-orange-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-orange-600 dark:text-orange-400">
                    <p className="font-medium mb-1">{t('auth.registrationNotPossible')}</p>
                    <p>{t('auth.registrationClosedMessage')}</p>
                  </div>
                </div>
              </div>

              <div className="text-center">
                <Link
                  to="/login"
                  className="btn btn-primary w-full"
                >
                  {t('auth.toLogin')}
                </Link>
              </div>
            </div>
          ) : (
            /* Form */
            <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            <div>
              <label htmlFor="username" className="block text-sm font-medium mb-2">
                {t('auth.username')} *
              </label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder={t('auth.usernamePlaceholder')}
                required
                minLength={3}
                maxLength={50}
                className="input"
                autoComplete="username"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2">
                {t('auth.email')} *
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder={t('auth.emailPlaceholder')}
                required
                className="input"
                autoComplete="email"
              />
            </div>

            <div>
              <label htmlFor="fullName" className="block text-sm font-medium mb-2">
                {t('auth.fullName')} ({t('auth.optional')})
              </label>
              <input
                type="text"
                id="fullName"
                name="fullName"
                value={formData.fullName}
                onChange={handleChange}
                placeholder={t('auth.fullNamePlaceholder')}
                className="input"
                autoComplete="name"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2">
                {t('auth.password')} *
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder={t('auth.passwordPlaceholder')}
                required
                minLength={8}
                className="input"
                autoComplete="new-password"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {t('auth.minCharacters')}
              </p>
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium mb-2">
                {t('auth.confirmPassword')} *
              </label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder={t('auth.passwordPlaceholder')}
                required
                className="input"
                autoComplete="new-password"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  {t('auth.registering')}
                </>
              ) : (
                <>
                  <UserPlus className="w-5 h-5" />
                  {t('auth.register')}
                </>
              )}
            </button>
          </form>
          )}

          {/* Footer - Only show when registration is open */}
          {!isRegistrationClosed && (
            <div className="mt-6 text-center text-sm">
              <p className="text-gray-600 dark:text-gray-400">
                {t('auth.haveAccount')}{' '}
                <Link
                  to="/login"
                  className="text-primary-500 hover:text-primary-600 font-medium"
                >
                  {t('auth.loginNow')}
                </Link>
              </p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  )
}
