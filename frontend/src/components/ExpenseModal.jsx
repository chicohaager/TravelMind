import { useState, useEffect } from 'react'
import { X, DollarSign, Calendar, User, Users } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'

const categories = [
  { value: 'food', labelKey: 'budget.categories.food', icon: '🍽️' },
  { value: 'transport', labelKey: 'budget.categories.transport', icon: '🚗' },
  { value: 'accommodation', labelKey: 'budget.categories.accommodation', icon: '🏨' },
  { value: 'activities', labelKey: 'budget.categories.activities', icon: '🎯' },
  { value: 'shopping', labelKey: 'budget.categories.shopping', icon: '🛍️' },
  { value: 'other', labelKey: 'budget.categories.other', icon: '📝' }
]

export default function ExpenseModal({ isOpen, onClose, onSubmit, initialData = null, participants = [] }) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    title: '',
    amount: '',
    currency: 'EUR',
    category: 'other',
    date: new Date().toISOString().split('T')[0],
    paid_by: '',
    notes: '',
    splits: []
  })

  const [splitMode, setSplitMode] = useState('equal') // 'equal' or 'custom'

  useEffect(() => {
    if (initialData) {
      setFormData({
        title: initialData.title || '',
        amount: initialData.amount || '',
        currency: initialData.currency || 'EUR',
        category: initialData.category || 'other',
        date: initialData.date ? new Date(initialData.date).toISOString().split('T')[0] : new Date().toISOString().split('T')[0],
        paid_by: initialData.paid_by || '',
        notes: initialData.notes || '',
        splits: initialData.splits || []
      })
      setSplitMode(initialData.splits && initialData.splits.length > 0 ? 'custom' : 'equal')
    } else if (!isOpen) {
      // Reset form
      setFormData({
        title: '',
        amount: '',
        currency: 'EUR',
        category: 'other',
        date: new Date().toISOString().split('T')[0],
        paid_by: participants.length > 0 ? participants[0].id : '',
        notes: '',
        splits: []
      })
      setSplitMode('equal')
    }
  }, [initialData, isOpen, participants])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))

    // Recalculate equal splits when amount changes
    if (name === 'amount' && splitMode === 'equal') {
      calculateEqualSplits(parseFloat(value) || 0)
    }
  }

  const calculateEqualSplits = (totalAmount) => {
    if (participants.length === 0) return

    const splitAmount = totalAmount / participants.length
    const splits = participants.map((p, i) => ({
      participant_id: p.id,
      // Last participant gets remainder to handle rounding
      amount: i === participants.length - 1
        ? totalAmount - (splitAmount * (participants.length - 1))
        : splitAmount
    }))

    setFormData((prev) => ({ ...prev, splits }))
  }

  const handleSplitModeChange = (mode) => {
    setSplitMode(mode)

    if (mode === 'equal') {
      calculateEqualSplits(parseFloat(formData.amount) || 0)
    } else {
      // Custom mode - initialize with zeros
      const splits = participants.map((p) => ({
        participant_id: p.id,
        amount: 0
      }))
      setFormData((prev) => ({ ...prev, splits }))
    }
  }

  const handleSplitChange = (participantId, amount) => {
    const newSplits = formData.splits.map((split) =>
      split.participant_id === participantId
        ? { ...split, amount: parseFloat(amount) || 0 }
        : split
    )
    setFormData((prev) => ({ ...prev, splits: newSplits }))
  }

  const getTotalSplits = () => {
    return formData.splits.reduce((sum, split) => sum + (split.amount || 0), 0)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    const totalAmount = parseFloat(formData.amount)
    const totalSplits = getTotalSplits()

    // Validate splits
    if (Math.abs(totalSplits - totalAmount) > 0.01) {
      alert(t('budget:splitSumError')
        .replace('{splitSum}', totalSplits.toFixed(2))
        .replace('{totalAmount}', totalAmount.toFixed(2)))
      return
    }

    const expenseData = {
      title: formData.title,
      amount: totalAmount,
      currency: formData.currency,
      category: formData.category,
      date: formData.date,
      paid_by: parseInt(formData.paid_by),
      notes: formData.notes || null,
      splits: formData.splits.map((split) => ({
        participant_id: split.participant_id,
        amount: parseFloat(split.amount)
      }))
    }

    await onSubmit(expenseData)
  }

  if (!isOpen) return null

  const totalSplits = getTotalSplits()
  const totalAmount = parseFloat(formData.amount) || 0
  const isValid = Math.abs(totalSplits - totalAmount) <= 0.01

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              {/* Header */}
              <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-between items-center">
                <h2 className="text-2xl font-bold">
                  {initialData ? t('budget:editExpense') : t('budget:newExpense')}
                </h2>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-6 space-y-6">
                {/* Title & Category */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('budget:titleLabel')} *</label>
                    <input
                      type="text"
                      name="title"
                      value={formData.title}
                      onChange={handleChange}
                      placeholder={t('budget:titlePlaceholder')}
                      required
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('budget:categoryLabel')}</label>
                    <select name="category" value={formData.category} onChange={handleChange} className="input">
                      {categories.map((cat) => (
                        <option key={cat.value} value={cat.value}>
                          {cat.icon} {t(cat.labelKey)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Amount & Currency */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="col-span-2">
                    <label className="block text-sm font-medium mb-2">
                      <DollarSign className="w-4 h-4 inline mr-1" />
                      {t('budget:amountLabel')} *
                    </label>
                    <input
                      type="number"
                      name="amount"
                      value={formData.amount}
                      onChange={handleChange}
                      placeholder="0.00"
                      step="0.01"
                      min="0"
                      required
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">{t('budget:currencyLabel')}</label>
                    <select name="currency" value={formData.currency} onChange={handleChange} className="input">
                      <option value="EUR">EUR (€)</option>
                      <option value="USD">USD ($)</option>
                      <option value="GBP">GBP (£)</option>
                    </select>
                  </div>
                </div>

                {/* Date & Paid By */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      <Calendar className="w-4 h-4 inline mr-1" />
                      {t('budget:dateLabel')} *
                    </label>
                    <input
                      type="date"
                      name="date"
                      value={formData.date}
                      onChange={handleChange}
                      required
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      <User className="w-4 h-4 inline mr-1" />
                      {t('budget:paidByLabel')} *
                    </label>
                    <select name="paid_by" value={formData.paid_by} onChange={handleChange} required className="input">
                      <option value="">{t('budget:paidByPlaceholder')}</option>
                      {participants.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Notes */}
                <div>
                  <label className="block text-sm font-medium mb-2">{t('budget:notesLabel')}</label>
                  <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    placeholder={t('budget:notesPlaceholder')}
                    rows={2}
                    className="input"
                  />
                </div>

                {/* Split Mode */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    <Users className="w-4 h-4 inline mr-1" />
                    {t('budget:splitLabel')}
                  </label>
                  <div className="flex gap-2 mb-3">
                    <button
                      type="button"
                      onClick={() => handleSplitModeChange('equal')}
                      className={`flex-1 px-4 py-2 rounded-lg border transition-colors ${
                        splitMode === 'equal'
                          ? 'bg-primary-500 text-white border-primary-500'
                          : 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600'
                      }`}
                    >
                      {t('budget:splitEqual')}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSplitModeChange('custom')}
                      className={`flex-1 px-4 py-2 rounded-lg border transition-colors ${
                        splitMode === 'custom'
                          ? 'bg-primary-500 text-white border-primary-500'
                          : 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600'
                      }`}
                    >
                      {t('budget:splitCustom')}
                    </button>
                  </div>

                  {/* Split Breakdown */}
                  <div className="space-y-2">
                    {formData.splits.map((split) => {
                      const participant = participants.find((p) => p.id === split.participant_id)
                      return (
                        <div key={split.participant_id} className="flex items-center gap-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                          <div className="flex-1 font-medium">{participant?.name || t('budget:unknown')}</div>
                          <input
                            type="number"
                            value={split.amount}
                            onChange={(e) => handleSplitChange(split.participant_id, e.target.value)}
                            disabled={splitMode === 'equal'}
                            step="0.01"
                            min="0"
                            className="input w-32"
                          />
                          <span className="text-sm text-gray-500">{formData.currency}</span>
                        </div>
                      )
                    })}
                  </div>

                  {/* Validation */}
                  <div className={`mt-3 p-3 rounded-lg text-sm ${isValid ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300' : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'}`}>
                    <div className="flex justify-between">
                      <span>{t('budget:totalSplit')}</span>
                      <strong>{totalSplits.toFixed(2)} {formData.currency}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>{t('budget:totalAmount')}</span>
                      <strong>{totalAmount.toFixed(2)} {formData.currency}</strong>
                    </div>
                    {!isValid && (
                      <div className="mt-2 font-medium">
                        {t('budget:splitValidationError')}
                      </div>
                    )}
                  </div>
                </div>

                {/* Buttons */}
                <div className="flex gap-3 pt-4">
                  <button type="button" onClick={onClose} className="btn btn-secondary flex-1">
                    {t('common:cancel')}
                  </button>
                  <button type="submit" disabled={!isValid} className="btn btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed">
                    {initialData ? t('budget:saveButton') : t('budget:addButton')}
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
