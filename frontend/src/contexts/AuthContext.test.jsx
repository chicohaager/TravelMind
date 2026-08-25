/**
 * Wächter gegen einen Fehler, der am 2026-08-25 in der laufenden Produktion
 * gemessen wurde.
 *
 * Nach einem Kontowechsel OHNE Neuladen der Seite zeigte die Oberfläche die
 * Reisen des VORIGEN Kontos. Ursache: der React-Query-Schlüssel heißt überall
 * nur `['trips']` — er trägt das Konto nicht —, und `staleTime: 5 min`
 * verhindert, dass überhaupt neu geladen wird. Im Server-Protokoll standen
 * zwei erfolgreiche Anmeldungen und genau EIN `/api/trips`-Aufruf.
 *
 * Das ist nicht nur falsch, sondern ein Datenschutzproblem: auf einem
 * geteilten Rechner sieht der Nächste die Liste des Vorigen.
 *
 * Geprüft wird die Eigenschaft am Zwischenspeicher selbst, nicht an einer
 * Bildschirmausgabe — ein Test auf gerenderten Text hätte sich mit einem
 * beliebigen anderen Ladepfad zufriedengegeben.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { authService } from '@/services/api'

vi.mock('@/services/api', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

function bauen() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity, staleTime: Infinity } },
  })
  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>{children}</AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
  return { queryClient, wrapper }
}

describe('AuthContext: der Zwischenspeicher gehört zum Konto', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    authService.getCurrentUser.mockResolvedValue({ data: { id: 2, username: 'der Betreiber' } })
    authService.login.mockResolvedValue({ data: { access_token: 'token-fuer-Holgi' } })
    authService.register.mockResolvedValue({ data: { access_token: 'token-fuer-neu' } })
    authService.logout.mockResolvedValue({})
  })

  it('Positivkontrolle: der Aufbau legt überhaupt etwas in den Speicher', () => {
    const { queryClient } = bauen()
    queryClient.setQueryData(['trips'], [{ id: 1, title: 'Erste Reise' }])
    expect(queryClient.getQueryData(['trips'])).toHaveLength(1)
  })

  it('Abmelden leert den Zwischenspeicher', async () => {
    const { queryClient, wrapper } = bauen()
    queryClient.setQueryData(['trips'], [{ id: 1, title: 'Erste Reise' }])

    const { result } = renderHook(() => useAuth(), { wrapper })
    await act(async () => {
      await result.current.logout()
    })

    expect(queryClient.getQueryData(['trips'])).toBeUndefined()
  })

  it('Anmelden leert den Zwischenspeicher des vorigen Kontos', async () => {
    // Der Fall, der in der Produktion auftrat: die vorige Sitzung endete
    // NICHT über logout (abgelaufenes Token, zweiter Tab, harter Reload).
    const { queryClient, wrapper } = bauen()
    queryClient.setQueryData(['trips'], [{ id: 1, title: 'Reise des anderen Kontos' }])

    const { result } = renderHook(() => useAuth(), { wrapper })
    await act(async () => {
      await result.current.login('der Betreiber', 'geheim')
    })

    expect(queryClient.getQueryData(['trips'])).toBeUndefined()
  })

  it('Registrieren leert den Zwischenspeicher ebenfalls', async () => {
    const { queryClient, wrapper } = bauen()
    queryClient.setQueryData(['trips'], [{ id: 1, title: 'Fremd' }])

    const { result } = renderHook(() => useAuth(), { wrapper })
    await act(async () => {
      await result.current.register('neu', 'neu@example.com', 'ein-langes-passwort', 'Neu')
    })

    expect(queryClient.getQueryData(['trips'])).toBeUndefined()
  })

  it('Abmelden entfernt auch das Token', async () => {
    // `localStorage` ist in src/test/setup.js eine Attrappe mit vi.fn(); es
    // SPEICHERT nichts. Geprüft wird deshalb der Aufruf, nicht der Inhalt —
    // sonst prüft der Test die Attrappe statt den Code.
    const { wrapper } = bauen()
    const { result } = renderHook(() => useAuth(), { wrapper })
    await act(async () => {
      await result.current.logout()
    })
    expect(localStorage.removeItem).toHaveBeenCalledWith('token')
  })

  it('eine gescheiterte Abmeldung am Server beendet die Sitzung trotzdem lokal', async () => {
    authService.logout.mockRejectedValue(new Error('offline'))
    const { queryClient, wrapper } = bauen()
    queryClient.setQueryData(['trips'], [{ id: 1 }])

    const { result } = renderHook(() => useAuth(), { wrapper })
    await act(async () => {
      await result.current.logout()
    })

    expect(localStorage.removeItem).toHaveBeenCalledWith('token')
    expect(queryClient.getQueryData(['trips'])).toBeUndefined()
  })

  it('nach der Anmeldung ist das neue Konto gesetzt', async () => {
    const { wrapper } = bauen()
    const { result } = renderHook(() => useAuth(), { wrapper })
    await act(async () => {
      await result.current.login('der Betreiber', 'geheim')
    })
    await waitFor(() => expect(result.current.user?.username).toBe('der Betreiber'))
    expect(localStorage.setItem).toHaveBeenCalledWith('token', 'token-fuer-Holgi')
  })
})
