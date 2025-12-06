/**
 * Test Utilities
 *
 * Provides helper functions and custom render methods for testing.
 */

import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/contexts/AuthContext'
import { vi } from 'vitest'

/**
 * Create a fresh QueryClient for testing
 */
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {}, // Suppress error logs in tests
    },
  })
}

/**
 * All Providers wrapper for testing
 */
function AllProviders({ children }) {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          {children}
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

/**
 * Custom render function that wraps component with all providers
 */
function customRender(ui, options = {}) {
  return render(ui, { wrapper: AllProviders, ...options })
}

/**
 * Render with custom query client (for testing query states)
 */
function renderWithQueryClient(ui, queryClient) {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {ui}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

/**
 * Create a mock user object
 */
function createMockUser(overrides = {}) {
  return {
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    full_name: 'Test User',
    avatar_url: null,
    is_active: true,
    is_superuser: false,
    created_at: new Date().toISOString(),
    ...overrides,
  }
}

/**
 * Create a mock trip object
 */
function createMockTrip(overrides = {}) {
  return {
    id: 1,
    title: 'Test Trip',
    destination: 'Test City',
    description: 'A test trip description',
    start_date: '2024-01-01T00:00:00Z',
    end_date: '2024-01-07T00:00:00Z',
    latitude: 48.8566,
    longitude: 2.3522,
    interests: ['culture', 'food'],
    budget: 1000,
    currency: 'EUR',
    cover_image: null,
    created_at: new Date().toISOString(),
    updated_at: null,
    ...overrides,
  }
}

/**
 * Create a mock diary entry
 */
function createMockDiaryEntry(overrides = {}) {
  return {
    id: 1,
    title: 'Test Entry',
    content: '# Day 1\n\nGreat day!',
    entry_date: '2024-01-01T00:00:00Z',
    location_name: 'Test Location',
    latitude: 48.8566,
    longitude: 2.3522,
    photos: [],
    tags: ['adventure'],
    mood: 'happy',
    rating: 5,
    created_at: new Date().toISOString(),
    updated_at: null,
    ...overrides,
  }
}

/**
 * Wait for async operations to complete
 */
async function waitForLoadingToFinish() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

/**
 * Mock the API service
 */
function mockApiService() {
  return {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
  }
}

// Re-export everything from testing-library
export * from '@testing-library/react'

// Export custom utilities
export {
  customRender as render,
  renderWithQueryClient,
  createTestQueryClient,
  createMockUser,
  createMockTrip,
  createMockDiaryEntry,
  waitForLoadingToFinish,
  mockApiService,
  AllProviders,
}
