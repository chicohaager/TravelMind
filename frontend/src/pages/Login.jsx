import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { LogIn, Loader } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useTranslation } from 'react-i18next'

export default function Login() {
  const navigate = useNavigate()
  const { login, isAuthenticated } = useAuth()
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  })
  const [loading, setLoading] = useState(false)

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
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    const success = await login(formData.username, formData.password)

    if (success) {
      navigate('/trips')
    }

    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-secondary-50 dark:from-gray-900 dark:to-gray-800 px-4">
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
              className="w-16 h-16 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-full flex items-center justify-center mx-auto mb-4"
            >
              <LogIn className="w-8 h-8 text-white" />
            </motion.div>
            <h1 className="text-3xl font-bold mb-2">{t('auth:welcomeBack')}</h1>
            <p className="text-gray-600 dark:text-gray-400">
              {t('auth:loginDescription')}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="username" className="block text-sm font-medium mb-2">
                {t('auth:username')}
              </label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder={t('auth:usernamePlaceholder')}
                required
                className="input"
                autoComplete="username"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2">
                {t('auth:password')}
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder={t('auth:passwordPlaceholder')}
                required
                className="input"
                autoComplete="current-password"
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
                  {t('auth:loggingIn')}
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  {t('auth:login')}
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-6 text-center text-sm">
            <p className="text-gray-600 dark:text-gray-400">
              {t('auth:noAccount')}{' '}
              <Link
                to="/register"
                className="text-primary-500 hover:text-primary-600 font-medium"
              >
                {t('auth:registerNow')}
              </Link>
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
