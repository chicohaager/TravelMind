import { BarChart3, MapPin, BookOpen, Image, CalendarDays, Wallet } from 'lucide-react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { analyticsService } from '@services/api'

/** Horizontal bar list scaled to the largest value. Pure CSS, no chart lib. */
function BarList({ title, items, format = (v) => v }) {
  if (!items || items.length === 0) return null
  const max = Math.max(...items.map((i) => i.value), 1)
  return (
    <div className="card">
      <h2 className="text-lg font-semibold mb-4">{title}</h2>
      <div className="space-y-3">
        {items.map((it, idx) => (
          <div key={idx}>
            <div className="flex justify-between text-sm mb-1">
              <span className="truncate pr-2">{it.label}</span>
              <span className="text-gray-500 dark:text-gray-400 shrink-0">{format(it.value)}</span>
            </div>
            <div className="h-2.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-primary-500"
                initial={{ width: 0 }}
                animate={{ width: `${(it.value / max) * 100}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="card flex items-center gap-4">
      <div className="w-11 h-11 rounded-xl bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center shrink-0">
        <Icon className="w-6 h-6 text-primary-500" />
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-bold leading-tight">{value}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{label}</p>
      </div>
    </div>
  )
}

export default function Analytics() {
  const { t, i18n } = useTranslation()

  const { data, isLoading, error } = useQuery({
    queryKey: ['analyticsSummary'],
    queryFn: async () => (await analyticsService.summary()).data,
  })

  const money = (v, currency = data?.primary_currency || 'EUR') => {
    try {
      return new Intl.NumberFormat(i18n.language, { style: 'currency', currency }).format(v)
    } catch {
      return `${v} ${currency}`
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
          <BarChart3 className="w-9 h-9 text-primary-500" />
          {t('analytics:title')}
        </h1>
        <p className="text-gray-600 dark:text-gray-400">{t('analytics:subtitle')}</p>
      </div>

      {isLoading && (
        <div className="card text-center py-16">
          <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">{t('analytics:loading')}</p>
        </div>
      )}

      {!isLoading && error && (
        <div className="card text-center py-16">
          <p className="text-red-600 dark:text-red-400">{t('analytics:error')}</p>
        </div>
      )}

      {!isLoading && !error && data && data.trips === 0 && (
        <div className="card text-center py-16">
          <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">{t('analytics:empty')}</p>
        </div>
      )}

      {!isLoading && !error && data && data.trips > 0 && (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <StatCard icon={MapPin} label={t('analytics:trips')} value={data.trips} />
            <StatCard icon={BookOpen} label={t('analytics:entries')} value={data.diary_entries} />
            <StatCard icon={Image} label={t('analytics:photos')} value={data.photos} />
            <StatCard icon={CalendarDays} label={t('analytics:travelDays')} value={data.travel_days} />
            <StatCard icon={Wallet} label={t('analytics:totalSpend')} value={money(data.total_spend)} />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <BarList
              title={t('analytics:spendByCategory')}
              items={data.spend_by_category.map((c) => ({ label: c.category, value: c.amount }))}
              format={(v) => money(v)}
            />
            {Object.keys(data.spend_by_currency || {}).length > 1 && (
              <BarList
                title={t('analytics:spendByCurrency')}
                items={Object.entries(data.spend_by_currency).map(([cur, amt]) => ({ label: cur, value: amt }))}
                format={(v) => v.toFixed(2)}
              />
            )}
            <BarList
              title={t('analytics:photosByTrip')}
              items={data.photos_by_trip.map((x) => ({ label: x.label, value: x.count }))}
            />
            <BarList
              title={t('analytics:entriesByTrip')}
              items={data.entries_by_trip.map((x) => ({ label: x.label, value: x.count }))}
            />
            {data.trips_by_year.length > 1 && (
              <BarList
                title={t('analytics:tripsByYear')}
                items={data.trips_by_year.map((x) => ({ label: x.label, value: x.count }))}
              />
            )}
          </div>
        </>
      )}
    </div>
  )
}
