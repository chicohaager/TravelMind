import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Map, ArrowLeft, Loader } from 'lucide-react'
import { toast, Toaster } from 'react-hot-toast'
import InteractiveMap from '../components/InteractiveMap'
import RouteBuilder from '../components/RouteBuilder'
import { tripsService, placesService, routesService } from '../services/api'
import { useTranslation } from 'react-i18next'

export default function TripMap() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const [routes, setRoutes] = useState([])

  // Fetch trip data
  const { data: trip, isLoading: tripLoading } = useQuery({
    queryKey: ['trip', id],
    queryFn: async () => {
      const response = await tripsService.getById(id)
      return response.data
    },
  })

  // Fetch places
  const { data: places = [], isLoading: placesLoading } = useQuery({
    queryKey: ['places', id],
    queryFn: async () => {
      const response = await placesService.getByTrip(id)
      return response.data
    },
  })

  // Fetch routes
  const { data: routesData = [], isLoading: routesLoading, refetch: refetchRoutes } = useQuery({
    queryKey: ['routes', id],
    queryFn: async () => {
      const response = await routesService.getByTrip(id)
      return response.data
    },
  })

  useEffect(() => {
    if (routesData) {
      setRoutes(routesData)
    }
  }, [routesData])

  const handleRoutesChange = (newRoutes) => {
    setRoutes(newRoutes)
    refetchRoutes()
  }

  if (tripLoading || placesLoading || routesLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  if (!trip) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Trip not found</h2>
          <p className="text-gray-600 mb-4">The trip you're looking for doesn't exist.</p>
          <button
            onClick={() => navigate('/trips')}
            className="btn btn-primary"
          >
            Back to Trips
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate(`/trips/${id}`)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <Map className="w-6 h-6 text-indigo-600" />
                  {trip.title} - Interactive Map
                </h1>
                <p className="text-sm text-gray-600 mt-1">
                  {places.length} places • {routes.length} routes
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Map */}
          <div className="lg:col-span-2">
            <div className="card p-0 overflow-hidden" style={{ height: 'calc(100vh - 180px)' }}>
              {places.length > 0 ? (
                <InteractiveMap
                  places={places}
                  routes={routes}
                  center={trip.latitude && trip.longitude ? [trip.latitude, trip.longitude] : undefined}
                  zoom={12}
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-center p-8">
                  <Map className="w-16 h-16 text-gray-300 mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('map:noPlacesYet')}</h3>
                  <p className="text-gray-600 mb-4">
                    {t('map:addPlacesToSeeOnMap')}
                  </p>
                  <button
                    onClick={() => navigate(`/trips/${id}`)}
                    className="btn btn-primary"
                  >
                    {t('map:addPlaces')}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Route Builder Sidebar */}
          <div className="lg:col-span-1">
            <div className="sticky top-24">
              {places.length >= 2 ? (
                <RouteBuilder
                  tripId={parseInt(id)}
                  places={places}
                  routes={routes}
                  onRoutesChange={handleRoutesChange}
                />
              ) : (
                <div className="card">
                  <div className="text-center py-8">
                    <Map className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <h3 className="font-semibold text-gray-900 mb-2">
                      {t('map:createRoutes')}
                    </h3>
                    <p className="text-sm text-gray-600 mb-4">
                      {t('map:needTwoPlacesForRoute')}
                    </p>
                    <button
                      onClick={() => navigate(`/trips/${id}`)}
                      className="btn btn-primary btn-sm"
                    >
                      {t('map:addMorePlaces')}
                    </button>
                  </div>
                </div>
              )}

              {/* Quick Stats */}
              {places.length > 0 && (
                <div className="card mt-4">
                  <h3 className="font-semibold mb-3">{t('map:mapStatistics')}</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">{t('map:totalPlaces')}</span>
                      <span className="font-medium">{places.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">{t('map:activeRoutes')}</span>
                      <span className="font-medium">{routes.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">{t('map:visited')}</span>
                      <span className="font-medium">
                        {places.filter(p => p.visited).length} / {places.length}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Help Section */}
              <div className="card mt-4 bg-indigo-50 border-indigo-200">
                <h3 className="font-semibold text-indigo-900 mb-2">💡 {t('map:tip')}</h3>
                <p className="text-sm text-indigo-700">
                  {t('map:dragPlacesToCreateRoutes')}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
