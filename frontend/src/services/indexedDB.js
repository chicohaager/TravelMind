/**
 * IndexedDB Service for Offline Data Storage
 * Stores trips, diary entries, places, and sync queue
 */

const DB_NAME = 'TravelMindDB'
const DB_VERSION = 1

// Object store names
const STORES = {
  TRIPS: 'trips',
  DIARY_ENTRIES: 'diary_entries',
  PLACES: 'places',
  SYNC_QUEUE: 'sync_queue',
  METADATA: 'metadata'
}

class IndexedDBService {
  constructor() {
    this.db = null
  }

  /**
   * Initialize the database
   */
  async init() {
    if (this.db) return this.db

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onerror = () => {
        console.error('IndexedDB error:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        this.db = request.result
        console.log('IndexedDB initialized successfully')
        resolve(this.db)
      }

      request.onupgradeneeded = (event) => {
        const db = event.target.result

        // Trips store
        if (!db.objectStoreNames.contains(STORES.TRIPS)) {
          const tripsStore = db.createObjectStore(STORES.TRIPS, { keyPath: 'id' })
          tripsStore.createIndex('user_id', 'user_id', { unique: false })
          tripsStore.createIndex('updated_at', 'updated_at', { unique: false })
        }

        // Diary entries store
        if (!db.objectStoreNames.contains(STORES.DIARY_ENTRIES)) {
          const diaryStore = db.createObjectStore(STORES.DIARY_ENTRIES, { keyPath: 'id' })
          diaryStore.createIndex('trip_id', 'trip_id', { unique: false })
          diaryStore.createIndex('entry_date', 'entry_date', { unique: false })
        }

        // Places store
        if (!db.objectStoreNames.contains(STORES.PLACES)) {
          const placesStore = db.createObjectStore(STORES.PLACES, { keyPath: 'id' })
          placesStore.createIndex('trip_id', 'trip_id', { unique: false })
          placesStore.createIndex('visited', 'visited', { unique: false })
        }

        // Sync queue store (for offline operations)
        if (!db.objectStoreNames.contains(STORES.SYNC_QUEUE)) {
          const syncStore = db.createObjectStore(STORES.SYNC_QUEUE, {
            keyPath: 'id',
            autoIncrement: true
          })
          syncStore.createIndex('timestamp', 'timestamp', { unique: false })
          syncStore.createIndex('status', 'status', { unique: false })
        }

        // Metadata store (for last sync times, etc.)
        if (!db.objectStoreNames.contains(STORES.METADATA)) {
          db.createObjectStore(STORES.METADATA, { keyPath: 'key' })
        }

        console.log('IndexedDB schema upgraded to version', DB_VERSION)
      }
    })
  }

  /**
   * Generic get operation
   */
  async get(storeName, key) {
    await this.init()
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(storeName, 'readonly')
      const store = transaction.objectStore(storeName)
      const request = store.get(key)

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * Generic getAll operation
   */
  async getAll(storeName, indexName = null, indexValue = null) {
    await this.init()
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(storeName, 'readonly')
      const store = transaction.objectStore(storeName)

      let request
      if (indexName && indexValue !== null) {
        const index = store.index(indexName)
        request = index.getAll(indexValue)
      } else {
        request = store.getAll()
      }

      request.onsuccess = () => resolve(request.result || [])
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * Generic put operation
   */
  async put(storeName, data) {
    await this.init()
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(storeName, 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.put(data)

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * Generic delete operation
   */
  async delete(storeName, key) {
    await this.init()
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(storeName, 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.delete(key)

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * Clear all data from a store
   */
  async clear(storeName) {
    await this.init()
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(storeName, 'readwrite')
      const store = transaction.objectStore(storeName)
      const request = store.clear()

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  // ==================== TRIPS ====================

  async saveTrip(trip) {
    return this.put(STORES.TRIPS, {
      ...trip,
      _cached_at: new Date().toISOString()
    })
  }

  async getTrip(tripId) {
    return this.get(STORES.TRIPS, tripId)
  }

  async getAllTrips() {
    return this.getAll(STORES.TRIPS)
  }

  async deleteTrip(tripId) {
    // Also delete associated diary entries and places
    const diaryEntries = await this.getDiaryEntriesByTrip(tripId)
    const places = await this.getPlacesByTrip(tripId)

    for (const entry of diaryEntries) {
      await this.delete(STORES.DIARY_ENTRIES, entry.id)
    }

    for (const place of places) {
      await this.delete(STORES.PLACES, place.id)
    }

    return this.delete(STORES.TRIPS, tripId)
  }

  // ==================== DIARY ENTRIES ====================

  async saveDiaryEntry(entry) {
    return this.put(STORES.DIARY_ENTRIES, {
      ...entry,
      _cached_at: new Date().toISOString()
    })
  }

  async getDiaryEntry(entryId) {
    return this.get(STORES.DIARY_ENTRIES, entryId)
  }

  async getDiaryEntriesByTrip(tripId) {
    return this.getAll(STORES.DIARY_ENTRIES, 'trip_id', tripId)
  }

  async deleteDiaryEntry(entryId) {
    return this.delete(STORES.DIARY_ENTRIES, entryId)
  }

  // ==================== PLACES ====================

  async savePlace(place) {
    return this.put(STORES.PLACES, {
      ...place,
      _cached_at: new Date().toISOString()
    })
  }

  async getPlace(placeId) {
    return this.get(STORES.PLACES, placeId)
  }

  async getPlacesByTrip(tripId) {
    return this.getAll(STORES.PLACES, 'trip_id', tripId)
  }

  async deletePlace(placeId) {
    return this.delete(STORES.PLACES, placeId)
  }

  // ==================== SYNC QUEUE ====================

  async addToSyncQueue(operation) {
    const queueItem = {
      ...operation,
      timestamp: new Date().toISOString(),
      status: 'pending', // pending, syncing, failed, completed
      retries: 0
    }
    return this.put(STORES.SYNC_QUEUE, queueItem)
  }

  async getSyncQueue(status = 'pending') {
    const allItems = await this.getAll(STORES.SYNC_QUEUE)
    if (!status) return allItems
    return allItems.filter(item => item.status === status)
  }

  async updateSyncQueueItem(id, updates) {
    const item = await this.get(STORES.SYNC_QUEUE, id)
    if (!item) throw new Error('Sync queue item not found')

    return this.put(STORES.SYNC_QUEUE, {
      ...item,
      ...updates
    })
  }

  async removeSyncQueueItem(id) {
    return this.delete(STORES.SYNC_QUEUE, id)
  }

  async clearSyncQueue() {
    return this.clear(STORES.SYNC_QUEUE)
  }

  // ==================== METADATA ====================

  async setMetadata(key, value) {
    return this.put(STORES.METADATA, { key, value, updated_at: new Date().toISOString() })
  }

  async getMetadata(key) {
    const result = await this.get(STORES.METADATA, key)
    return result?.value
  }

  async setLastSync(storeName) {
    return this.setMetadata(`last_sync_${storeName}`, new Date().toISOString())
  }

  async getLastSync(storeName) {
    return this.getMetadata(`last_sync_${storeName}`)
  }

  // ==================== BULK OPERATIONS ====================

  async saveTrips(trips) {
    const promises = trips.map(trip => this.saveTrip(trip))
    return Promise.all(promises)
  }

  async saveDiaryEntries(entries) {
    const promises = entries.map(entry => this.saveDiaryEntry(entry))
    return Promise.all(promises)
  }

  async savePlaces(places) {
    const promises = places.map(place => this.savePlace(place))
    return Promise.all(promises)
  }

  // ==================== UTILITY ====================

  async clearAll() {
    await this.clear(STORES.TRIPS)
    await this.clear(STORES.DIARY_ENTRIES)
    await this.clear(STORES.PLACES)
    await this.clear(STORES.SYNC_QUEUE)
    await this.clear(STORES.METADATA)
    console.log('All IndexedDB data cleared')
  }

  async getStorageStats() {
    const trips = await this.getAllTrips()
    const diary = await this.getAll(STORES.DIARY_ENTRIES)
    const places = await this.getAll(STORES.PLACES)
    const syncQueue = await this.getAll(STORES.SYNC_QUEUE)

    return {
      trips: trips.length,
      diary_entries: diary.length,
      places: places.length,
      sync_queue: syncQueue.length,
      pending_sync: syncQueue.filter(item => item.status === 'pending').length
    }
  }
}

// Export singleton instance
const indexedDB = new IndexedDBService()
export default indexedDB
