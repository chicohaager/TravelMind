/**
 * Shared helpers for rendering uploaded images.
 *
 * The backend stores a web-sized WebP plus a `<stem>_thumb.webp` thumbnail
 * (see backend/utils/images.py). Galleries should load the thumbnail and only
 * fetch the full image in a lightbox/detail view.
 */

const API_ORIGIN = import.meta.env.VITE_API_URL || ''

/** Resolve a stored photo path to an absolute URL. */
export function getPhotoUrl(photo) {
  if (!photo) return ''
  return photo.startsWith('http') ? photo : `${API_ORIGIN}${photo}`
}

/**
 * Resolve the thumbnail URL for a stored photo.
 *
 * New uploads are `<stem>.webp` with a sibling `<stem>_thumb.webp`. For those we
 * return the thumbnail. Anything else (legacy jpg/png, external URLs) falls back
 * to the full image so nothing breaks. Pair with `onThumbError` for a runtime
 * fallback if a thumbnail is missing on disk.
 */
export function getThumbUrl(photo) {
  if (!photo) return ''
  if (photo.startsWith('http')) return photo
  const thumb = photo.endsWith('.webp')
    ? photo.replace(/\.webp$/, '_thumb.webp')
    : photo
  return `${API_ORIGIN}${thumb}`
}

/**
 * onError handler that swaps a failed thumbnail for the full image exactly once,
 * so a missing thumbnail degrades gracefully instead of showing a broken image.
 */
export function onThumbError(photo) {
  return (e) => {
    const full = getPhotoUrl(photo)
    if (e.target.src !== full) {
      e.target.src = full
    }
  }
}
