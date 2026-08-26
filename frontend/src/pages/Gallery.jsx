import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { GalleryThumbnails, ChevronDown, ChevronRight, MapPin } from 'lucide-react'
import { motion } from 'framer-motion'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { mediaService } from '@services/api'
import { getThumbUrl, onThumbError } from '@/utils/images'
import Lightbox from '@components/Lightbox'

/**
 * Cross-trip photo gallery: every photo the user can see, grouped by trip and
 * sorted newest-capture-first. Backed by GET /media/gallery.
 */
export default function Gallery() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [collapsed, setCollapsed] = useState(() => new Set())
  const [lightbox, setLightbox] = useState({ open: false, items: [], index: 0 })

  const {
    data: media = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['galleryMedia'],
    queryFn: async () => {
      const response = await mediaService.getGallery()
      return response.data
    },
  })

  // Group media by trip, preserving the backend's order (newest photo first),
  // so trips with the most recent photos appear at the top.
  const groups = useMemo(() => {
    const byTrip = new Map()
    for (const m of media) {
      if (!byTrip.has(m.trip_id)) {
        byTrip.set(m.trip_id, { tripId: m.trip_id, tripTitle: m.trip_title, items: [] })
      }
      byTrip.get(m.trip_id).items.push(m)
    }
    return Array.from(byTrip.values())
  }, [media])

  const toggleTrip = (tripId) => {
    setCollapsed((prev) => {
      const next = new Set(prev)
      next.has(tripId) ? next.delete(tripId) : next.add(tripId)
      return next
    })
  }

  const openLightbox = (items, index) => setLightbox({ open: true, items, index })
  const closeLightbox = () => setLightbox({ open: false, items: [], index: 0 })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
          <GalleryThumbnails className="w-9 h-9 text-primary-500" />
          {t('gallery:title')}
        </h1>
        <p className="text-gray-600 dark:text-gray-400">{t('gallery:subtitle')}</p>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="card text-center py-16">
          <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">{t('gallery:loading')}</p>
        </div>
      )}

      {/* Error State */}
      {!isLoading && error && (
        <div className="card text-center py-16">
          <p className="text-red-600 dark:text-red-400">{t('gallery:error')}</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && groups.length === 0 && (
        <div className="card text-center py-16">
          <GalleryThumbnails className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400 font-medium">{t('gallery:empty')}</p>
          <p className="text-gray-500 dark:text-gray-500 text-sm mt-1">{t('gallery:emptyHint')}</p>
        </div>
      )}

      {/* Trip groups */}
      {!isLoading &&
        !error &&
        groups.map((group) => {
          const isCollapsed = collapsed.has(group.tripId)
          return (
            <motion.section
              key={group.tripId}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="card"
            >
              <div className="flex items-center justify-between mb-4">
                <button
                  onClick={() => toggleTrip(group.tripId)}
                  className="flex items-center gap-2 text-left group"
                >
                  {isCollapsed ? (
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  )}
                  <h2 className="text-xl font-semibold group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                    {group.tripTitle}
                  </h2>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    ({t('gallery:photoCount', { count: group.items.length })})
                  </span>
                </button>
                <Link
                  to={`/trips/${group.tripId}`}
                  aria-label={group.tripTitle}
                  title={group.tripTitle}
                  className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 flex items-center gap-1 shrink-0"
                >
                  <MapPin className="w-4 h-4" />
                </Link>
              </div>

              {!isCollapsed && (
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
                  {group.items.map((m, i) => (
                    <img
                      key={m.id}
                      src={getThumbUrl(m.url)}
                      onError={onThumbError(m.url)}
                      loading="lazy"
                      alt={m.caption || `Photo ${i + 1}`}
                      title={m.caption || undefined}
                      onClick={() => openLightbox(group.items, i)}
                      className="aspect-square w-full object-cover rounded-lg cursor-pointer hover:opacity-80 transition-opacity"
                    />
                  ))}
                </div>
              )}
            </motion.section>
          )
        })}

      {/* Lightbox */}
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
