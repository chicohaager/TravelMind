import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import Layout from '@components/layout/Layout'
import ProtectedRoute from '@components/ProtectedRoute'
import OfflineIndicator from '@components/OfflineIndicator'
import ErrorBoundary from '@components/ErrorBoundary'
import Home from '@pages/Home'
import Trips from '@pages/Trips'
import TripDetail from '@pages/TripDetail'
import TripMap from '@pages/TripMap'
import AIAssistant from '@pages/AIAssistant'
import Diary from '@pages/Diary'
import Budget from '@pages/Budget'
import Transcribe from '@pages/Transcribe'
import Profile from '@pages/Profile'
import Settings from '@pages/Settings'
import AdminPanel from '@pages/AdminPanel'
import Login from '@pages/Login'
import Register from '@pages/Register'
import NotFound from '@pages/NotFound'

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <OfflineIndicator />
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
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
