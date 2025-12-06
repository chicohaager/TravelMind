/**
 * API Service Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock axios before importing api
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    }
  }

  return {
    default: {
      create: vi.fn(() => mockAxiosInstance)
    }
  }
})

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset localStorage mock
    window.localStorage.getItem.mockReturnValue(null)
  })

  describe('Configuration', () => {
    it('should create axios instance with baseURL', async () => {
      const axios = (await import('axios')).default

      // Import api to trigger axios.create
      await import('./api')

      expect(axios.create).toHaveBeenCalled()
      const config = axios.create.mock.calls[0][0]
      expect(config.baseURL).toBeDefined()
    })

    it('should set default timeout', async () => {
      const axios = (await import('axios')).default
      await import('./api')

      const config = axios.create.mock.calls[0][0]
      expect(config.timeout).toBe(30000) // 30 seconds
    })

    it('should set Content-Type header', async () => {
      const axios = (await import('axios')).default
      await import('./api')

      const config = axios.create.mock.calls[0][0]
      expect(config.headers['Content-Type']).toBe('application/json')
    })
  })

  describe('Service Exports', () => {
    it('should export aiService', async () => {
      const { aiService } = await import('./api')
      expect(aiService).toBeDefined()
      expect(aiService.suggest).toBeDefined()
      expect(aiService.chat).toBeDefined()
    })

    it('should export tripsService', async () => {
      const { tripsService } = await import('./api')
      expect(tripsService).toBeDefined()
      expect(tripsService.getAll).toBeDefined()
      expect(tripsService.create).toBeDefined()
    })

    it('should export diaryService', async () => {
      const { diaryService } = await import('./api')
      expect(diaryService).toBeDefined()
      expect(diaryService.getEntries).toBeDefined()
      expect(diaryService.create).toBeDefined()
    })

    it('should export authService', async () => {
      const { authService } = await import('./api')
      expect(authService).toBeDefined()
      expect(authService.login).toBeDefined()
      expect(authService.register).toBeDefined()
    })
  })
})
