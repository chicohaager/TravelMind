import axios from 'axios'

// In development, ALWAYS use relative URLs to leverage Vite proxy
// In production, use the configured API URL
const isDev = import.meta.env.DEV
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Force relative URLs in development
let baseURL
if (isDev || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  baseURL = '/api'
} else {
  baseURL = `${API_URL}/api`
}

console.log('API Config:', { isDev, API_URL, baseURL, hostname: window.location.hostname })

// Create axios instance
const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for adding auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// AI Services
export const aiService = {
  suggest: (data) => api.post('/ai/suggest', data),
  plan: (data) => api.post('/ai/plan', data),
  describe: (destination) => api.post('/ai/describe', { destination }),
  chat: (message, context) => api.post('/ai/chat', { message, context }),
  localTips: (destination, category = 'all') =>
    api.post('/ai/local-tips', { destination, category }),
  getTripSuggestions: (destination) =>
    api.post('/ai/trip-suggestions', { destination }),
  getPersonalizedRecommendations: (data) =>
    api.post('/ai/personalized-recommendations', data),
}

// Trips Services
export const tripsService = {
  getAll: () => api.get('/trips'),
  getById: (id) => api.get(`/trips/${id}`),
  create: (data) => api.post('/trips', data),
  update: (id, data) => api.put(`/trips/${id}`, data),
  delete: (id) => api.delete(`/trips/${id}`),
  getSummary: (id) => api.get(`/trips/${id}/summary`),
  uploadImage: (id, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/trips/${id}/upload-image`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  geocode: (location) => api.get(`/trips/geocode/${encodeURIComponent(location)}`),
}

// Diary Services
export const diaryService = {
  getEntries: (tripId) => api.get(`/diary/${tripId}`),
  create: (tripId, data) => api.post(`/diary/${tripId}`, data),
  update: (entryId, data) => api.put(`/diary/${entryId}`, data),
  delete: (entryId) => api.delete(`/diary/${entryId}`),
  uploadPhoto: (entryId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/diary/${entryId}/upload-photo`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  deletePhoto: (entryId, photoUrl) => api.delete(`/diary/${entryId}/photo`, { params: { photo_url: photoUrl } }),
  exportMarkdown: (tripId) => api.get(`/diary/${tripId}/export/markdown`, { responseType: 'blob' }),
  exportPdf: (tripId) => api.get(`/diary/${tripId}/export/pdf`, { responseType: 'blob' }),
}

// Places Services
export const placesService = {
  getPlaces: (tripId) => api.get(`/places/${tripId}/places`),
  create: (tripId, data) => api.post(`/places/${tripId}/places`, data),
  update: (placeId, data) => api.put(`/places/places/${placeId}`, data),
  delete: (placeId) => api.delete(`/places/places/${placeId}`),
  markVisited: (placeId, visited) => api.put(`/places/places/${placeId}/visited`, null, { params: { visited } }),
  reorder: (tripId, placeIds) => api.post(`/places/${tripId}/places/reorder`, placeIds),
  // Guide Import
  searchGuides: (tripId, destination) =>
    api.post(`/places/${tripId}/search-guides`, { destination }),
  parseGuideUrl: (tripId, url, destination) =>
    api.post(`/places/${tripId}/import-from-guide`, { url, destination }),
  importPlacesBulk: (tripId, places) =>
    api.post(`/places/${tripId}/import-places-bulk`, { places }),
  // Custom Place Lists
  getLists: (tripId) => api.get(`/places/${tripId}/lists`),
  createList: (tripId, data) => api.post(`/places/${tripId}/lists`, data),
  updateList: (listId, data) => api.put(`/places/lists/${listId}`, data),
  deleteList: (listId) => api.delete(`/places/lists/${listId}`),
  toggleListCollapse: (listId) => api.patch(`/places/lists/${listId}/toggle-collapse`),
  // Photo Upload
  uploadPhoto: (placeId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/places/places/${placeId}/upload-photo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  deletePhoto: (placeId, photoUrl) =>
    api.delete(`/places/places/${placeId}/photo`, { params: { photo_url: photoUrl } }),
}

// Timeline Services
export const timelineService = {
  getTimeline: (tripId) => api.get(`/timeline/${tripId}/timeline`),
  create: (tripId, data) => api.post(`/timeline/${tripId}/timeline`, data),
  update: (entryId, data) => api.put(`/timeline/timeline/${entryId}`, data),
  delete: (entryId) => api.delete(`/timeline/timeline/${entryId}`),
  reorder: (tripId, entryIds) => api.post(`/timeline/${tripId}/timeline/reorder`, entryIds),
  optimize: (tripId, dayDate) => api.post(`/timeline/${tripId}/timeline/optimize`, null, { params: { day_date: dayDate } }),
}

// Budget Services
export const budgetService = {
  getExpenses: (tripId) => api.get(`/budget/${tripId}/expenses`),
  create: (tripId, data) => api.post(`/budget/${tripId}/expenses`, data),
  update: (expenseId, data) => api.put(`/budget/expenses/${expenseId}`, data),
  delete: (expenseId) => api.delete(`/budget/expenses/${expenseId}`),
  getSummary: (tripId) => api.get(`/budget/${tripId}/budget-summary`),
  splitEqually: (tripId, data) => api.post(`/budget/${tripId}/expenses/split-equally`, null, { params: data }),
}

// Auth Services
export const authService = {
  register: (data) => api.post('/auth/register', data),
  login: (username, password) => {
    // OAuth2 expects form data, not JSON
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
  },
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me'),
  refreshToken: () => api.post('/auth/refresh'),
  getRegistrationStatus: () => api.get('/auth/registration-status'),
}

// Users Services
export const usersService = {
  getProfile: () => api.get('/users/profile'),
  updateProfile: (data) => api.put('/users/profile', data),
  changePassword: (data) => api.post('/users/change-password', data),
  getUser: (userId) => api.get(`/users/${userId}`),
  deleteAccount: () => api.delete('/users/account'),
  uploadAvatar: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/users/upload-avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}

// User Settings Services
export const userSettingsService = {
  getSettings: () => api.get('/user/settings'),
  getAISettings: () => api.get('/user/settings/ai'),
  updateAISettings: (data) => api.put('/user/settings/ai', data),
  deleteAISettings: () => api.delete('/user/settings/ai'),
  validateAPIKey: (data) => api.post('/user/settings/ai/validate', data),
}

// Admin Services
export const adminService = {
  getUsers: (params) => api.get('/admin/users', { params }),
  getUser: (userId) => api.get(`/admin/users/${userId}`),
  updateUser: (userId, data) => api.put(`/admin/users/${userId}`, data),
  deleteUser: (userId) => api.delete(`/admin/users/${userId}`),
  getStats: () => api.get('/admin/stats'),

  // Settings management
  getSettings: () => api.get('/admin/settings'),
  getSetting: (key) => api.get(`/admin/settings/${key}`),
  updateSetting: (key, data) => api.put(`/admin/settings/${key}`, data),
  toggleRegistration: () => api.post('/admin/settings/registration/toggle'),

  // User creation
  createUser: (userData) => api.post('/admin/users/create', userData),

  // Geocoding utilities
  fixPlaceCoordinates: () => api.post('/admin/geocode/fix-places'),
}

// Participants Services
export const participantsService = {
  getParticipants: (tripId) => api.get(`/trips/${tripId}/participants`),
  create: (tripId, data) => api.post(`/trips/${tripId}/participants`, data),
  update: (participantId, data) => api.put(`/trips/participants/${participantId}`, data),
  delete: (participantId) => api.delete(`/trips/participants/${participantId}`),
  uploadPhoto: (participantId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/trips/participants/${participantId}/upload-photo`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}

// Routes Services (for map itineraries)
export const routesService = {
  getByTrip: (tripId) => api.get(`/routes/trip/${tripId}`),
  getById: (routeId) => api.get(`/routes/${routeId}`),
  create: (data) => api.post('/routes/', data),
  update: (routeId, data) => api.put(`/routes/${routeId}`, data),
  delete: (routeId) => api.delete(`/routes/${routeId}`),
}

export default api
