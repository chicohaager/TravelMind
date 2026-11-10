import { ExpenseModal } from 'travelmind-frontend'

const teilnehmer = [
  { id: 1, name: 'Anita' },
  { id: 2, name: 'Bert' },
  { id: 3, name: 'Cem' },
]

/** Leeres Formular — der Zustand beim Erfassen einer neuen Ausgabe. */
export const Neu = () => (
  <ExpenseModal isOpen participants={teilnehmer} onClose={() => {}} onSubmit={() => {}} />
)

/** Mit vorbelegten Werten — der Bearbeiten-Fall. */
export const Bearbeiten = () => (
  <ExpenseModal
    isOpen
    participants={teilnehmer}
    initialData={{
      id: 1,
      title: 'Abendessen im Time Out Market',
      amount: 47.8,
      currency: 'EUR',
      category: 'food',
      date: '2026-09-02',
      paid_by: 1,
    }}
    onClose={() => {}}
    onSubmit={() => {}}
  />
)
