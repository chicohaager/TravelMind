import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, X, BookOpen, MapPin, Map as MapIcon, Image as ImageIcon } from 'lucide-react'
import { searchService } from '@services/api'
import { useTranslation } from 'react-i18next'

// Per-type icon + target route (everything navigates within a trip).
const TYPE_META = {
  trip: { icon: MapIcon, route: (h) => `/trips/${h.trip_id}` },
  diary: { icon: BookOpen, route: (h) => `/diary/${h.trip_id}` },
  place: { icon: MapPin, route: (h) => `/trips/${h.trip_id}` },
  media: { icon: ImageIcon, route: (h) => `/diary/${h.trip_id}` },
}

export default function GlobalSearch() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [debounced, setDebounced] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  // Debounce the query so we don't hit the API on every keystroke.
  useEffect(() => {
    const id = setTimeout(() => setDebounced(q.trim()), 250)
    return () => clearTimeout(id)
  }, [q])

  // Close the dropdown on outside click.
  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const { data, isFetching } = useQuery({
    queryKey: ['globalSearch', debounced],
    queryFn: async () => (await searchService.search(debounced)).data,
    enabled: debounced.length >= 2,
    staleTime: 30000,
  })

  const results = data?.results || []

  const go = (hit) => {
    const route = TYPE_META[hit.type]?.route(hit)
    setOpen(false)
    setQ('')
    if (route) navigate(route)
  }

  return (
    <div className="relative" ref={ref}>
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false) }}
          placeholder={t('common:searchPlaceholder', 'Reisen, Einträge, Orte…')}
          aria-label={t('common:search', 'Suchen')}
          className="w-36 sm:w-52 md:w-64 pl-8 pr-7 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-700 border border-transparent focus:border-primary-500 focus:bg-white dark:focus:bg-gray-800 focus:outline-none transition-colors"
        />
        {q && (
          <button
            type="button"
            onClick={() => { setQ(''); setOpen(false) }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            aria-label={t('common:clear', 'Löschen')}
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {open && debounced.length >= 2 && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-auto bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50">
          {isFetching && (
            <div className="px-4 py-3 text-sm text-gray-500">{t('common:loading', 'Lädt…')}</div>
          )}
          {!isFetching && results.length === 0 && (
            <div className="px-4 py-3 text-sm text-gray-500">{t('common:noResults', 'Keine Treffer')}</div>
          )}
          {results.map((hit) => {
            const Icon = TYPE_META[hit.type]?.icon || Search
            return (
              <button
                key={`${hit.type}-${hit.id}`}
                type="button"
                onClick={() => go(hit)}
                className="w-full text-left px-3 py-2 flex gap-2 items-start hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <Icon className="w-4 h-4 mt-0.5 text-gray-400 shrink-0" />
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{hit.title || '—'}</div>
                  {hit.snippet && (
                    <div className="text-xs text-gray-500 dark:text-gray-400 truncate">{hit.snippet}</div>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
