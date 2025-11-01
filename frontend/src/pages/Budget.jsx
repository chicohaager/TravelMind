import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  DollarSign, TrendingUp, TrendingDown, MapPin, Calendar,
  Loader, AlertCircle
} from 'lucide-react'
import { tripsService, budgetService } from '@/services/api'
import { format } from 'date-fns'
import { de } from 'date-fns/locale'
import { useTranslation } from 'react-i18next'

export default function Budget() {
  const { t } = useTranslation()
  // Fetch all trips
  const { data: trips = [], isLoading, error } = useQuery({
    queryKey: ['trips'],
    queryFn: async () => {
      const response = await tripsService.getAll()
      return response.data
    }
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">{t('budget.errorLoading')}</h2>
          <p className="text-gray-600 dark:text-gray-400">
            {t('budget.errorLoadingData')}
          </p>
        </div>
      </div>
    )
  }

  if (trips.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <DollarSign className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">{t('trips.noTrips')}</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {t('budget.createTripToManageExpenses')}
          </p>
          <Link
            to="/trips"
            className="btn-primary inline-flex items-center gap-2"
          >
            <MapPin className="w-5 h-5" />
            {t('trips.createTrip')}
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">{t('budget.budgetOverview')}</h1>
        <p className="text-gray-600 dark:text-gray-400">
          {t('budget.manageExpensesForTrips')}
        </p>
      </div>

      {/* Budget Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {trips.map((trip, index) => (
          <TripBudgetCard key={trip.id} trip={trip} index={index} />
        ))}
      </div>
    </div>
  )
}

function TripBudgetCard({ trip, index }) {
  const { t } = useTranslation()
  // Fetch budget summary for this trip
  const { data: summary } = useQuery({
    queryKey: ['budget-summary', trip.id],
    queryFn: async () => {
      const response = await budgetService.getSummary(trip.id)
      return response.data
    }
  })

  const budget = trip.budget || 0
  const spent = summary?.total_spent || 0
  const remaining = budget - spent
  const percentageSpent = budget > 0 ? (spent / budget) * 100 : 0
  const isOverBudget = spent > budget

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <Link
        to={`/trips/${trip.id}?tab=budget`}
        className="block h-full"
      >
        <div className="card h-full hover:shadow-xl transition-shadow duration-200 cursor-pointer">
          {/* Trip Header */}
          <div className="mb-4">
            <h3 className="text-xl font-bold mb-1 line-clamp-2">
              {trip.title}
            </h3>
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <MapPin className="w-4 h-4" />
              <span>{trip.destination}</span>
            </div>
            {trip.start_date && (
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 mt-1">
                <Calendar className="w-4 h-4" />
                <span>
                  {format(new Date(trip.start_date), 'PP', { locale: de })}
                </span>
              </div>
            )}
          </div>

          {/* Budget Summary */}
          <div className="space-y-4">
            {/* Progress Bar */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium">{t('budget.budgetUsage')}</span>
                <span className={`text-sm font-bold ${
                  isOverBudget ? 'text-red-600' : 'text-primary-600'
                }`}>
                  {percentageSpent.toFixed(0)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${
                    isOverBudget
                      ? 'bg-red-500'
                      : percentageSpent > 80
                      ? 'bg-yellow-500'
                      : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(percentageSpent, 100)}%` }}
                />
              </div>
            </div>

            {/* Budget Details */}
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                  {t('budget.title')}
                </div>
                <div className="font-bold text-sm">
                  {budget.toFixed(0)} {trip.currency || 'EUR'}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                  {t('budget.spent')}
                </div>
                <div className={`font-bold text-sm ${
                  isOverBudget ? 'text-red-600' : ''
                }`}>
                  {spent.toFixed(0)} {trip.currency || 'EUR'}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                  {t('budget.remaining')}
                </div>
                <div className={`font-bold text-sm flex items-center justify-center gap-1 ${
                  isOverBudget ? 'text-red-600' : 'text-green-600'
                }`}>
                  {isOverBudget ? (
                    <TrendingDown className="w-3 h-3" />
                  ) : (
                    <TrendingUp className="w-3 h-3" />
                  )}
                  {Math.abs(remaining).toFixed(0)} {trip.currency || 'EUR'}
                </div>
              </div>
            </div>

            {/* Status Badge */}
            {isOverBudget && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-2">
                <p className="text-xs text-red-600 dark:text-red-400 font-medium text-center">
                  {t('budget.budgetExceeded')}
                </p>
              </div>
            )}
          </div>
        </div>
      </Link>
    </motion.div>
  )
}
