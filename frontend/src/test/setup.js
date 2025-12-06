/**
 * Vitest Test Setup
 *
 * This file is executed before each test file.
 * It sets up the testing environment with necessary mocks and matchers.
 */

import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Cleanup after each test case (unmount components, etc.)
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia (needed for responsive components)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver (needed for lazy loading, infinite scroll)
class MockIntersectionObserver {
  constructor(callback) {
    this.callback = callback
  }
  observe() { return null }
  unobserve() { return null }
  disconnect() { return null }
}
window.IntersectionObserver = MockIntersectionObserver

// Mock ResizeObserver (needed for some UI components)
class MockResizeObserver {
  observe() { return null }
  unobserve() { return null }
  disconnect() { return null }
}
window.ResizeObserver = MockResizeObserver

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock scrollTo
window.scrollTo = vi.fn()

// Suppress console errors/warnings in tests (optional, remove if you want to see them)
// vi.spyOn(console, 'error').mockImplementation(() => {})
// vi.spyOn(console, 'warn').mockImplementation(() => {})
