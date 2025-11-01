import { DollarSign, Calendar, User, Users, Edit, Trash2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

const categoryIcons = {
  food: '🍽️',
  transport: '🚗',
  accommodation: '🏨',
  activities: '🎯',
  shopping: '🛍️',
  other: '📝'
}

const categoryColors = {
  food: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  transport: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  accommodation: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  activities: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  shopping: 'bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-300',
  other: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}

export default function ExpenseCard({ expense, participants, onEdit, onDelete }) {
  const { t } = useTranslation()
  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('de-DE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    })
  }

  const categoryClass = categoryColors[expense.category] || categoryColors.other
  const categoryIcon = categoryIcons[expense.category] || categoryIcons.other
  const categoryLabel = t(`budget.categories.${expense.category}`) || t('budget.categories.other')

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card hover:shadow-lg transition-shadow"
    >
      <div className="flex justify-between items-start gap-4">
        {/* Left: Content */}
        <div className="flex-1">
          <div className="flex items-start justify-between mb-2">
            <div>
              <h3 className="text-lg font-bold mb-1">{expense.title}</h3>
              <span className={`inline-block text-xs px-2 py-1 rounded-full ${categoryClass}`}>
                {categoryIcon} {categoryLabel}
              </span>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-primary-600 dark:text-primary-400">
                {expense.amount.toFixed(2)} {expense.currency}
              </div>
            </div>
          </div>

          {/* Meta Info */}
          <div className="flex flex-wrap items-center gap-4 mt-3 text-sm text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              <span>{formatDate(expense.date)}</span>
            </div>

            <div className="flex items-center gap-1">
              <User className="w-4 h-4" />
              <span>{t('budget.paidBy')} <strong>{expense.paid_by_name}</strong></span>
            </div>

            {expense.splits && expense.splits.length > 0 && (
              <div className="flex items-center gap-1">
                <Users className="w-4 h-4" />
                <span>{t('budget.splitBetween').replace('{count}', expense.splits.length)}</span>
              </div>
            )}
          </div>

          {/* Splits Details */}
          {expense.splits && expense.splits.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <div className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">{t('budget.splitDetails')}</div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {expense.splits.map((split) => {
                  const participant = participants.find((p) => p.id === split.participant_id)
                  return (
                    <div key={split.participant_id} className="flex items-center justify-between text-xs bg-gray-50 dark:bg-gray-700/50 rounded px-2 py-1">
                      <span>{participant?.name || t('budget.unknown')}</span>
                      <span className="font-medium">{split.amount.toFixed(2)} {expense.currency}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Notes */}
          {expense.notes && (
            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400">{expense.notes}</p>
            </div>
          )}
        </div>

        {/* Right: Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => onEdit(expense)}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title={t('budget.editExpenseButton')}
          >
            <Edit className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(expense.id)}
            className="p-2 hover:bg-red-100 dark:hover:bg-red-900 rounded-lg transition-colors"
            title={t('budget.deleteExpenseButton')}
          >
            <Trash2 className="w-4 h-4 text-red-600" />
          </button>
        </div>
      </div>
    </motion.div>
  )
}
