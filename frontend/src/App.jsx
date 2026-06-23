import { Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Loader } from 'lucide-react'
import { AuthProvider } from '@/contexts/AuthContext'
import Layout from '@components/layout/Layout'
import ProtectedRoute from '@components/ProtectedRoute'
import OfflineIndicator from '@components/OfflineIndicator'
import ErrorBoundary from '@components/ErrorBoundary'
import lazyWithRetry from '@/utils/lazyWithRetry'

// Route pages are code-split: each becomes its own chunk and the heavy
// dependencies (e.g. Leaflet on the map pages) load only when first visited.
const Home = lazyWithRetry(() => import('@pages/Home'))
const Trips = lazyWithRetry(() => import('@pages/Trips'))
const TripDetail = lazyWithRetry(() => import('@pages/TripDetail'))
const TripMap = lazyWithRetry(() => import('@pages/TripMap'))
const AIAssistant = lazyWithRetry(() => import('@pages/AIAssistant'))
const Diary = lazyWithRetry(() => import('@pages/Diary'))
const Budget = lazyWithRetry(() => import('@pages/Budget'))
const Transcribe = lazyWithRetry(() => import('@pages/Transcribe'))
const Profile = lazyWithRetry(() => import('@pages/Profile'))
const Settings = lazyWithRetry(() => import('@pages/Settings'))
const AdminPanel = lazyWithRetry(() => import('@pages/AdminPanel'))
const Login = lazyWithRetry(() => import('@pages/Login'))
const Register = lazyWithRetry(() => import('@pages/Register'))
const NotFound = lazyWithRetry(() => import('@pages/NotFound'))

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <Loader className="w-8 h-8 animate-spin text-primary-500" />
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <OfflineIndicator />
        <Suspense fallback={<PageLoader />}>
          <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected routes (require authentication) */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/trips" replace />} />
            <Route path="trips" element={<Trips />} />
            <Route path="trips/:id" element={<TripDetail />} />
            <Route path="trips/:id/map" element={<TripMap />} />
            <Route path="trips/:id/edit" element={<Navigate to="/trips" replace />} />
            <Route path="ai" element={<AIAssistant />} />
            <Route path="budget" element={<Budget />} />
            <Route path="diary" element={<Diary />} />
            <Route path="diary/:tripId" element={<Diary />} />
            <Route path="transcribe" element={<Transcribe />} />
            <Route path="transkribieren" element={<Transcribe />} />
            <Route path="profile" element={<Profile />} />
            <Route path="settings" element={<Settings />} />
            <Route path="admin" element={<AdminPanel />} />
            <Route path="*" element={<NotFound />} />
          </Route>
          </Routes>
        </Suspense>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
