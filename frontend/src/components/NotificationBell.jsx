import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Check } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { notificationsService } from '@services/api'

/**
 * Navbar bell showing the unread-notification count, with a dropdown that lists
 * notifications, marks them read on click and navigates to the related trip.
 */
export default function NotificationBell() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const { data: unread } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: async () => (await notificationsService.unreadCount()).data.count,
    refetchInterval: 60000,
    staleTime: 30000,
  })

  const { data: items = [] } = useQuery({
    queryKey: ['notifications', 'list'],
    queryFn: async () => (await notificationsService.list()).data,
    enabled: open,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications', 'unread-count'] })
    queryClient.invalidateQueries({ queryKey: ['notifications', 'list'] })
  }

  const markRead = useMutation({
    mutationFn: (id) => notificationsService.markRead(id),
    onSuccess: invalidate,
  })
  const markAllRead = useMutation({
    mutationFn: () => notificationsService.markAllRead(),
    onSuccess: invalidate,
  })

  useEffect(() => {
    const onDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  const onItemClick = (n) => {
    if (!n.is_read) markRead.mutate(n.id)
    setOpen(false)
    if (n.trip_id) navigate(`/diary/${n.trip_id}`)
  }

  const message = (n) =>
    t(`notifications:${n.type}`, { actor: n.actor_name || '', trip: n.trip_title || '' })

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        aria-label={t('notifications:title')}
      >
        <Bell className="w-5 h-5" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[11px] font-semibold flex items-center justify-center">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 z-50">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
            <span className="font-semibold">{t('notifications:title')}</span>
            {items.some((n) => !n.is_read) && (
              <button
                onClick={() => markAllRead.mutate()}
                className="inline-flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:underline"
              >
                <Check className="w-3.5 h-3.5" />
                {t('notifications:markAllRead')}
              </button>
            )}
          </div>

          {items.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
              {t('notifications:empty')}
            </p>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-700">
              {items.map((n) => (
                <li key={n.id}>
                  <button
                    onClick={() => onItemClick(n)}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                      n.is_read ? '' : 'bg-primary-50/50 dark:bg-primary-900/10'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {!n.is_read && (
                        <span className="mt-1.5 w-2 h-2 rounded-full bg-primary-500 shrink-0" />
                      )}
                      <div className="min-w-0">
                        <p className="text-sm text-gray-800 dark:text-gray-200">{message(n)}</p>
                        {n.created_at && (
                          <p className="text-xs text-gray-400 mt-0.5">
                            {new Date(n.created_at).toLocaleDateString(i18n.language)}
                          </p>
                        )}
                      </div>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
