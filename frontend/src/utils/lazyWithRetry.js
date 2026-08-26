import { lazy } from 'react'

/**
 * `React.lazy` with a one-shot recovery from stale chunk loads.
 *
 * After a new deployment, hashed chunk filenames change; a client still running
 * the old `index` may request a chunk that no longer exists and the dynamic
 * import rejects. We then reload the page once to fetch the fresh manifest.
 *
 * A sessionStorage flag prevents an infinite reload loop: if the import still
 * fails after a reload (a genuine error, not a stale chunk), we rethrow so the
 * surrounding ErrorBoundary can handle it.
 */
const RELOAD_FLAG = 'chunkReloaded'

export default function lazyWithRetry(importer) {
  return lazy(() =>
    importer()
      .then((module) => {
        sessionStorage.removeItem(RELOAD_FLAG)
        return module
      })
      .catch((error) => {
        if (!sessionStorage.getItem(RELOAD_FLAG)) {
          sessionStorage.setItem(RELOAD_FLAG, '1')
          window.location.reload()
          // Resolve never: the page is reloading.
          return new Promise(() => {})
        }
        throw error
      })
  )
}
