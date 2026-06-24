import { useState, useEffect, useCallback } from 'react'
import { X, ChevronLeft, ChevronRight } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { mediaService } from '@services/api'
import { getPhotoUrl, getThumbUrl, onThumbError } from '@/utils/images'

/**
 * Full-screen photo lightbox with keyboard navigation, a thumbnail strip and
 * inline caption editing. Shared by the diary and the cross-trip gallery.
 *
 * Props:
 *   open          - whether the lightbox is visible
 *   items         - array of media objects ({ id, url, caption })
 *   initialIndex  - index of the photo to show first
 *   onClose       - called when the lightbox should close
 *   onCaptionSaved- optional callback after a caption is saved (e.g. to
 *                   invalidate the caller's queries)
 */
export default function Lightbox({ open, items = [], initialIndex = 0, onClose, onCaptionSaved }) {
  const { t } = useTranslation()
  const [index, setIndex] = useState(initialIndex)
  const [captionDraft, setCaptionDraft] = useState('')

  // Sync internal state whenever the lightbox is (re)opened on a given photo.
  useEffect(() => {
    if (open) {
      setIndex(initialIndex)
      setCaptionDraft(items[initialIndex]?.caption || '')
    }
  }, [open, initialIndex]) // eslint-disable-line react-hooks/exhaustive-deps

  const goTo = useCallback((i) => {
    setIndex(i)
    setCaptionDraft(items[i]?.caption || '')
  }, [items])

  const nextPhoto = useCallback(() => {
    goTo((index + 1) % items.length)
  }, [goTo, index, items.length])

  const prevPhoto = useCallback(() => {
    goTo((index - 1 + items.length) % items.length)
  }, [goTo, index, items.length])

  const saveCaptionMutation = useMutation({
    mutationFn: ({ mediaId, caption }) => mediaService.updateCaption(mediaId, caption),
    onSuccess: () => {
      onCaptionSaved?.()
      toast.success(t('diary:captionSaved', 'Bildunterschrift gespeichert'))
    },
    onError: () => toast.error(t('common:error', 'Fehler')),
  })

  const saveCaption = () => {
    const current = items[index]
    if (current?.id) saveCaptionMutation.mutate({ mediaId: current.id, caption: captionDraft })
  }

  // Keyboard navigation while the lightbox is open.
  const handleKeyDown = useCallback((e) => {
    if (!open) return
    if (e.key === 'Escape') onClose?.()
    if (e.key === 'ArrowLeft') prevPhoto()
    if (e.key === 'ArrowRight') nextPhoto()
  }, [open, onClose, prevPhoto, nextPhoto])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  if (!open) return null

  const current = items[index]

  return (
    <div
      className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
      onClick={onClose}
    >
      {/* Close Button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors z-10"
      >
        <X className="w-8 h-8" />
      </button>

      {/* Photo Counter */}
      <div className="absolute top-4 left-4 text-white text-sm">
        {index + 1} / {items.length}
      </div>

      {/* Previous Button */}
      {items.length > 1 && (
        <button
          onClick={(e) => { e.stopPropagation(); prevPhoto(); }}
          className="absolute left-4 text-white hover:text-gray-300 transition-colors p-2 rounded-full bg-black/50 hover:bg-black/70"
        >
          <ChevronLeft className="w-8 h-8" />
        </button>
      )}

      {/* Image */}
      <img
        src={getPhotoUrl(current?.url)}
        alt={current?.caption || `Photo ${index + 1}`}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[80vh] max-w-[90vw] object-contain"
      />

      {/* Next Button */}
      {items.length > 1 && (
        <button
          onClick={(e) => { e.stopPropagation(); nextPhoto(); }}
          className="absolute right-4 text-white hover:text-gray-300 transition-colors p-2 rounded-full bg-black/50 hover:bg-black/70"
        >
          <ChevronRight className="w-8 h-8" />
        </button>
      )}

      {/* Caption editor + thumbnails */}
      <div
        className="absolute bottom-4 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3 w-[90vw] max-w-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex w-full gap-2">
          <input
            type="text"
            value={captionDraft}
            onChange={(e) => setCaptionDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') saveCaption() }}
            placeholder={t('diary:captionPlaceholder', 'Bildunterschrift hinzufügen…')}
            maxLength={500}
            className="flex-1 px-3 py-2 rounded-lg bg-white/10 text-white placeholder-white/50 border border-white/20 focus:outline-none focus:border-white/50 text-sm"
          />
          <button
            onClick={saveCaption}
            disabled={saveCaptionMutation.isPending || captionDraft === (current?.caption || '')}
            className="px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {t('common:save', 'Speichern')}
          </button>
        </div>

        {items.length > 1 && (
          <div className="flex gap-2">
            {items.map((m, i) => (
              <img
                key={m.id ?? i}
                src={getThumbUrl(m.url)}
                onError={onThumbError(m.url)}
                loading="lazy"
                alt={m.caption || `Thumbnail ${i + 1}`}
                onClick={() => goTo(i)}
                className={`w-12 h-12 object-cover rounded cursor-pointer transition-all ${
                  i === index ? 'ring-2 ring-white opacity-100' : 'opacity-50 hover:opacity-75'
                }`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
