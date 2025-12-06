/**
 * Offline Sync Queue Service
 * Handles queuing and syncing offline operations
 */

import indexedDB from './indexedDB'
import { tripsService, diaryService, placesService } from './api'
import toast from 'react-hot-toast'
import i18n from '@/i18n'

class SyncQueueService {
  constructor() {
    this.isSyncing = false
    this.syncListeners = []
  }

  /**
   * Add a listener for sync events
   */
  onSyncStatusChange(callback) {
    this.syncListeners.push(callback)
    return () => {
      this.syncListeners = this.syncListeners.filter(cb => cb !== callback)
    }
  }

  /**
   * Notify all listeners of sync status
   */
  notifySyncStatus(status) {
    this.syncListeners.forEach(listener => listener(status))
  }

  /**
   * Queue an operation for later sync
   */
  async queueOperation(operation) {
    try {
      await indexedDB.addToSyncQueue({
        operation: operation.type,
        method: operation.method,
        endpoint: operation.endpoint,
        data: operation.data,
        entityType: operation.entityType,
        tempId: operation.tempId || `temp_${Date.now()}_${Math.random()}`,
        metadata: operation.metadata || {}
      })

      console.log('Operation queued:', operation)
      return true
    } catch (error) {
      console.error('Error queuing operation:', error)
      return false
    }
  }

  /**
   * Process the sync queue
   */
  async processSyncQueue() {
    if (this.isSyncing) {
      console.log('Sync already in progress, skipping...')
      return
    }

    // Check if online
    if (!navigator.onLine) {
      console.log('Offline - cannot sync')
      return
    }

    this.isSyncing = true
    this.notifySyncStatus({ syncing: true, progress: 0 })

    try {
      const pendingItems = await indexedDB.getSyncQueue('pending')
      console.log(`Processing ${pendingItems.length} pending sync items...`)

      if (pendingItems.length === 0) {
        this.notifySyncStatus({ syncing: false, success: true })
        this.isSyncing = false
        return
      }

      let processed = 0
      let succeeded = 0
      let failed = 0

      for (const item of pendingItems) {
        try {
          await indexedDB.updateSyncQueueItem(item.id, { status: 'syncing' })

          // Execute the queued operation
          const result = await this.executeOperation(item)

          // Mark as completed
          await indexedDB.updateSyncQueueItem(item.id, {
            status: 'completed',
            completed_at: new Date().toISOString(),
            result
          })

          succeeded++

          // Remove completed item after a delay
          setTimeout(() => indexedDB.removeSyncQueueItem(item.id), 5000)
        } catch (error) {
          console.error('Error syncing item:', error)

          const retries = (item.retries || 0) + 1
          const maxRetries = 3

          if (retries >= maxRetries) {
            // Mark as failed after max retries
            await indexedDB.updateSyncQueueItem(item.id, {
              status: 'failed',
              error: error.message,
              retries,
              failed_at: new Date().toISOString()
            })
            failed++
          } else {
            // Mark as pending for retry
            await indexedDB.updateSyncQueueItem(item.id, {
              status: 'pending',
              error: error.message,
              retries
            })
          }
        }

        processed++
        this.notifySyncStatus({
          syncing: true,
          progress: (processed / pendingItems.length) * 100
        })
      }

      console.log(`Sync complete: ${succeeded} succeeded, ${failed} failed`)

      // Show toast notification
      if (succeeded > 0 && failed === 0) {
        toast.success(i18n.t('offline:changesSynced', { count: succeeded }))
      } else if (failed > 0) {
        toast.error(i18n.t('offline:changesFailedToSync', { count: failed }))
      }

      this.notifySyncStatus({
        syncing: false,
        success: failed === 0,
        succeeded,
        failed
      })
    } catch (error) {
      console.error('Error processing sync queue:', error)
      this.notifySyncStatus({ syncing: false, error: error.message })
    } finally {
      this.isSyncing = false
    }
  }

  /**
   * Execute a queued operation
   */
  async executeOperation(item) {
    const { operation, method, data, entityType, tempId } = item

    console.log('Executing operation:', operation, entityType, method)

    switch (entityType) {
      case 'trip':
        return this.executeTripOperation(operation, method, data, tempId)
      case 'diary':
        return this.executeDiaryOperation(operation, method, data, tempId)
      case 'place':
        return this.executePlaceOperation(operation, method, data, tempId)
      default:
        throw new Error(`Unknown entity type: ${entityType}`)
    }
  }

  /**
   * Execute trip operations
   */
  async executeTripOperation(operation, method, data, tempId) {
    switch (operation) {
      case 'create':
        const tripResponse = await tripsService.create(data)
        // Update local cache with real ID
        await indexedDB.saveTrip(tripResponse.data)
        return tripResponse.data

      case 'update':
        const updateResponse = await tripsService.update(data.id, data)
        await indexedDB.saveTrip(updateResponse.data)
        return updateResponse.data

      case 'delete':
        await tripsService.delete(data.id)
        await indexedDB.deleteTrip(data.id)
        return { deleted: true }

      default:
        throw new Error(`Unknown trip operation: ${operation}`)
    }
  }

  /**
   * Execute diary operations
   */
  async executeDiaryOperation(operation, method, data, tempId) {
    switch (operation) {
      case 'create':
        const diaryResponse = await diaryService.create(data.trip_id, data)
        await indexedDB.saveDiaryEntry(diaryResponse.data)
        return diaryResponse.data

      case 'update':
        const updateResponse = await diaryService.update(data.id, data)
        await indexedDB.saveDiaryEntry(updateResponse.data)
        return updateResponse.data

      case 'delete':
        await diaryService.delete(data.id)
        await indexedDB.deleteDiaryEntry(data.id)
        return { deleted: true }

      case 'uploadPhoto':
        const photoResponse = await diaryService.uploadPhoto(data.entryId, data.file)
        return photoResponse.data

      default:
        throw new Error(`Unknown diary operation: ${operation}`)
    }
  }

  /**
   * Execute place operations
   */
  async executePlaceOperation(operation, method, data, tempId) {
    switch (operation) {
      case 'create':
        const placeResponse = await placesService.create(data.trip_id, data)
        await indexedDB.savePlace(placeResponse.data)
        return placeResponse.data

      case 'update':
        const updateResponse = await placesService.update(data.id, data)
        await indexedDB.savePlace(updateResponse.data)
        return updateResponse.data

      case 'delete':
        await placesService.delete(data.id)
        await indexedDB.deletePlace(data.id)
        return { deleted: true }

      case 'uploadPhoto':
        const photoResponse = await placesService.uploadPhoto(data.placeId, data.file)
        return photoResponse.data

      default:
        throw new Error(`Unknown place operation: ${operation}`)
    }
  }

  /**
   * Get sync queue statistics
   */
  async getStats() {
    const all = await indexedDB.getSyncQueue()
    return {
      total: all.length,
      pending: all.filter(item => item.status === 'pending').length,
      syncing: all.filter(item => item.status === 'syncing').length,
      failed: all.filter(item => item.status === 'failed').length,
      completed: all.filter(item => item.status === 'completed').length
    }
  }

  /**
   * Retry failed items
   */
  async retryFailed() {
    const failed = await indexedDB.getSyncQueue('failed')
    for (const item of failed) {
      await indexedDB.updateSyncQueueItem(item.id, {
        status: 'pending',
        retries: 0
      })
    }

    if (failed.length > 0) {
      toast.info(i18n.t('offline:retryingFailedOperations', { count: failed.length }))
      await this.processSyncQueue()
    }
  }

  /**
   * Clear completed items
   */
  async clearCompleted() {
    const completed = await indexedDB.getSyncQueue('completed')
    for (const item of completed) {
      await indexedDB.removeSyncQueueItem(item.id)
    }
    return completed.length
  }

  /**
   * Clear all sync queue items
   */
  async clearAll() {
    await indexedDB.clearSyncQueue()
    toast.success(i18n.t('offline:queueCleared'))
  }
}

// Export singleton instance
const syncQueueService = new SyncQueueService()
export default syncQueueService
