/**
 * Wächter für Barrierefreiheit (Roadmap 5.5).
 *
 * Warum das hier nicht bloß Pflichtübung ist: bei der Handy-Messung am
 * 2026-08-25 stellte sich heraus, dass drei Knöpfe der Kopfzeile von
 * Vorlesesoftware nur als „Schaltfläche" angesagt werden — darunter der
 * einzige Weg zur Navigation und zum Abmelden. Aufgefallen ist das
 * zufällig. Diese Suite sucht danach systematisch.
 *
 * Geprüft werden die STRUKTURELLEN Regeln, die in jsdom belastbar sind:
 * Beschriftungen, Rollen, Alternativtexte, Formularfelder. Kontraste prüft
 * `design-tokens.test.js` rechnerisch — in jsdom gibt es kein Layout, ein
 * Kontrastbefund von dort wäre ein Ersatzsignal.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import axe from 'axe-core'
import { I18nextProvider } from 'react-i18next'
import i18n from '../i18n'

import ColorPicker from '@components/ColorPicker'
import IconSelector from '@components/IconSelector'
import OfflineIndicator from '@components/OfflineIndicator'
import ErrorBoundary from '@components/ErrorBoundary'

// Nur die Regeln, die ohne Layout ein echtes Urteil erlauben.
const REGELN = {
  runOnly: {
    type: 'rule',
    values: [
      'button-name',
      'link-name',
      'image-alt',
      'input-image-alt',
      'label',
      'aria-valid-attr',
      'aria-valid-attr-value',
      'aria-required-attr',
      'aria-roles',
      'duplicate-id-aria',
      'select-name',
      'form-field-multiple-labels',
    ],
  },
}

async function pruefe(ui) {
  const { container } = render(<I18nextProvider i18n={i18n}>{ui}</I18nextProvider>)
  const ergebnis = await axe.run(container, REGELN)
  return ergebnis.violations.map((v) => ({
    regel: v.id,
    wirkung: v.impact,
    stellen: v.nodes.map((n) => n.html.slice(0, 90)),
  }))
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Barrierefreiheit: der Prüfer selbst', () => {
  it('Positivkontrolle: ein Knopf ohne Namen wird gefunden', async () => {
    const verstoesse = await pruefe(
      <button type="button">
        <svg aria-hidden="true" />
      </button>
    )
    expect(verstoesse.map((v) => v.regel)).toContain('button-name')
  })

  it('Positivkontrolle: ein Bild ohne Alternativtext wird gefunden', async () => {
    const verstoesse = await pruefe(<img src="/x.jpg" />)
    expect(verstoesse.map((v) => v.regel)).toContain('image-alt')
  })

  it('Gegenkontrolle: ein beschrifteter Knopf löst NICHT aus', async () => {
    const verstoesse = await pruefe(
      <button type="button" aria-label="Menü öffnen">
        <svg aria-hidden="true" />
      </button>
    )
    expect(verstoesse).toEqual([])
  })
})

describe('Barrierefreiheit: Komponenten', () => {
  it('ColorPicker', async () => {
    expect(
      await pruefe(<ColorPicker value="#1F7A7D" onChange={() => {}} label="Linienfarbe" />)
    ).toEqual([])
  })

  it('IconSelector', async () => {
    expect(await pruefe(<IconSelector value="location" onChange={() => {}} />)).toEqual([])
  })

  it('OfflineIndicator', async () => {
    expect(await pruefe(<OfflineIndicator />)).toEqual([])
  })

  it('ErrorBoundary mit Inhalt', async () => {
    expect(
      await pruefe(
        <ErrorBoundary>
          <button type="button">Weiter</button>
        </ErrorBoundary>
      )
    ).toEqual([])
  })
})
