import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Lock, Trash2, AlertTriangle, Eye, EyeOff, Brain, CheckCircle, XCircle, Loader } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { usersService, userSettingsService } from '@/services/api'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

export default function Settings() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showAPIKey, setShowAPIKey] = useState(false)
  const [validatingAPIKey, setValidatingAPIKey] = useState(false)
  const [aiLoading, setAILoading] = useState(false)

  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })

  const [aiSettings, setAISettings] = useState({
    ai_provider: 'GROQ',
    api_key: '',
    has_api_key: false,
  })

  const [deleteConfirmText, setDeleteConfirmText] = useState('')

  // Load AI settings on mount
  useEffect(() => {
    loadAISettings()
  }, [])

  const loadAISettings = async () => {
    try {
      const response = await userSettingsService.getAISettings()
      setAISettings({
        ...aiSettings,
        ai_provider: response.data.ai_provider || 'GROQ',
        has_api_key: response.data.has_api_key,
      })
    } catch (error) {
      console.error('Failed to load AI settings:', error)
    }
  }

  const handleValidateAPIKey = async () => {
    if (!aiSettings.api_key) {
      toast.error(t('settings.enterApiKey'))
      return
    }

    setValidatingAPIKey(true)

    try {
      const response = await userSettingsService.validateAPIKey({
        ai_provider: aiSettings.ai_provider,
        api_key: aiSettings.api_key,
      })

      if (response.data.valid) {
        toast.success(t('settings.apiKeyValid'))
      } else {
        toast.error(response.data.message || t('settings.apiKeyInvalid'))
      }
    } catch (error) {
      const message = error.response?.data?.detail || t('settings.validationError')
      toast.error(message)
    } finally {
      setValidatingAPIKey(false)
    }
  }

  const handleSaveAISettings = async () => {
    if (!aiSettings.api_key) {
      toast.error(t('settings.enterApiKey'))
      return
    }

    setAILoading(true)

    try {
      await userSettingsService.updateAISettings({
        ai_provider: aiSettings.ai_provider,
        api_key: aiSettings.api_key,
      })

      toast.success(t('settings.aiSettingsSaved'))
      setAISettings({ ...aiSettings, api_key: '', has_api_key: true })
      setShowAPIKey(false)
      await loadAISettings()
    } catch (error) {
      const message = error.response?.data?.detail || t('settings.saveError')
      toast.error(message)
    } finally {
      setAILoading(false)
    }
  }

  const handleDeleteAISettings = async () => {
    if (!confirm(t('settings.deleteAiConfirm'))) {
      return
    }

    setAILoading(true)

    try {
      await userSettingsService.deleteAISettings()
      toast.success(t('settings.aiSettingsDeleted'))
      setAISettings({ ai_provider: 'GROQ', api_key: '', has_api_key: false })
    } catch (error) {
      const message = error.response?.data?.detail || t('settings.deleteError')
      toast.error(message)
    } finally {
      setAILoading(false)
    }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error(t('auth.passwordsDoNotMatch'))
      return
    }

    if (passwordForm.new_password.length < 8) {
      toast.error(t('settings.passwordMinLength'))
      return
    }

    setLoading(true)

    try {
      await usersService.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      })

      toast.success(t('settings.passwordChanged'))
      setPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: '',
      })
    } catch (error) {
      const message = error.response?.data?.detail || t('settings.passwordChangeError')
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== user?.username) {
      toast.error(t('auth.usernameDoesNotMatch'))
      return
    }

    setLoading(true)

    try {
      await usersService.deleteAccount()
      toast.success(t('settings.accountDeleted'))
      logout()
      navigate('/')
    } catch (error) {
      const message = error.response?.data?.detail || t('settings.accountDeleteError')
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold mb-2">{t('settings.title')}</h1>
        <p className="text-gray-600 dark:text-gray-400">
          {t('settings.securityDescription')}
        </p>
      </motion.div>

      <div className="space-y-6">
        {/* AI Configuration Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-100 dark:bg-indigo-900 rounded-lg">
                  <Brain className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-xl font-bold">{t('ai.aiConfiguration')}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {t('ai.configureProvider')}
                  </p>
                </div>
              </div>
              {aiSettings.has_api_key && (
                <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                  <CheckCircle className="w-5 h-5" />
                  <span className="text-sm font-medium">{t('ai.configured')}</span>
                </div>
              )}
            </div>

            <div className="space-y-4">
              {/* Provider Selection */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  {t('ai.provider')}
                </label>
                <select
                  value={aiSettings.ai_provider}
                  onChange={(e) => setAISettings({ ...aiSettings, ai_provider: e.target.value })}
                  className="input w-full"
                  disabled={aiLoading}
                >
                  <option value="GROQ">{t('ai.groqOption')}</option>
                  <option value="CLAUDE">{t('ai.claudeOption')}</option>
                  <option value="OPENAI">{t('ai.openaiOption')}</option>
                  <option value="GEMINI">{t('ai.geminiOption')}</option>
                </select>
                <p className="text-sm text-gray-500 mt-1">
                  {t('ai.selectProvider')}
                </p>
              </div>

              {/* API Key Input */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  {t('ai.apiKey')}
                  {aiSettings.has_api_key && (
                    <span className="ml-2 text-xs text-green-600 dark:text-green-400">
                      ({t('ai.apiKeyStored')})
                    </span>
                  )}
                </label>
                <div className="relative">
                  <input
                    type={showAPIKey ? 'text' : 'password'}
                    value={aiSettings.api_key}
                    onChange={(e) => setAISettings({ ...aiSettings, api_key: e.target.value })}
                    className="input w-full pr-10"
                    placeholder={aiSettings.has_api_key ? t('ai.enterNewApiKey') : t('ai.enterApiKey')}
                    disabled={aiLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowAPIKey(!showAPIKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showAPIKey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-gray-500">
                    {aiSettings.ai_provider === 'GROQ' && t('settings.getApiKeyGroq')}
                    {aiSettings.ai_provider === 'CLAUDE' && t('settings.getApiKeyClaude')}
                    {aiSettings.ai_provider === 'OPENAI' && t('settings.getApiKeyOpenAI')}
                    {aiSettings.ai_provider === 'GEMINI' && t('settings.getApiKeyGemini')}
                  </p>
                  <p className="text-xs text-gray-500">
                    {t('settings.apiKeyEncrypted')}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={handleValidateAPIKey}
                  className="btn-outline flex-1 flex items-center justify-center gap-2"
                  disabled={!aiSettings.api_key || validatingAPIKey || aiLoading}
                >
                  {validatingAPIKey ? (
                    <>
                      <Loader className="w-4 h-4 animate-spin" />
                      Validiere...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      Validieren
                    </>
                  )}
                </button>
                <button
                  onClick={handleSaveAISettings}
                  className="btn-primary flex-1"
                  disabled={!aiSettings.api_key || aiLoading}
                >
                  {aiLoading ? t('settings.saving') : t('common.save')}
                </button>
              </div>

              {/* Delete Button */}
              {aiSettings.has_api_key && (
                <button
                  onClick={handleDeleteAISettings}
                  className="btn bg-red-600 hover:bg-red-700 text-white w-full flex items-center justify-center gap-2"
                  disabled={aiLoading}
                >
                  <XCircle className="w-4 h-4" />
                  {t('settings.deleteAiSettings')}
                </button>
              )}
            </div>
          </div>
        </motion.div>

        {/* Password Change Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="card">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-primary-100 dark:bg-primary-900 rounded-lg">
                <Lock className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <h3 className="text-xl font-bold">{t('settings.changePassword')}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {t('settings.changePasswordDescription')}
                </p>
              </div>
            </div>

            <form onSubmit={handlePasswordChange} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  {t('settings.currentPassword')}
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={passwordForm.current_password}
                    onChange={(e) =>
                      setPasswordForm({ ...passwordForm, current_password: e.target.value })
                    }
                    className="input w-full pr-10"
                    required
                    disabled={loading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  {t('settings.newPassword')}
                </label>
                <div className="relative">
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    value={passwordForm.new_password}
                    onChange={(e) =>
                      setPasswordForm({ ...passwordForm, new_password: e.target.value })
                    }
                    className="input w-full pr-10"
                    required
                    minLength="8"
                    disabled={loading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  {t('auth.passwordTooShort')}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  {t('settings.confirmNewPassword')}
                </label>
                <input
                  type={showNewPassword ? 'text' : 'password'}
                  value={passwordForm.confirm_password}
                  onChange={(e) =>
                    setPasswordForm({ ...passwordForm, confirm_password: e.target.value })
                  }
                  className="input w-full"
                  required
                  minLength="8"
                  disabled={loading}
                />
              </div>

              <button
                type="submit"
                className="btn-primary w-full"
                disabled={loading}
              >
                {loading ? t('settings.updating') : t('settings.changePassword')}
              </button>
            </form>
          </div>
        </motion.div>

        {/* Delete Account Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="card border-2 border-red-200 dark:border-red-900">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-red-100 dark:bg-red-900 rounded-lg">
                <Trash2 className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-red-600 dark:text-red-400">
                  {t('settings.deleteAccount')}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {t('settings.deleteAccountPermanently')}
                </p>
              </div>
            </div>

            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
              <div className="flex gap-3">
                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-red-800 dark:text-red-300">
                  <p className="font-semibold mb-1">{t('settings.deleteWarningTitle')}</p>
                  <p>{t('settings.deleteWarningText')}</p>
                </div>
              </div>
            </div>

            {!showDeleteConfirm ? (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="btn bg-red-600 hover:bg-red-700 text-white w-full"
              >
                {t('settings.deleteAccount')}
              </button>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2" dangerouslySetInnerHTML={{
                    __html: t('settings.confirmUsernamePrompt').replace('{username}', user?.username || '')
                  }} />

                  <input
                    type="text"
                    value={deleteConfirmText}
                    onChange={(e) => setDeleteConfirmText(e.target.value)}
                    className="input w-full"
                    placeholder={user?.username}
                    disabled={loading}
                  />
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setShowDeleteConfirm(false)
                      setDeleteConfirmText('')
                    }}
                    className="btn-outline flex-1"
                    disabled={loading}
                  >
                    {t('common.cancel')}
                  </button>
                  <button
                    onClick={handleDeleteAccount}
                    className="btn bg-red-600 hover:bg-red-700 text-white flex-1"
                    disabled={loading || deleteConfirmText !== user?.username}
                  >
                    {loading ? t('settings.deleting') : t('settings.permanentlyDelete')}
                  </button>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  )
}
