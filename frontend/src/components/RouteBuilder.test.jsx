/**
 * Wächter für den Fehler, den der Betreiber am 2026-08-25 gemeldet hat:
 * „Route speichern — Button ohne Funktion".
 *
 * Der Knopf war `disabled`, weil die Route weniger als zwei Orte hatte — und
 * Orte ließen sich AUSSCHLIESSLICH per Ziehen zwischen zwei scrollenden
 * Listen hinzufügen. Auf dem Telefon, also dem Gerät, mit dem man unterwegs
 * eine Route plant, ist das unzuverlässig. Der Nutzer sah einen Knopf, der
 * nichts tut, und erfuhr nirgends, warum.
 *
 * Behoben durch ➕ an jedem Ort und einen Hinweis, was noch fehlt. Diese
 * Suite hält BEIDES fest — von Hand geprüft war es einmal, hier wiederholt
 * es sich bei jedem Lauf.
 *
 * Ziehen wird hier NICHT geprüft: @hello-pangea/dnd braucht Layout, und
 * jsdom hat keins. Ein Ziehtest von hier wäre ein Ersatzsignal. Das Ziehen
 * ist im Browser per Tastatur nachgewiesen (siehe docs/ROADMAP.md).
 */

import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nextProvider } from 'react-i18next'
import i18n from '../i18n'
import RouteBuilder from './RouteBuilder'

vi.mock('../services/api', () => ({
  routesService: {
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    getByTrip: vi.fn(),
  },
}))

vi.mock('react-hot-toast', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
  default: { success: vi.fn(), error: vi.fn() },
}))

import { routesService } from '../services/api'

const ORTE = [
  { id: 1, name: 'Reeperbahn', category: 'nightlife' },
  { id: 2, name: 'Speicherstadt', category: 'attraction' },
  { id: 3, name: 'Elbphilharmonie', category: 'attraction' },
]

function zeigen(props = {}) {
  return render(
    <I18nextProvider i18n={i18n}>
      <RouteBuilder tripId={7} places={ORTE} routes={[]} {...props} />
    </I18nextProvider>
  )
}

const speicherknopf = () => screen.getByRole('button', { name: /Route speichern/i })

// In jsdom gibt es weder navigator.languages noch localStorage-Inhalt, also
// faellt die Spracherkennung auf `en` zurueck. Geprueft wird aber in der
// NUTZER-LOCALE — so steht es in CLAUDE.md, und es ist der einzige Weg, bei
// dem die Beschriftungen etwas ueber die echte Oberflaeche aussagen.
beforeAll(async () => {
  await i18n.changeLanguage('de')
  // Die Uebersetzungen werden nachgeladen; ohne dieses Warten stehen die
  // Schluessel auf den Knoepfen statt der Woerter.
  await i18n.loadNamespaces(['routes', 'common'])
})

beforeEach(() => {
  vi.clearAllMocks()
})

describe('RouteBuilder: die Pruefung laeuft auf Deutsch', () => {
  it('Positivkontrolle: sonst sagen die Beschriftungen nichts aus', () => {
    expect(i18n.resolvedLanguage).toBe('de')
    expect(i18n.t('routes:saveRoute')).toBe('Route speichern')
  })
})

describe('RouteBuilder: der Knopf sagt, was fehlt', () => {
  it('Positivkontrolle: das Formular lässt sich überhaupt öffnen', async () => {
    const nutzer = userEvent.setup()
    zeigen()
    await nutzer.click(screen.getByRole('button', { name: /Neue Route/i }))
    expect(speicherknopf()).toBeTruthy()
  })

  it('am Anfang fehlen Name UND zwei Orte — und beides steht da', async () => {
    const nutzer = userEvent.setup()
    zeigen()
    await nutzer.click(screen.getByRole('button', { name: /Neue Route/i }))

    expect(speicherknopf().disabled).toBe(true)
    const hinweis = screen.getByText(/Zum Speichern fehlt noch/i)
    expect(hinweis.textContent).toMatch(/Routenname/i)
    expect(hinweis.textContent).toMatch(/zwei Orte/i)
  })

  it('nach dem Namen fehlen nur noch die Orte', async () => {
    const nutzer = userEvent.setup()
    zeigen()
    await nutzer.click(screen.getByRole('button', { name: /Neue Route/i }))
    await nutzer.type(screen.getByPlaceholderText(/Stadttour/i), 'Tag 1')

    const hinweis = screen.getByText(/Zum Speichern fehlt noch/i)
    expect(hinweis.textContent).toMatch(/zwei Orte/i)
    expect(hinweis.textContent).not.toMatch(/Routenname/i)
    expect(speicherknopf().disabled).toBe(true)
  })
})

describe('RouteBuilder: Orte per Klick — nicht nur per Ziehen', () => {
  it('jeder verfügbare Ort hat einen Hinzufügen-Knopf', async () => {
    const nutzer = userEvent.setup()
    zeigen()
    await nutzer.click(screen.getByRole('button', { name: /Neue Route/i }))

    const plus = screen.getAllByRole('button', { name: /Zur Route hinzufügen/i })
    expect(plus).toHaveLength(ORTE.length)
  })

  it('ein Klick nimmt den Ort in die Route auf', async () => {
    const nutzer = userEvent.setup()
    zeigen()
    await nutzer.click(screen.getByRole('button', { name: /Neue Route/i }))
    await nutzer.click(screen.getAllByRole('button', { name: /Zur Route hinzufügen/i })[0])

    expect(screen.getByText(/Routen-Reihenfolge \(1\)/)).toBeTruthy()
  })

  it('ein aufgenommener Ort wird nicht mehr angeboten', async () => {
    // Die Eigenschaft, die wirklich gilt — und die verhindert, dass ein Ort
    // ueberhaupt zweimal angeklickt werden kann. Der erste Entwurf dieses
    // Tests nahm das Gegenteil an und klickte zweimal auf denselben Platz
    // in der Liste; dort stand dann aber schon der NAECHSTE Ort.
    const nutzer = userEvent.setup()
    zeigen()
    await nutzer.click(screen.getByRole('button', { name: /Neue Route/i }))
    const plus = () => screen.getAllByRole('button', { name: /Zur Route hinzufügen/i })
    expect(plus()).toHaveLength(3)

    await nutzer.click(screen.getByRole('button', { name: /Zur Route hinzufügen: Reeperbahn/i }))

    expect(screen.getByText(/Routen-Reihenfolge \(1\)/)).toBeTruthy()
    expect(plus()).toHaveLength(2)
    expect(screen.queryByRole('button', { name: /Zur Route hinzufügen: Reeperbahn/i })).toBeNull()
  })

  it('ein entfernter Ort wird wieder angeboten', async () => {
    const nutzer = userEvent.setup()
    zeigen()
    await nutzer.click(screen.getByRole('button', { name: /Neue Route/i }))
    await nutzer.click(screen.getByRole('button', { name: /Zur Route hinzufügen: Reeperbahn/i }))
    await nutzer.click(screen.getByRole('button', { name: /Aus der Route entfernen: Reeperbahn/i }))

    expect(screen.getByText(/Routen-Reihenfolge \(0\)/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /Zur Route hinzufügen: Reeperbahn/i })).toBeTruthy()
  })

  it('mit Name und zwei Orten lässt sich speichern', async () => {
    const nutzer = userEvent.setup()
    routesService.create.mockResolvedValue({ data: { id: 42, name: 'Tag 1', place_ids: [1, 2] } })
    zeigen()
    await nutzer.click(screen.getByRole('button', { name: /Neue Route/i }))
    await nutzer.type(screen.getByPlaceholderText(/Stadttour/i), 'Tag 1')
    const plus = () => screen.getAllByRole('button', { name: /Zur Route hinzufügen/i })
    await nutzer.click(plus()[0])
    await nutzer.click(plus()[0])

    expect(screen.queryByText(/Zum Speichern fehlt noch/i)).toBeNull()
    expect(speicherknopf().disabled).toBe(false)

    await nutzer.click(speicherknopf())
    await waitFor(() => expect(routesService.create).toHaveBeenCalledTimes(1))

    const gesendet = routesService.create.mock.calls[0][0]
    expect(gesendet.name).toBe('Tag 1')
    expect(gesendet.trip_id).toBe(7)
    expect(gesendet.place_ids).toHaveLength(2)
  })

  it('ein Ort lässt sich wieder entfernen', async () => {
    const nutzer = userEvent.setup()
    zeigen()
    await nutzer.click(screen.getByRole('button', { name: /Neue Route/i }))
    await nutzer.click(screen.getAllByRole('button', { name: /Zur Route hinzufügen/i })[0])
    expect(screen.getByText(/Routen-Reihenfolge \(1\)/)).toBeTruthy()

    await nutzer.click(screen.getByRole('button', { name: /Aus der Route entfernen/i }))
    expect(screen.getByText(/Routen-Reihenfolge \(0\)/)).toBeTruthy()
  })

  it('Gegenkontrolle: ohne Orte wird NICHT gespeichert', async () => {
    const nutzer = userEvent.setup()
    zeigen()
    await nutzer.click(screen.getByRole('button', { name: /Neue Route/i }))
    await nutzer.type(screen.getByPlaceholderText(/Stadttour/i), 'Leer')
    await nutzer.click(speicherknopf())

    expect(routesService.create).not.toHaveBeenCalled()
  })
})
