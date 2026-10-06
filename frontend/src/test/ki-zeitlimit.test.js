/**
 * Wächter: KI-Aufrufe dürfen nicht am Standard-Zeitlimit abbrechen.
 *
 * Am 2026-08-26 gegen die laufende Instanz gemessen. Im nginx-Zugriffs-
 * protokoll des Frontend-Containers stand:
 *
 *   "POST /api/ai/personalized-recommendations HTTP/1.1" 499 0 rt=30.001
 *
 * 499 heißt bei nginx: der Browser hat aufgelegt. Die 30,001 s sind exakt der
 * Standardwert der axios-Instanz. Das Backend rechnete danach weiter — die
 * Bildsuche protokollierte noch Sekunden später echte Ortsnamen —, nur sah das
 * niemand mehr: im Browser stand „Keine Empfehlungen verfügbar".
 *
 * Genau die gefährliche Sorte Fehler: ein Abbruch, der aussieht wie ein
 * Ergebnis. Deshalb prüft dieser Test jede einzelne KI-Methode, nicht nur eine
 * Stichprobe — es genügt, eine beim Erweitern zu vergessen.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

const post = vi.fn(() => Promise.resolve({ data: {} }))
const get = vi.fn(() => Promise.resolve({ data: {} }))

vi.mock('axios', () => ({
  default: {
    create: () => ({
      post,
      get,
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    }),
  },
}))

const { aiService, KI_ZEITLIMIT_MS } = await import('@/services/api')

// Jeder Eintrag: Name der Methode und ein Aufruf mit plausiblen Argumenten.
const KI_AUFRUFE = {
  suggest: () => aiService.suggest({ interests: ['Kultur'], duration: 7 }),
  plan: () => aiService.plan({ destination: 'Zagreb', duration: 3, interests: [] }),
  describe: () => aiService.describe('Zagreb'),
  chat: () => aiService.chat('Wo esse ich?', null),
  localTips: () => aiService.localTips('Zagreb'),
  getTripSuggestions: () => aiService.getTripSuggestions('Zagreb'),
  getPersonalizedRecommendations: () =>
    aiService.getPersonalizedRecommendations({ destination: 'Zagreb' }),
}

describe('KI-Zeitlimit', () => {
  beforeEach(() => post.mockClear())

  it('ist länger als das Standardlimit von 30 s', () => {
    // Ohne diese Zeile wären alle Tests unten auch bei KI_ZEITLIMIT_MS = 1000
    // grün: sie vergleichen gegen dieselbe Konstante.
    expect(KI_ZEITLIMIT_MS).toBeGreaterThanOrEqual(120000)
  })

  it.each(Object.keys(KI_AUFRUFE))('%s schickt das lange Zeitlimit mit', async (name) => {
    await KI_AUFRUFE[name]()
    expect(post).toHaveBeenCalledTimes(1)
    const optionen = post.mock.calls[0].at(-1)
    expect(optionen?.timeout).toBe(KI_ZEITLIMIT_MS)
  })

  it('deckt jede Methode von aiService ab', () => {
    // Gegenkontrolle gegen die Liste oben: eine neu hinzugefügte KI-Methode
    // fällt hier auf, statt still ohne Zeitlimit zu bleiben.
    expect(Object.keys(aiService).sort()).toEqual(Object.keys(KI_AUFRUFE).sort())
  })
})
