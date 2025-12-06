import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { formatDate } from '@/utils/format'

export default function Home() {
  const { t } = useTranslation()

  const recentTrips = [
    {
      id: 1,
      title: 'Sommer in Portugal',
      destination: 'Lissabon',
      image: 'https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=800&auto=format&fit=crop',
      startDate: '2024-07-15',
      duration: 7
    },
    {
      id: 2,
      title: 'Herbst in Japan',
      destination: 'Kyoto',
      image: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&auto=format&fit=crop',
      startDate: '2024-10-01',
      duration: 10
    }
  ]

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center py-12"
      >
        <h1 className="text-5xl md:text-6xl font-bold mb-6">
          <span className="text-gradient">{t('home:yourNextTrip')}</span>
          <br />
          <span className="text-gray-900 dark:text-white">{t('home:isWaiting')}</span>
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-400 mb-8 max-w-2xl mx-auto">
          {t('home:planExploreDocument')}
          {' '}
          {t('home:selfHostedPrivacy')}
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            to="/trips"
            className="btn btn-primary text-lg px-8 py-3"
          >
            {t('home:planNewTrip')}
          </Link>
          <Link
            to="/ai"
            className="btn btn-outline text-lg px-8 py-3"
          >
            <Sparkles className="w-5 h-5" />
            {t('home:aiAssistant')}
          </Link>
        </div>
      </motion.section>


      {/* Recent Trips */}
      <section>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-3xl font-bold">{t('home:recentTrips')}</h2>
          <Link
            to="/trips"
            className="text-primary-500 hover:text-primary-600 font-medium"
          >
            {t('home:showAll')} →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {recentTrips.map((trip) => (
            <motion.div
              key={trip.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
              className="card p-0 overflow-hidden group cursor-pointer"
            >
              <div className="relative h-48 overflow-hidden">
                <img
                  src={trip.image}
                  alt={trip.title}
                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                <div className="absolute bottom-4 left-4 text-white">
                  <h3 className="text-2xl font-bold">{trip.title}</h3>
                  <p className="text-sm opacity-90">{trip.destination}</p>
                </div>
              </div>
              <div className="p-4 flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {formatDate(trip.startDate, 'long')}
                </span>
                <span className="badge badge-primary">{trip.duration} {t('common:days')}</span>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.5 }}
        className="card bg-gradient-to-br from-primary-500 to-secondary-500 text-white text-center py-12"
      >
        <h2 className="text-3xl font-bold mb-4">
          {t('home:readyForNextAdventure')}
        </h2>
        <p className="text-xl mb-6 opacity-90">
          {t('home:letAiHelp')}
        </p>
        <Link
          to="/ai"
          className="inline-flex items-center gap-2 bg-white text-primary-500 px-8 py-3 rounded-lg font-medium hover:shadow-lg transition-shadow"
        >
          <Sparkles className="w-5 h-5" />
          {t('home:startWithAi')}
        </Link>
      </motion.section>
    </div>
  )
}
