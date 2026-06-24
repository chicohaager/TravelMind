import { createContext, useContext, useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { authService } from '@services/api'
import { clearUserContext } from '@/utils/sentry'
import toast from 'react-hot-toast'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const { t } = useTranslation()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(localStorage.getItem('token'))

  // Load user on mount if token exists
  useEffect(() => {
    if (token) {
      loadUser()
    } else {
      setLoading(false)
    }
  }, [token])

  // Clear local session state without any user-facing toast (used for stale
  // tokens on load and as the shared teardown for an explicit logout).
  const clearSession = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    clearUserContext()
  }

  const loadUser = async () => {
    try {
      const response = await authService.getCurrentUser()
      setUser(response.data)
    } catch (error) {
      console.error('Failed to load user:', error)
      // Stale/invalid token: clear silently, do NOT fire a "logged out" toast.
      clearSession()
    } finally {
      setLoading(false)
    }
  }

  const register = async (username, email, password, fullName) => {
    try {
      const response = await authService.register({
        username,
        email,
        password,
        full_name: fullName,
      })
      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      setToken(access_token)
      await loadUser()
      toast.success(t('auth:registrationSuccessful'))
      return true
    } catch (error) {
      const message = error.response?.data?.detail || t('auth:registrationFailed')
      toast.error(message)
      return false
    }
  }

  const login = async (username, password) => {
    try {
      const response = await authService.login(username, password)
      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      setToken(access_token)
      await loadUser()
      toast.success(t('auth:loginSuccessful'))
      return true
    } catch (error) {
      const message = error.response?.data?.detail || t('auth:loginFailed')
      toast.error(message)
      return false
    }
  }

  const logout = async () => {
    // Best-effort server-side revoke (refresh cookie/session); ignore failures
    // so logout always succeeds locally even when offline or already expired.
    try {
      await authService.logout()
    } catch (_) {
      // intentionally ignored
    }
    clearSession()
    toast.success(t('auth:logoutSuccessful'))
  }

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user,
    register,
    login,
    logout,
    loadUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
