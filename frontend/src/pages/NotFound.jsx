import { Link } from 'react-router-dom'
import { Home, MapPin } from 'lucide-react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

export default function NotFound() {
  const { t } = useTranslation()
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="text-center"
      >
        <div className="mb-8">
          <motion.div
            animate={{
              y: [0, -20, 0],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className="inline-block"
          >
            <MapPin className="w-24 h-24 text-gray-300 dark:text-gray-700" />
          </motion.div>
        </div>

        <h1 className="text-6xl font-bold mb-4 text-gradient">404</h1>
        <h2 className="text-2xl font-semibold mb-4">{t('notFound:title')}</h2>
        <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md">
          {t('notFound:subtitle')} {t('notFound:description')}
        </p>

        <div className="flex gap-4 justify-center">
          <Link to="/" className="btn btn-primary">
            <Home className="w-5 h-5" />
            {t('notFound:backHome')}
          </Link>
          <Link to="/trips" className="btn btn-outline">
            <MapPin className="w-5 h-5" />
            {t('notFound:toTrips')}
          </Link>
        </div>
      </motion.div>
    </div>
  )
}
