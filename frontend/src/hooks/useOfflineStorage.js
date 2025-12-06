/**
 * React Hook for Offline Storage with IndexedDB
 * Integrates with React Query for seamless online/offline experience
 */

import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import indexedDB from '@services/indexedDB'
import syncQueueService from '@services/syncQueue'
import toast from 'react-hot-toast'

/**
 * Hook to sync data between API and IndexedDB
 */
export const useOfflineSync = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [syncStatus, setSyncStatus] = useState({ syncing: false })
  const queryClient = useQueryClient()

  useEffect(() => {
    const handleOnline = async () => {
      setIsOnline(true)
      // Process sync queue when coming back online
      await syncQueueService.processSyncQueue()
      // Refresh all queries after sync
      queryClient.invalidateQueries()
    }

    const handleOffline = () => {
      setIsOnline(false)
    }

    // Subscribe to sync status changes
    const unsubscribe = syncQueueService.onSyncStatusChange((status) => {
      setSyncStatus(status)
    })

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      unsubscribe()
    }
  }, [queryClient])

  /**
   * Manually trigger sync
   */
  const triggerSync = async () => {
    await syncQueueService.processSyncQueue()
    queryClient.invalidateQueries()
  }

  return { isOnline, syncStatus, triggerSync }
}

/**
 * Hook to get trips with offline support
 */
export const useOfflineTrips = (apiQuery) => {
  const { isOnline } = useOfflineSync()
  const [cachedTrips, setCachedTrips] = useState([])
  const [loading, setLoading] = useState(true)

  // Load cached trips on mount
  useEffect(() => {
    const loadCached = async () => {
      try {
        const trips = await indexedDB.getAllTrips()
        setCachedTrips(trips)
        setLoading(false)
      } catch (error) {
        console.error('Error loading cached trips:', error)
        setLoading(false)
      }
    }
    loadCached()
  }, [])

  // API query with cache update
  const query = useQuery({
    ...apiQuery,
    enabled: isOnline && apiQuery.enabled !== false,
    onSuccess: async (data) => {
      // Save to IndexedDB
      try {
        if (Array.isArray(data)) {
          await indexedDB.saveTrips(data)
          await indexedDB.setLastSync('trips')
        }
      } catch (error) {
        console.error('Error caching trips:', error)
      }
      apiQuery.onSuccess?.(data)
    }
  })

  // Return cached data if offline or while loading
  const data = isOnline ? (query.data || cachedTrips) : cachedTrips

  return {
    ...query,
    data,
    isOffline: !isOnline,
    isCached: !isOnline || !query.data,
    isLoading: isOnline ? query.isLoading : loading
  }
}

/**
 * Hook to get diary entries with offline support
 */
export const useOfflineDiary = (tripId, apiQuery) => {
  const { isOnline } = useOfflineSync()
  const [cachedEntries, setCachedEntries] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadCached = async () => {
      try {
        const entries = await indexedDB.getDiaryEntriesByTrip(tripId)
        setCachedEntries(entries)
        setLoading(false)
      } catch (error) {
        console.error('Error loading cached diary entries:', error)
        setLoading(false)
      }
    }
    if (tripId) loadCached()
  }, [tripId])

  const query = useQuery({
    ...apiQuery,
    enabled: isOnline && !!tripId && apiQuery.enabled !== false,
    onSuccess: async (data) => {
      try {
        if (Array.isArray(data)) {
          await indexedDB.saveDiaryEntries(data)
        }
      } catch (error) {
        console.error('Error caching diary entries:', error)
      }
      apiQuery.onSuccess?.(data)
    }
  })

  const data = isOnline ? (query.data || cachedEntries) : cachedEntries

  return {
    ...query,
    data,
    isOffline: !isOnline,
    isCached: !isOnline || !query.data,
    isLoading: isOnline ? query.isLoading : loading
  }
}

/**
 * Hook to get places with offline support
 */
export const useOfflinePlaces = (tripId, apiQuery) => {
  const { isOnline } = useOfflineSync()
  const [cachedPlaces, setCachedPlaces] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadCached = async () => {
      try {
        const places = await indexedDB.getPlacesByTrip(tripId)
        setCachedPlaces(places)
        setLoading(false)
      } catch (error) {
        console.error('Error loading cached places:', error)
        setLoading(false)
      }
    }
    if (tripId) loadCached()
  }, [tripId])

  const query = useQuery({
    ...apiQuery,
    enabled: isOnline && !!tripId && apiQuery.enabled !== false,
    onSuccess: async (data) => {
      try {
        if (Array.isArray(data)) {
          await indexedDB.savePlaces(data)
        }
      } catch (error) {
        console.error('Error caching places:', error)
      }
      apiQuery.onSuccess?.(data)
    }
  })

  const data = isOnline ? (query.data || cachedPlaces) : cachedPlaces

  return {
    ...query,
    data,
    isOffline: !isOnline,
    isCached: !isOnline || !query.data,
    isLoading: isOnline ? query.isLoading : loading
  }
}

/**
 * Hook to create mutations with offline queue support
 */
export const useOfflineMutation = (mutationFn, options = {}) => {
  const { t } = useTranslation()
  const { isOnline } = useOfflineSync()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (variables) => {
      if (isOnline) {
        // Online: execute normally
        return mutationFn(variables)
      } else {
        // Offline: add to sync queue
        await syncQueueService.queueOperation({
          type: options.operationType || 'unknown',
          method: options.method || 'POST',
          endpoint: options.endpoint,
          data: variables,
          entityType: options.entityType,
          metadata: options.metadata || {}
        })

        toast.success(t('offline:changeWillSync'))

        // Return optimistic data with temporary ID
        const tempId = `temp_${Date.now()}_${Math.random()}`
        return { ...variables, id: tempId, _temp: true }
      }
    },
    ...options,
    onSuccess: async (data, variables, context) => {
      // Cache the result if online
      if (isOnline && data && !data._temp) {
        try {
          if (options.entityType === 'trip') {
            await indexedDB.saveTrip(data)
          } else if (options.entityType === 'diary') {
            await indexedDB.saveDiaryEntry(data)
          } else if (options.entityType === 'place') {
            await indexedDB.savePlace(data)
          }
        } catch (error) {
          console.error('Error caching mutation result:', error)
        }
      }

      options.onSuccess?.(data, variables, context)
    }
  })
}

/**
 * Hook to get storage statistics
 */
export const useStorageStats = () => {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    const loadStats = async () => {
      try {
        const storageStats = await indexedDB.getStorageStats()
        setStats(storageStats)
      } catch (error) {
        console.error('Error loading storage stats:', error)
      }
    }
    loadStats()

    // Refresh stats every 10 seconds
    const interval = setInterval(loadStats, 10000)
    return () => clearInterval(interval)
  }, [])

  return stats
}

/**
 * Hook to clear all offline data
 */
export const useClearOfflineData = () => {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      await indexedDB.clearAll()
      queryClient.clear()
    },
    onSuccess: () => {
      toast.success(t('offline:dataDeleted'))
    },
    onError: (error) => {
      toast.error(t('offline:errorDeleting'))
      console.error(error)
    }
  })
}
