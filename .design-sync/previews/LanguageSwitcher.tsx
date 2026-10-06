import { LanguageSwitcher } from 'travelmind-frontend'

/**
 * Der Umschalter zeigt die aktive Sprache als Flagge; die Liste klappt beim
 * Klick auf. Statisch ist nur der geschlossene Zustand darstellbar — der
 * offene braucht ein Klickereignis und wäre hier eine Attrappe.
 */
export const Standard = () => <LanguageSwitcher />
