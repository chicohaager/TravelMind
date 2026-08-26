import { ExpenseCard } from 'travelmind-frontend'

const teilnehmer = [
  { id: 1, name: 'Anita' },
  { id: 2, name: 'Bert' },
  { id: 3, name: 'Cem' },
]

const abendessen = {
  id: 1,
  title: 'Abendessen im Time Out Market',
  amount: 47.8,
  currency: 'EUR',
  category: 'food',
  date: '2026-09-02',
  paid_by: 1,
  paid_by_name: 'Anita',
}

export const Standard = () => <ExpenseCard expense={abendessen} participants={teilnehmer} />

/** Geteilt: der eigentliche Zweck — wer schuldet wem was. */
export const Geteilt = () => (
  <ExpenseCard
    expense={{
      ...abendessen,
      title: 'Hotel Alfama, 2 Nächte',
      amount: 240,
      category: 'accommodation',
      splits: [
        { participant_id: 1, amount: 80 },
        { participant_id: 2, amount: 80 },
        { participant_id: 3, amount: 80 },
      ],
    }}
    participants={teilnehmer}
  />
)

/** Mit Notiz und ohne Zahler — der Fall bei Alleinreisenden. */
export const OhneZahler = () => (
  <ExpenseCard
    expense={{
      id: 3,
      title: 'Tram 28, Tageskarte',
      amount: 6.8,
      currency: 'EUR',
      category: 'transport',
      date: '2026-09-03',
      notes: 'Am Automaten günstiger als beim Fahrer.',
    }}
    participants={[]}
  />
)

export const MitAktionen = () => (
  <ExpenseCard expense={abendessen} participants={teilnehmer} onEdit={() => {}} onDelete={() => {}} />
)
