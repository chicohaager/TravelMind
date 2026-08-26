/**
 * Die Oberfläche des TravelMind-Design-Systems.
 *
 * Angelegt am 2026-08-25 für den Sync nach claude.ai/design. TravelMind ist
 * eine Anwendung, keine Komponentenbibliothek — es gab bis dahin keinen
 * Einstiegspunkt, der sagt, WAS das Design-System nach außen anbietet. Diese
 * Datei ist genau das: eine ausdrückliche Liste statt einer geratenen.
 *
 * Sie wird von der Anwendung selbst NICHT importiert (Vite lädt jede
 * Komponente einzeln, damit das Code-Splitting erhalten bleibt) — sie ist die
 * Quelle für den Konverter und zugleich die einzige Stelle, an der man
 * nachlesen kann, aus welchen Bauteilen diese Oberfläche besteht.
 *
 * Ein Test hält fest, dass sie vollständig ist: jede Komponente unter
 * src/components/ muss hier stehen.
 */

export { default as AddToTimelineModal } from './components/AddToTimelineModal'
export { default as AudioRecorder } from './components/AudioRecorder'
export { default as BudgetView } from './components/BudgetView'
export { default as ColorPicker } from './components/ColorPicker'
export { default as DiaryEntry } from './components/DiaryEntry'
export { default as DiaryModal } from './components/DiaryModal'
export { default as ErrorBoundary } from './components/ErrorBoundary'
export { default as ExpenseCard } from './components/ExpenseCard'
export { default as ExpenseModal } from './components/ExpenseModal'
export { default as GlobalSearch } from './components/GlobalSearch'
export { default as IconSelector } from './components/IconSelector'
export { default as ImportFromGuideModal } from './components/ImportFromGuideModal'
export { default as InteractiveMap } from './components/InteractiveMap'
export { default as LanguageSwitcher } from './components/LanguageSwitcher'
export { default as Layout } from './components/layout/Layout'
export { default as Lightbox } from './components/Lightbox'
export { default as NativeCamera } from './components/NativeCamera'
export { default as Navbar } from './components/layout/Navbar'
export { default as NotificationBell } from './components/NotificationBell'
export { default as OfflineIndicator } from './components/OfflineIndicator'
export { default as ParticipantsManager } from './components/ParticipantsManager'
export { default as PlaceCard } from './components/PlaceCard'
export { default as PlaceDetailModal } from './components/PlaceDetailModal'
export { default as PlaceListsSection } from './components/PlaceListsSection'
export { default as PlaceModal } from './components/PlaceModal'
export { default as ProtectedRoute } from './components/ProtectedRoute'
export { default as RecommendationsView } from './components/RecommendationsView'
export { default as RouteBuilder } from './components/RouteBuilder'
export { default as ShareButton } from './components/ShareButton'
export { default as SharePanel } from './components/SharePanel'
export { default as Sidebar } from './components/layout/Sidebar'
export { default as TimelineDay } from './components/TimelineDay'
export { default as TimelineEntryCard } from './components/TimelineEntryCard'
export { default as TimelineView } from './components/TimelineView'
export { default as TripModal } from './components/TripModal'

// Der Kontext, in dem die Vorschaukarten rendern (siehe cfg.provider).
export { default as DesignSystemProvider } from './design-system-provider'
