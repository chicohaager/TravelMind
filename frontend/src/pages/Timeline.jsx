import { useState, useMemo } from 'react'
import { CalendarClock } from 'lucide-react'
import { motion } from 'framer-motion'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { mediaService } from '@services/api'
import { getThumbUrl, onThumbError } from '@/utils/images'
import Lightbox from '@components/Lightbox'

/**
 * Cross-trip photo timeline: every photo the user can see, grouped by capture
 * month (taken_at, falling back to created_at), newest first. Reuses the gallery
 * endpoint's data.
 */
export default function Timeline() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const [lightbox, setLightbox] = useState({ open: false, items: [], index: 0 })

  const {
    data: media = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['galleryMedia'],
    queryFn: async () => (await mediaService.getGallery()).data,
  })

  // Group by year-month of the capture date (or upload date as fallback),
  // newest group first, newest photo first within a group.
  const groups = useMemo(() => {
    const withDate = media.map((m) => ({ m, date: m.taken_at || m.created_at || null }))
    withDate.sort((a, b) => {
      if (!a.date) return 1
      if (!b.date) return -1
      return new Date(b.date) - new Date(a.date)
    })
    const byMonth = new Map()
    for (const { m, date } of withDate) {
      const key = date ? `${new Date(date).getFullYear()}-${new Date(date).getMonth()}` : 'nodate'
      if (!byMonth.has(key)) {
        byMonth.set(key, {
          key,
          label: date
            ? new Date(date).toLocaleDateString(i18n.language, { year: 'numeric', month: 'long' })
            : t('gallery:noDate'),
          items: [],
        })
      }
      byMonth.get(key).items.push(m)
    }
    return Array.from(byMonth.values())
  }, [media, i18n.language, t])

  const openLightbox = (items, index) => setLightbox({ open: true, items, index })
  const closeLightbox = () => setLightbox({ open: false, items: [], index: 0 })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
          <CalendarClock className="w-9 h-9 text-primary-500" />
          {t('gallery:timelineTitle')}
        </h1>
        <p className="text-gray-600 dark:text-gray-400">{t('gallery:timelineSubtitle')}</p>
      </div>

      {isLoading && (
        <div className="card text-center py-16">
          <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">{t('gallery:loading')}</p>
        </div>
      )}

      {!isLoading && error && (
        <div className="card text-center py-16">
          <p className="text-red-600 dark:text-red-400">{t('gallery:error')}</p>
        </div>
      )}

      {!isLoading && !error && groups.length === 0 && (
        <div className="card text-center py-16">
          <CalendarClock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400 font-medium">{t('gallery:empty')}</p>
          <p className="text-gray-500 dark:text-gray-500 text-sm mt-1">{t('gallery:emptyHint')}</p>
        </div>
      )}

      {/* Month groups along a vertical timeline */}
      {!isLoading &&
        !error &&
        groups.map((group) => (
          <motion.section
            key={group.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative pl-6 border-l-2 border-primary-200 dark:border-primary-900"
          >
            <span className="absolute -left-[7px] top-1.5 w-3 h-3 rounded-full bg-primary-500" />
            <div className="flex items-baseline gap-2 mb-3">
              <h2 className="text-lg font-semibold capitalize">{group.label}</h2>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                ({t('gallery:photoCount', { count: group.items.length })})
              </span>
            </div>
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
              {group.items.map((m, i) => (
                <img
                  key={m.id}
                  src={getThumbUrl(m.url)}
                  onError={onThumbError(m.url)}
                  loading="lazy"
                  alt={m.caption || `Photo ${i + 1}`}
                  title={m.caption || m.trip_title || undefined}
                  onClick={() => openLightbox(group.items, i)}
                  className="aspect-square w-full object-cover rounded-lg cursor-pointer hover:opacity-80 transition-opacity"
                />
              ))}
            </div>
          </motion.section>
        ))}

      <Lightbox
        open={lightbox.open}
        items={lightbox.items}
        initialIndex={lightbox.index}
        onClose={closeLightbox}
        onCaptionSaved={() => queryClient.invalidateQueries({ queryKey: ['galleryMedia'] })}
      />
    </div>
  )
}
