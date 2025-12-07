import { useState, useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapPin, Hotel, Coffee, UtensilsCrossed, Camera, Mountain, Ship, Plane } from 'lucide-react'
import { useTranslation } from 'react-i18next'

// Fix Leaflet default marker icon issue
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

// Icon mapping
const iconMap = {
  location: MapPin,
  hotel: Hotel,
  coffee: Coffee,
  restaurant: UtensilsCrossed,
  camera: Camera,
  mountain: Mountain,
  ship: Ship,
  plane: Plane,
}

// Create custom marker icon
const createCustomIcon = (color = '#6366F1', iconType = 'location') => {
  const size = 40
  const IconComponent = iconMap[iconType] || MapPin

  // Create SVG string
  const svg = `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
      <circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 2}" fill="${color}" stroke="white" stroke-width="2"/>
      <g transform="translate(${size / 4}, ${size / 4})">
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" fill="white" stroke="none"/>
      </g>
    </svg>
  `

  return L.divIcon({
    html: svg,
    className: 'custom-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  })
}

// Component to center map on places
function MapCenterController({ places }) {
  const map = useMap()

  useEffect(() => {
    if (places && places.length > 0) {
      const bounds = L.latLngBounds(places.map(p => [p.latitude, p.longitude]))
      map.fitBounds(bounds, { padding: [50, 50] })
    }
  }, [places, map])

  return null
}

// Category colors for legend
const categoryColors = {
  restaurant: '#ef4444',
  attraction: '#8b5cf6',
  hotel: '#3b82f6',
  museum: '#f59e0b',
  park: '#22c55e',
  beach: '#06b6d4',
  shopping: '#ec4899',
  viewpoint: '#6366f1',
  nightlife: '#a855f7',
  other: '#6b7280',
  sight: '#8b5cf6',
  activity: '#f97316',
  transport: '#64748b'
}

export default function InteractiveMap({
  places = [],
  routes = [],
  onPlaceClick = null,
  onRouteClick = null,
  editable = false,
  center = [51.505, -0.09],
  zoom = 13
}) {
  const { t } = useTranslation(['map', 'places'])
  const [selectedPlace, setSelectedPlace] = useState(null)
  const [selectedRoute, setSelectedRoute] = useState(null)

  // Calculate initial center and zoom based on places
  const mapCenter = useMemo(() => {
    if (places.length === 0) return center
    const avgLat = places.reduce((sum, p) => sum + p.latitude, 0) / places.length
    const avgLng = places.reduce((sum, p) => sum + p.longitude, 0) / places.length
    return [avgLat, avgLng]
  }, [places, center])

  const handlePlaceClick = (place) => {
    setSelectedPlace(place)
    if (onPlaceClick) {
      onPlaceClick(place)
    }
  }

  const handleRouteClick = (route) => {
    setSelectedRoute(route)
    if (onRouteClick) {
      onRouteClick(route)
    }
  }

  // Get route coordinates
  const getRouteCoordinates = (route) => {
    if (!route.place_ids || route.place_ids.length === 0) return []

    return route.place_ids
      .map(placeId => places.find(p => p.id === placeId))
      .filter(place => place)
      .map(place => [place.latitude, place.longitude])
  }

  return (
    <div className="relative w-full h-full rounded-lg overflow-hidden shadow-lg">
      <MapContainer
        center={mapCenter}
        zoom={zoom}
        className="w-full h-full"
        style={{ minHeight: '400px' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapCenterController places={places} />

        {/* Render routes first (so they appear below markers) */}
        {routes.map((route) => {
          const coordinates = getRouteCoordinates(route)
          if (coordinates.length < 2) return null

          return (
            <Polyline
              key={route.id}
              positions={coordinates}
              pathOptions={{
                color: route.color || '#6366F1',
                weight: route.line_width || 3,
                opacity: 0.7,
                dashArray: route.line_style === 'dashed' ? '10, 10' : route.line_style === 'dotted' ? '2, 5' : null,
              }}
              eventHandlers={{
                click: () => handleRouteClick(route),
              }}
            >
              <Popup>
                <div className="font-semibold">{route.name}</div>
                {route.description && <div className="text-sm text-gray-600 mt-1">{route.description}</div>}
                {route.total_distance && (
                  <div className="text-sm text-gray-500 mt-1">
                    Distance: {route.total_distance.toFixed(1)} km
                  </div>
                )}
              </Popup>
            </Polyline>
          )
        })}

        {/* Render place markers */}
        {places.map((place) => (
          <Marker
            key={place.id}
            position={[place.latitude, place.longitude]}
            icon={createCustomIcon(place.color || '#6366F1', place.icon_type || 'location')}
            eventHandlers={{
              click: () => handlePlaceClick(place),
            }}
          >
            <Popup>
              <div className="max-w-xs">
                <h3 className="font-bold text-lg">{place.name}</h3>
                {place.category && (
                  <span className="inline-block px-2 py-1 text-xs bg-gray-100 rounded-full mt-1">
                    {place.category}
                  </span>
                )}
                {place.description && (
                  <p className="text-sm text-gray-600 mt-2">{place.description}</p>
                )}
                {place.address && (
                  <p className="text-xs text-gray-500 mt-2">{place.address}</p>
                )}
                {place.rating && (
                  <div className="flex items-center mt-2">
                    <span className="text-yellow-500 mr-1">★</span>
                    <span className="text-sm">{place.rating}/5</span>
                  </div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Map Legend */}
      {(places.length > 0 || routes.length > 0) && (
        <div className="absolute bottom-4 right-4 bg-white/95 backdrop-blur-sm p-4 rounded-2xl shadow-xl max-w-xs z-[1000] border border-gray-100">
          <h4 className="font-bold text-sm mb-3 text-gray-800">{t('map:legend')}</h4>

          {/* Places legend */}
          {places.length > 0 && (
            <div className="mb-3">
              <div className="text-xs font-medium text-gray-500 mb-2">{t('map:places')}: {places.length}</div>
              <div className="flex flex-wrap gap-1.5">
                {Array.from(new Set(places.map(p => p.category))).filter(Boolean).map(category => (
                  <span
                    key={category}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-white rounded-full shadow-sm"
                    style={{ backgroundColor: categoryColors[category] || '#6b7280' }}
                  >
                    <span
                      className="w-1.5 h-1.5 rounded-full bg-white/40"
                    />
                    {t(`places:categories.${category}`, category)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Routes legend */}
          {routes.length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-500 mb-2">{t('map:routes')}: {routes.length}</div>
              <div className="space-y-1.5">
                {routes.slice(0, 3).map(route => (
                  <div key={route.id} className="flex items-center gap-2 text-xs">
                    <div
                      className="w-5 h-1 rounded-full"
                      style={{ backgroundColor: route.color || '#6366F1' }}
                    />
                    <span className="truncate text-gray-700 font-medium">{route.name}</span>
                  </div>
                ))}
                {routes.length > 3 && (
                  <div className="text-xs text-gray-400 mt-1">{t('map:moreRoutes', { count: routes.length - 3 })}</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
