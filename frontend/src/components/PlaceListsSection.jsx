import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus, ChevronDown, ChevronRight, MoreVertical, Edit, Trash2,
  MapPin, Sparkles, X, Check
} from 'lucide-react'
import { placesService } from '@/services/api'
import toast from 'react-hot-toast'
import PlaceCard from './PlaceCard'
import { clsx } from 'clsx'
import { useTranslation } from 'react-i18next'

const EMOJI_PRESETS = [
  { emoji: '🍽️', label: 'Restaurants' },
  { emoji: '🏛️', label: 'Museums' },
  { emoji: '🏖️', label: 'Beaches' },
  { emoji: '🌳', label: 'Parks' },
  { emoji: '🎯', label: 'Attractions' },
  { emoji: '🛍️', label: 'Shopping' },
  { emoji: '🎉', label: 'Nightlife' },
  { emoji: '☕', label: 'Cafes' },
  { emoji: '🏨', label: 'Hotels' },
  { emoji: '👁️', label: 'Viewpoints' },
]

const COLOR_PRESETS = [
  '#6366F1', // Indigo
  '#F59E0B', // Orange
  '#10B981', // Green
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#EF4444', // Red
  '#14B8A6', // Teal
]

export default function PlaceListsSection({
  tripId,
  places = [],
  onEditPlace,
  onDeletePlace,
  onToggleVisited,
  onPlaceClick
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [isCreatingList, setIsCreatingList] = useState(false)
  const [editingListId, setEditingListId] = useState(null)
  const [newListTitle, setNewListTitle] = useState('')
  const [newListIcon, setNewListIcon] = useState('📍')
  const [newListColor, setNewListColor] = useState('#6366F1')
  const [collapsedLists, setCollapsedLists] = useState(new Set())

  // Fetch custom lists
  const { data: placeLists = [] } = useQuery({
    queryKey: ['placeLists', tripId],
    queryFn: async () => {
      const response = await placesService.getLists(tripId)
      return response.data
    },
    enabled: !!tripId
  })

  // Create list mutation
  const createListMutation = useMutation({
    mutationFn: async (data) => {
      const response = await placesService.createList(tripId, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['placeLists', tripId])
      setIsCreatingList(false)
      setNewListTitle('')
      setNewListIcon('📍')
      setNewListColor('#6366F1')
      toast.success(t('placeLists.listCreated'))
    },
    onError: () => {
      toast.error(t('placeLists.errorCreating'))
    }
  })

  // Update list mutation
  const updateListMutation = useMutation({
    mutationFn: async ({ listId, data }) => {
      const response = await placesService.updateList(listId, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['placeLists', tripId])
      setEditingListId(null)
      toast.success(t('placeLists.listUpdated'))
    },
    onError: () => {
      toast.error(t('placeLists.errorUpdating'))
    }
  })

  // Delete list mutation
  const deleteListMutation = useMutation({
    mutationFn: async (listId) => {
      await placesService.deleteList(listId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['placeLists', tripId])
      queryClient.invalidateQueries(['places', tripId])
      toast.success(t('placeLists.listDeleted'))
    },
    onError: () => {
      toast.error(t('placeLists.errorDeleting'))
    }
  })

  const handleCreateList = async () => {
    if (!newListTitle.trim()) {
      toast.error(t('placeLists.pleaseEnterTitle'))
      return
    }

    await createListMutation.mutateAsync({
      title: newListTitle,
      icon: newListIcon,
      color: newListColor,
      is_collapsed: false
    })
  }

  const handleDeleteList = async (listId) => {
    if (confirm(t('placeLists.confirmDeleteList'))) {
      await deleteListMutation.mutateAsync(listId)
    }
  }

  const toggleListCollapse = (listId) => {
    setCollapsedLists(prev => {
      const newSet = new Set(prev)
      if (newSet.has(listId)) {
        newSet.delete(listId)
      } else {
        newSet.add(listId)
      }
      return newSet
    })
  }

  // Group places by list
  const placesWithoutList = places.filter(p => !p.list_id)
  const placesByList = placeLists.map(list => ({
    ...list,
    places: places.filter(p => p.list_id === list.id)
  }))

  // Recommended places section (places without a custom list and no visit_date)
  const recommendedPlaces = placesWithoutList.filter(p => !p.visit_date)

  return (
    <div className="space-y-4">
      {/* Recommended Places Section */}
      {recommendedPlaces.length > 0 && (
        <div className="card">
          <button
            onClick={() => toggleListCollapse('recommended')}
            className="w-full flex items-center justify-between mb-4 hover:opacity-80 transition-opacity"
          >
            <div className="flex items-center gap-2">
              {collapsedLists.has('recommended') ? (
                <ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              )}
              <Sparkles className="w-5 h-5 text-primary-600" />
              <h3 className="text-lg font-bold">{t('placeLists.recommendedPlaces')}</h3>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                ({recommendedPlaces.length})
              </span>
            </div>
          </button>

          <AnimatePresence>
            {!collapsedLists.has('recommended') && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="space-y-3"
              >
                {recommendedPlaces.map((place) => (
                  <PlaceCard
                    key={place.id}
                    place={place}
                    onEdit={onEditPlace}
                    onDelete={onDeletePlace}
                    onToggleVisited={onToggleVisited}
                    onClick={() => onPlaceClick && onPlaceClick(place)}
                  />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Custom Place Lists */}
      {placesByList.map((list) => (
        <div key={list.id} className="card" style={{ borderLeft: `4px solid ${list.color}` }}>
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => toggleListCollapse(list.id)}
              className="flex-1 flex items-center gap-2 hover:opacity-80 transition-opacity"
            >
              {collapsedLists.has(list.id) ? (
                <ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              )}
              <span className="text-2xl">{list.icon}</span>
              <h3 className="text-lg font-bold">{list.title}</h3>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                ({list.places.length})
              </span>
            </button>

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleDeleteList(list.id)}
                className="p-2 text-gray-600 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/20 transition-colors"
                title={t('placeLists.deleteList')}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          <AnimatePresence>
            {!collapsedLists.has(list.id) && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="space-y-3"
              >
                {list.places.length > 0 ? (
                  list.places.map((place) => (
                    <PlaceCard
                      key={place.id}
                      place={place}
                      onEdit={onEditPlace}
                      onDelete={onDeletePlace}
                      onToggleVisited={onToggleVisited}
                      onClick={() => onPlaceClick && onPlaceClick(place)}
                    />
                  ))
                ) : (
                  <p className="text-sm text-gray-600 dark:text-gray-400 text-center py-4">
                    {t('placeLists.noPlacesInList')}
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}

      {/* Create New List Button */}
      {!isCreatingList ? (
        <button
          onClick={() => setIsCreatingList(true)}
          className="w-full btn btn-outline flex items-center justify-center gap-2"
        >
          <Plus className="w-5 h-5" />
          {t('placeLists.createNewList')}
        </button>
      ) : (
        <div className="card border-2 border-primary-500">
          <h3 className="text-lg font-bold mb-4">{t('placeLists.createNewList')}</h3>

          <div className="space-y-4">
            {/* Title */}
            <div>
              <label className="block text-sm font-medium mb-2">
                {t('placeLists.title')} <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={newListTitle}
                onChange={(e) => setNewListTitle(e.target.value)}
                placeholder={t('placeLists.titlePlaceholder')}
                className="input w-full"
                autoFocus
              />
            </div>

            {/* Icon Selector */}
            <div>
              <label className="block text-sm font-medium mb-2">{t('placeLists.icon')}</label>
              <div className="flex flex-wrap gap-2">
                {EMOJI_PRESETS.map(({ emoji, label }) => (
                  <button
                    key={emoji}
                    onClick={() => setNewListIcon(emoji)}
                    className={clsx(
                      'text-2xl p-2 rounded-lg border-2 transition-all',
                      newListIcon === emoji
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-primary-300'
                    )}
                    title={label}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            </div>

            {/* Color Selector */}
            <div>
              <label className="block text-sm font-medium mb-2">{t('placeLists.color')}</label>
              <div className="flex flex-wrap gap-2">
                {COLOR_PRESETS.map((color) => (
                  <button
                    key={color}
                    onClick={() => setNewListColor(color)}
                    className={clsx(
                      'w-10 h-10 rounded-lg border-2 transition-all',
                      newListColor === color
                        ? 'border-gray-900 dark:border-white scale-110'
                        : 'border-gray-200 dark:border-gray-700 hover:scale-105'
                    )}
                    style={{ backgroundColor: color }}
                    title={color}
                  />
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={handleCreateList}
                disabled={!newListTitle.trim() || createListMutation.isPending}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                <Check className="w-4 h-4" />
                {t('common.create')}
              </button>
              <button
                onClick={() => {
                  setIsCreatingList(false)
                  setNewListTitle('')
                  setNewListIcon('📍')
                  setNewListColor('#6366F1')
                }}
                disabled={createListMutation.isPending}
                className="btn-outline flex items-center gap-2"
              >
                <X className="w-4 h-4" />
                {t('common.cancel')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
