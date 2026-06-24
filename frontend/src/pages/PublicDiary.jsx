import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { MapPin, Calendar, Star, Globe } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { publicService } from '@services/api'
import { getThumbUrl, getPhotoUrl, onThumbError } from '@/utils/images'
import Lightbox from '@components/Lightbox'

/**
 * Public, unauthenticated read-only view of a shared trip diary.
 * Mounted outside ProtectedRoute at /share/:token.
 */
export default function PublicDiary() {
  const { t, i18n } = useTranslation()
  const { token } = useParams()
  const [lightbox, setLightbox] = useState({ open: false, items: [], index: 0 })

  const { data, isLoading, error } = useQuery({
    queryKey: ['publicDiary', token],
    queryFn: async () => (await publicService.getDiary(token)).data,
    retry: false,
  })

  const fmtDate = (d) => (d ? new Date(d).toLocaleDateString(i18n.language) : '')
  const openLightbox = (items, index) => setLightbox({ open: true, items, index })
  const closeLightbox = () => setLightbox({ open: false, items: [], index: 0 })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">{t('common:share.public.loading')}</p>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
        <div className="text-center max-w-md">
          <Globe className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-700 dark:text-gray-300 font-medium">{t('common:share.public.notFound')}</p>
        </div>
      </div>
    )
  }

  const dateRange = [fmtDate(data.start_date), fmtDate(data.end_date)].filter(Boolean).join(' – ')

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="relative">
        {data.cover_image && (
          <img
            src={getPhotoUrl(data.cover_image)}
            alt={data.title}
            className="w-full h-56 md:h-72 object-cover"
          />
        )}
        <div className={`max-w-3xl mx-auto px-4 ${data.cover_image ? '-mt-16 relative' : 'pt-10'}`}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6">
            <h1 className="text-3xl font-bold mb-1">{data.title}</h1>
            <div className="flex flex-wrap gap-4 text-gray-600 dark:text-gray-400 text-sm">
              <span className="inline-flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {data.destination}
              </span>
              {dateRange && (
                <span className="inline-flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {dateRange}
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Entries */}
      <main className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        {data.entries.length === 0 && (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            {t('common:share.public.empty')}
          </div>
        )}

        {data.entries.map((entry, idx) => (
          <article key={idx} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
            <div className="flex items-center justify-between gap-3 mb-2">
              <h2 className="text-xl font-semibold">{entry.title}</h2>
              {entry.rating ? (
                <span className="inline-flex items-center gap-0.5 text-amber-500 shrink-0">
                  {Array.from({ length: entry.rating }).map((_, i) => (
                    <Star key={i} className="w-4 h-4 fill-current" />
                  ))}
                </span>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400 mb-3">
              {entry.entry_date && (
                <span className="inline-flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  {fmtDate(entry.entry_date)}
                </span>
              )}
              {entry.location_name && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5" />
                  {entry.location_name}
                </span>
              )}
            </div>

            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{entry.content}</p>

            {entry.media && entry.media.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-4">
                {entry.media.map((m, i) => (
                  <img
                    key={m.id}
                    src={getThumbUrl(m.url)}
                    onError={onThumbError(m.url)}
                    loading="lazy"
                    alt={m.caption || `Photo ${i + 1}`}
                    title={m.caption || undefined}
                    onClick={() => openLightbox(entry.media, i)}
                    className="w-24 h-24 object-cover rounded-lg cursor-pointer hover:opacity-80 transition-opacity"
                  />
                ))}
              </div>
            )}
          </article>
        ))}
      </main>

      <footer className="text-center py-8 text-sm text-gray-400">
        {t('common:share.public.pageFooter')}
      </footer>

      <Lightbox
        open={lightbox.open}
        items={lightbox.items}
        initialIndex={lightbox.index}
        onClose={closeLightbox}
        readOnly
      />
    </div>
  )
}
