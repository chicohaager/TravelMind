import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, CalendarDays } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import { timelineService } from '@services/api'
import TimelineDay from './TimelineDay'
import AddToTimelineModal from './AddToTimelineModal'

export default function TimelineView({ tripId, places, tripStartDate, tripEndDate }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [expandedDays, setExpandedDays] = useState(new Set())

  // Fetch timeline
  const { data: timeline = [], isLoading } = useQuery({
    queryKey: ['timeline', tripId],
    queryFn: async () => {
      const response = await timelineService.getTimeline(tripId)
      return response.data
    },
    enabled: !!tripId
  })

  // Create timeline entry mutation
  const createEntryMutation = useMutation({
    mutationFn: async (data) => {
      const response = await timelineService.create(tripId, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['timeline', tripId])
      setIsAddModalOpen(false)
      toast.success('Zur Timeline hinzugefügt')
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || t('timeline.errorAdding'))
    }
  })

  // Delete timeline entry mutation
  const deleteEntryMutation = useMutation({
    mutationFn: async (entryId) => {
      await timelineService.delete(entryId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['timeline', tripId])
      toast.success('Aus Timeline entfernt')
    },
    onError: () => {
      toast.error(t('timeline.errorDeleting'))
    }
  })

  // Reorder mutation
  const reorderMutation = useMutation({
    mutationFn: async ({ entryIds }) => {
      await timelineService.reorder(tripId, entryIds)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['timeline', tripId])
    }
  })

  // Optimize mutation
  const optimizeMutation = useMutation({
    mutationFn: async (dayDate) => {
      const response = await timelineService.optimize(tripId, dayDate)
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries(['timeline', tripId])
      toast.success(data.message || 'Route optimiert')
    },
    onError: () => {
      toast.error(t('timeline.errorOptimizing'))
    }
  })

  const handleAddEntry = async (data) => {
    await createEntryMutation.mutateAsync(data)
  }

  const handleDeleteEntry = async (entryId) => {
    if (confirm('Aus Timeline entfernen?')) {
      await deleteEntryMutation.mutateAsync(entryId)
    }
  }

  const handleReorder = (dayDate, newOrder) => {
    // Optimistic update
    const entryIds = newOrder.map((entry) => entry.id)
    reorderMutation.mutate({ entryIds })
  }

  const handleOptimize = async (dayDate) => {
    await optimizeMutation.mutateAsync(dayDate)
  }

  const toggleDayExpansion = (dayDate) => {
    setExpandedDays((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(dayDate)) {
        newSet.delete(dayDate)
      } else {
        newSet.add(dayDate)
      }
      return newSet
    })
  }

  // Expand first day by default
  if (timeline.length > 0 && expandedDays.size === 0) {
    setExpandedDays(new Set([timeline[0].day_date]))
  }

  if (isLoading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="card">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <CalendarDays className="w-6 h-6" />
            Tagesplaner
          </h2>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="btn btn-primary btn-sm"
            disabled={!places || places.length === 0}
          >
            <Plus className="w-4 h-4" />
            Zum Tagesplan hinzufügen
          </button>
        </div>

        {timeline.length === 0 ? (
          <div className="text-center py-12">
            <CalendarDays className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              {t('timeline.noEntriesYet')}
            </p>
            {places && places.length > 0 ? (
              <button
                onClick={() => setIsAddModalOpen(true)}
                className="btn btn-primary"
              >
                <Plus className="w-4 h-4" />
                Ersten Eintrag hinzufügen
              </button>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-500">
                Füge zuerst Orte hinzu, um sie zu planen.
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {timeline.map((day) => (
              <TimelineDay
                key={day.day_date}
                day={day}
                onReorder={(newOrder) => handleReorder(day.day_date, newOrder)}
                onDeleteEntry={handleDeleteEntry}
                onOptimize={handleOptimize}
                isExpanded={expandedDays.has(day.day_date)}
                onToggleExpand={() => toggleDayExpansion(day.day_date)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Add to Timeline Modal */}
      <AddToTimelineModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSubmit={handleAddEntry}
        places={places}
        tripStartDate={tripStartDate}
        tripEndDate={tripEndDate}
      />
    </>
  )
}
