import { TimelineDay } from 'travelmind-frontend'

const ort = (id: number, name: string, kategorie: string, order: number, notes?: string) => ({
  id,
  place_id: id,
  place_name: name,
  place_category: kategorie,
  place_latitude: 53.55,
  place_longitude: 9.99,
  order,
  notes,
})

const tag = {
  day_date: '2026-09-02',
  total_duration_minutes: 320,
  entries: [
    ort(1, 'Speicherstadt', 'attraction', 0, 'Früh hin, dann ist das Licht besser.'),
    ort(2, 'Miniatur Wunderland', 'attraction', 1),
    ort(3, 'Restaurant Porto', 'restaurant', 2),
  ],
}

/** Ausgeklappt: der Zustand, in dem man den Tag plant. */
export const Ausgeklappt = () => (
  <TimelineDay day={tag} isExpanded onToggleExpand={() => {}} onReorder={() => {}} onDeleteEntry={() => {}} onOptimize={() => {}} />
)

/** Zugeklappt: die Übersicht über mehrere Tage. */
export const Zugeklappt = () => (
  <TimelineDay day={tag} isExpanded={false} onToggleExpand={() => {}} />
)

/** Ein Tag mit nur einem Ort — Optimieren ergibt hier nichts. */
export const EinOrt = () => (
  <TimelineDay
    day={{ day_date: '2026-09-05', entries: [ort(9, 'Elbstrand', 'beach', 0)] }}
    isExpanded
    onToggleExpand={() => {}}
  />
)
