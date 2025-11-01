import { useState, useEffect } from 'react'
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd'
import { Plus, X, GripVertical, Save, Route as RouteIcon, Minus } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import ColorPicker from './ColorPicker'
import { routesService } from '../services/api'

export default function RouteBuilder({ tripId, places = [], routes: initialRoutes = [], onRoutesChange }) {
  const { t } = useTranslation()
  const [routes, setRoutes] = useState(initialRoutes)
  const [editingRoute, setEditingRoute] = useState(null)
  const [isCreating, setIsCreating] = useState(false)

  const [newRoute, setNewRoute] = useState({
    name: '',
    description: '',
    color: '#6366F1',
    line_style: 'solid',
    line_width: 3,
    place_ids: [],
    transport_mode: 'car',
  })

  useEffect(() => {
    setRoutes(initialRoutes)
  }, [initialRoutes])

  const handleDragEnd = (result) => {
    if (!result.destination) return

    const { source, destination, draggableId } = result

    // Dragging from places list to route
    if (source.droppableId === 'places' && destination.droppableId === 'route-places') {
      const placeId = parseInt(draggableId.replace('place-', ''))
      const newPlaceIds = [...newRoute.place_ids]
      newPlaceIds.splice(destination.index, 0, placeId)
      setNewRoute({ ...newRoute, place_ids: newPlaceIds })
    }

    // Reordering within route
    if (source.droppableId === 'route-places' && destination.droppableId === 'route-places') {
      const newPlaceIds = [...newRoute.place_ids]
      const [removed] = newPlaceIds.splice(source.index, 1)
      newPlaceIds.splice(destination.index, 0, removed)
      setNewRoute({ ...newRoute, place_ids: newPlaceIds })
    }
  }

  const removePlace = (index) => {
    const newPlaceIds = newRoute.place_ids.filter((_, i) => i !== index)
    setNewRoute({ ...newRoute, place_ids: newPlaceIds })
  }

  const handleSaveRoute = async () => {
    if (!newRoute.name) {
      toast.error(t('routes.pleaseEnterRouteName'))
      return
    }

    if (newRoute.place_ids.length < 2) {
      toast.error(t('routes.routeNeedsTwoPlaces'))
      return
    }

    try {
      const routeData = {
        ...newRoute,
        trip_id: tripId,
      }

      let savedRoute
      if (editingRoute) {
        // Update existing route
        const response = await routesService.update(editingRoute.id, routeData)
        savedRoute = response.data
        toast.success('Route aktualisiert!')
      } else {
        // Create new route
        const response = await routesService.create(routeData)
        savedRoute = response.data
        toast.success('Route erstellt!')
      }

      // Update routes list
      if (editingRoute) {
        setRoutes(routes.map(r => r.id === savedRoute.id ? savedRoute : r))
      } else {
        setRoutes([...routes, savedRoute])
      }

      // Notify parent
      if (onRoutesChange) {
        onRoutesChange(editingRoute ? routes.map(r => r.id === savedRoute.id ? savedRoute : r) : [...routes, savedRoute])
      }

      // Reset form
      resetForm()
    } catch (error) {
      console.error('Error saving route:', error)
      toast.error(error.response?.data?.detail || t('routes.errorSavingRoute'))
    }
  }

  const handleDeleteRoute = async (routeId) => {
    if (!confirm(t('routes.confirmDeleteRoute'))) return

    try {
      await routesService.delete(routeId)
      const newRoutes = routes.filter(r => r.id !== routeId)
      setRoutes(newRoutes)
      if (onRoutesChange) {
        onRoutesChange(newRoutes)
      }
      toast.success(t('routes.routeDeleted'))
    } catch (error) {
      console.error('Error deleting route:', error)
      toast.error(t('routes.errorDeletingRoute'))
    }
  }

  const editRoute = (route) => {
    setEditingRoute(route)
    setNewRoute({
      name: route.name,
      description: route.description || '',
      color: route.color,
      line_style: route.line_style,
      line_width: route.line_width,
      place_ids: [...route.place_ids],
      transport_mode: route.transport_mode,
    })
    setIsCreating(true)
  }

  const resetForm = () => {
    setIsCreating(false)
    setEditingRoute(null)
    setNewRoute({
      name: '',
      description: '',
      color: '#6366F1',
      line_style: 'solid',
      line_width: 3,
      place_ids: [],
      transport_mode: 'car',
    })
  }

  const getPlaceById = (placeId) => places.find(p => p.id === placeId)

  const availablePlaces = places.filter(p => !newRoute.place_ids.includes(p.id))

  return (
    <div className="space-y-4">
      {/* Existing Routes List */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <RouteIcon className="w-5 h-5" />
            Routen ({routes.length})
          </h3>
          <button
            onClick={() => setIsCreating(!isCreating)}
            className="btn btn-primary btn-sm flex items-center gap-2"
          >
            {isCreating ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            {isCreating ? 'Abbrechen' : 'Neue Route'}
          </button>
        </div>

        {routes.length > 0 && (
          <div className="space-y-2">
            {routes.map(route => (
              <div
                key={route.id}
                className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg"
              >
                <div
                  className="w-1 h-12 rounded-full"
                  style={{ backgroundColor: route.color }}
                />
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium truncate">{route.name}</h4>
                  <p className="text-sm text-gray-500">
                    {route.place_ids.length} Stopps
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => editRoute(route)}
                    className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                  >
                    Bearbeiten
                  </button>
                  <button
                    onClick={() => handleDeleteRoute(route.id)}
                    className="text-sm text-red-600 hover:text-red-700 font-medium"
                  >
                    Löschen
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Route Creation/Edit Form */}
      {isCreating && (
        <DragDropContext onDragEnd={handleDragEnd}>
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">
              {editingRoute ? 'Route bearbeiten' : 'Neue Route erstellen'}
            </h3>

            {/* Route Details */}
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Routenname *
                </label>
                <input
                  type="text"
                  value={newRoute.name}
                  onChange={(e) => setNewRoute({ ...newRoute, name: e.target.value })}
                  placeholder="z.B. Tag 1: Stadttour"
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Beschreibung
                </label>
                <textarea
                  value={newRoute.description}
                  onChange={(e) => setNewRoute({ ...newRoute, description: e.target.value })}
                  placeholder="Optionale Beschreibung..."
                  className="input w-full"
                  rows="2"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <ColorPicker
                  value={newRoute.color}
                  onChange={(color) => setNewRoute({ ...newRoute, color })}
                  label="Linienfarbe"
                />

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Linienstil
                  </label>
                  <select
                    value={newRoute.line_style}
                    onChange={(e) => setNewRoute({ ...newRoute, line_style: e.target.value })}
                    className="input w-full"
                  >
                    <option value="solid">Durchgezogen</option>
                    <option value="dashed">Gestrichelt</option>
                    <option value="dotted">Gepunktet</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Places Selection */}
            <div className="grid md:grid-cols-2 gap-4">
              {/* Available Places */}
              <div>
                <h4 className="font-medium mb-2">Verfügbare Orte</h4>
                <Droppable droppableId="places" isDropDisabled>
                  {(provided) => (
                    <div
                      {...provided.droppableProps}
                      ref={provided.innerRef}
                      className="space-y-2 min-h-[200px] max-h-[400px] overflow-y-auto p-3 bg-gray-50 rounded-lg"
                    >
                      {availablePlaces.map((place, index) => (
                        <Draggable
                          key={`place-${place.id}`}
                          draggableId={`place-${place.id}`}
                          index={index}
                        >
                          {(provided, snapshot) => (
                            <div
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              className={`
                                flex items-center gap-2 p-2 bg-white border rounded-lg cursor-move
                                ${snapshot.isDragging ? 'shadow-lg border-indigo-500' : 'border-gray-200'}
                              `}
                            >
                              <GripVertical className="w-4 h-4 text-gray-400" />
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm truncate">{place.name}</p>
                                {place.category && (
                                  <p className="text-xs text-gray-500">{place.category}</p>
                                )}
                              </div>
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                      {availablePlaces.length === 0 && (
                        <p className="text-sm text-gray-500 text-center py-8">
                          {t('routes.allPlacesAddedToRoute')}
                        </p>
                      )}
                    </div>
                  )}
                </Droppable>
              </div>

              {/* Route Order */}
              <div>
                <h4 className="font-medium mb-2">Routen-Reihenfolge ({newRoute.place_ids.length})</h4>
                <Droppable droppableId="route-places">
                  {(provided) => (
                    <div
                      {...provided.droppableProps}
                      ref={provided.innerRef}
                      className="space-y-2 min-h-[200px] max-h-[400px] overflow-y-auto p-3 bg-indigo-50 rounded-lg border-2 border-dashed border-indigo-300"
                    >
                      {newRoute.place_ids.map((placeId, index) => {
                        const place = getPlaceById(placeId)
                        if (!place) return null

                        return (
                          <Draggable
                            key={`route-place-${placeId}`}
                            draggableId={`route-place-${placeId}`}
                            index={index}
                          >
                            {(provided, snapshot) => (
                              <div
                                ref={provided.innerRef}
                                {...provided.draggableProps}
                                {...provided.dragHandleProps}
                                className={`
                                  flex items-center gap-2 p-2 bg-white border rounded-lg
                                  ${snapshot.isDragging ? 'shadow-lg border-indigo-500' : 'border-gray-200'}
                                `}
                              >
                                <span className="flex items-center justify-center w-6 h-6 bg-indigo-500 text-white text-xs font-bold rounded-full">
                                  {index + 1}
                                </span>
                                <GripVertical className="w-4 h-4 text-gray-400" />
                                <div className="flex-1 min-w-0">
                                  <p className="font-medium text-sm truncate">{place.name}</p>
                                  {place.category && (
                                    <p className="text-xs text-gray-500">{place.category}</p>
                                  )}
                                </div>
                                <button
                                  onClick={() => removePlace(index)}
                                  className="text-red-500 hover:text-red-700"
                                >
                                  <Minus className="w-4 h-4" />
                                </button>
                              </div>
                            )}
                          </Draggable>
                        )
                      })}
                      {provided.placeholder}
                      {newRoute.place_ids.length === 0 && (
                        <p className="text-sm text-gray-500 text-center py-8">
                          Ziehe Orte hierher um eine Route zu erstellen
                        </p>
                      )}
                    </div>
                  )}
                </Droppable>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={handleSaveRoute}
                className="btn btn-primary flex items-center gap-2"
                disabled={!newRoute.name || newRoute.place_ids.length < 2}
              >
                <Save className="w-4 h-4" />
                {editingRoute ? 'Route aktualisieren' : 'Route speichern'}
              </button>
              <button
                onClick={resetForm}
                className="btn btn-outline"
              >
                Abbrechen
              </button>
            </div>
          </div>
        </DragDropContext>
      )}
    </div>
  )
}
