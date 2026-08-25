import { useState } from 'react'
import { Globe, Lock, Copy, RefreshCw, Check } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { tripsService } from '@services/api'

/**
 * Owner control for public read-only diary sharing of a single trip.
 * Renders a toggle plus, when public, the shareable link with copy + regenerate.
 */
export default function SharePanel({ trip }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [copied, setCopied] = useState(false)

  const isPublic = !!trip?.is_public
  const shareUrl = trip?.share_token ? `${window.location.origin}/share/${trip.share_token}` : ''

  const mutation = useMutation({
    mutationFn: ({ is_public, regenerate }) =>
      tripsService.setPublish(trip.id, { is_public, regenerate }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trips'] }),
    onError: () => toast.error(t('common:error', 'Fehler')),
  })

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      toast.success(t('common:share.linkCopied'))
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error(t('common:share.copyFailed'))
    }
  }

  const regenerate = () =>
    mutation.mutate(
      { is_public: true, regenerate: true },
      { onSuccess: () => toast.success(t('common:share.linkCopied', t('common:share.regenerate'))) }
    )

  return (
    <div className="card">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          {isPublic ? (
            <Globe className="w-5 h-5 mt-0.5 text-primary-500 shrink-0" />
          ) : (
            <Lock className="w-5 h-5 mt-0.5 text-gray-400 shrink-0" />
          )}
          <div>
            <h3 className="font-semibold">{t('common:share.public.title')}</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {isPublic ? t('common:share.public.enabled') : t('common:share.public.disabled')}
            </p>
          </div>
        </div>

        {/* Toggle */}
        <button
          type="button"
          role="switch"
          aria-checked={isPublic}
          aria-label={t('common:share.public.toggle')}
          disabled={mutation.isPending}
          onClick={() => mutation.mutate({ is_public: !isPublic, regenerate: false })}
          className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${
            isPublic ? 'bg-primary-500' : 'bg-gray-300 dark:bg-gray-600'
          }`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
              isPublic ? 'translate-x-5' : 'translate-x-0.5'
            }`}
          />
        </button>
      </div>

      {isPublic && shareUrl && (
        <div className="mt-4 space-y-2">
          <label className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {t('common:share.public.linkLabel')}
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              readOnly
              value={shareUrl}
              onFocus={(e) => e.target.select()}
              className="flex-1 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-sm font-mono"
            />
            <button onClick={copyLink} className="btn btn-secondary shrink-0" type="button">
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              {t('common:share.copyLink')}
            </button>
          </div>
          <button
            onClick={regenerate}
            disabled={mutation.isPending}
            type="button"
            className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-primary-600 dark:hover:text-primary-400 disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4" />
            {t('common:share.public.regenerate')}
            <span className="text-gray-400">— {t('common:share.public.regenerateHint')}</span>
          </button>
        </div>
      )}

      {!isPublic && (
        <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
          {t('common:share.public.hint')}
        </p>
      )}
    </div>
  )
}
