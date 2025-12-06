import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, DollarSign, TrendingUp, TrendingDown } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import { formatError } from '../utils/errorHandler'
import { budgetService } from '@services/api'
import ExpenseCard from './ExpenseCard'
import ExpenseModal from './ExpenseModal'

export default function BudgetView({ tripId, participants }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false)
  const [editingExpense, setEditingExpense] = useState(null)

  // Fetch expenses
  const { data: expenses = [], isLoading: expensesLoading } = useQuery({
    queryKey: ['expenses', tripId],
    queryFn: async () => {
      const response = await budgetService.getExpenses(tripId)
      return response.data
    },
    enabled: !!tripId
  })

  // Fetch budget summary
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['budget-summary', tripId],
    queryFn: async () => {
      const response = await budgetService.getSummary(tripId)
      return response.data
    },
    enabled: !!tripId
  })

  // Create expense mutation
  const createExpenseMutation = useMutation({
    mutationFn: async (data) => {
      const response = await budgetService.create(tripId, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['expenses', tripId])
      queryClient.invalidateQueries(['budget-summary', tripId])
      setIsExpenseModalOpen(false)
      toast.success('Ausgabe hinzugefügt')
    },
    onError: (error) => {
      toast.error(formatError(error, t('budget:errorAdding')))
    }
  })

  // Update expense mutation
  const updateExpenseMutation = useMutation({
    mutationFn: async ({ expenseId, data }) => {
      const response = await budgetService.update(expenseId, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['expenses', tripId])
      queryClient.invalidateQueries(['budget-summary', tripId])
      setIsExpenseModalOpen(false)
      setEditingExpense(null)
      toast.success('Ausgabe aktualisiert')
    },
    onError: (error) => {
      toast.error(formatError(error, t('budget:errorUpdating')))
    }
  })

  // Delete expense mutation
  const deleteExpenseMutation = useMutation({
    mutationFn: async (expenseId) => {
      await budgetService.delete(expenseId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['expenses', tripId])
      queryClient.invalidateQueries(['budget-summary', tripId])
      toast.success('Ausgabe gelöscht')
    },
    onError: (error) => {
      toast.error(formatError(error, t('budget:errorDeleting')))
    }
  })

  const handleExpenseSubmit = async (data) => {
    if (editingExpense) {
      await updateExpenseMutation.mutateAsync({ expenseId: editingExpense.id, data })
    } else {
      await createExpenseMutation.mutateAsync(data)
    }
  }

  const handleEditExpense = (expense) => {
    setEditingExpense(expense)
    setIsExpenseModalOpen(true)
  }

  const handleDeleteExpense = async (expenseId) => {
    if (confirm('Möchtest du diese Ausgabe wirklich löschen?')) {
      await deleteExpenseMutation.mutateAsync(expenseId)
    }
  }

  if (expensesLoading || summaryLoading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
        </div>
      </div>
    )
  }

  const categoryLabels = {
    food: 'Essen & Trinken',
    transport: 'Transport',
    accommodation: 'Unterkunft',
    activities: 'Aktivitäten',
    shopping: 'Shopping',
    other: 'Sonstiges'
  }

  return (
    <>
      <div className="space-y-6">
        {/* Budget Summary */}
        {summary && (
          <div className="card">
            <h2 className="text-2xl font-bold mb-4">Budget-Übersicht</h2>

            {/* Total */}
            <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl p-6 mb-6">
              <div className="text-sm opacity-90 mb-1">Gesamtausgaben</div>
              <div className="text-4xl font-bold">
                {summary.total_expenses.toFixed(2)} {summary.currency}
              </div>
            </div>

            {/* By Category */}
            {Object.keys(summary.by_category).length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-3">Nach Kategorie</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {Object.entries(summary.by_category).map(([category, amount]) => (
                    <div key={category} className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                      <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">
                        {categoryLabels[category] || category}
                      </div>
                      <div className="text-lg font-bold">
                        {amount.toFixed(2)} {summary.currency}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* By Participant - Balances */}
            {Object.keys(summary.by_participant).length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3">Teilnehmer-Übersicht</h3>
                <div className="space-y-2">
                  {Object.entries(summary.by_participant).map(([participantId, data]) => {
                    const balance = data.balance
                    const isPositive = balance > 0
                    const isNeutral = Math.abs(balance) < 0.01

                    return (
                      <div key={participantId} className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-semibold">{data.name}</div>
                          <div className={`flex items-center gap-1 font-bold ${
                            isNeutral
                              ? 'text-gray-600 dark:text-gray-400'
                              : isPositive
                              ? 'text-green-600 dark:text-green-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}>
                            {isPositive && <TrendingUp className="w-4 h-4" />}
                            {!isPositive && !isNeutral && <TrendingDown className="w-4 h-4" />}
                            <span>
                              {isNeutral ? 'Ausgeglichen' : `${isPositive ? '+' : ''}${balance.toFixed(2)} ${summary.currency}`}
                            </span>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div>
                            <span className="text-gray-600 dark:text-gray-400">Bezahlt:</span>
                            <span className="ml-2 font-medium">{data.paid.toFixed(2)} {summary.currency}</span>
                          </div>
                          <div>
                            <span className="text-gray-600 dark:text-gray-400">Schuldet:</span>
                            <span className="ml-2 font-medium">{data.owes.toFixed(2)} {summary.currency}</span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Expenses List */}
        <div className="card">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <DollarSign className="w-6 h-6" />
              Ausgaben
            </h2>
            <button
              onClick={() => {
                setEditingExpense(null)
                setIsExpenseModalOpen(true)
              }}
              className="btn btn-primary btn-sm"
              disabled={!participants || participants.length === 0}
            >
              <Plus className="w-4 h-4" />
              Ausgabe hinzufügen
            </button>
          </div>

          {expenses.length === 0 ? (
            <div className="text-center py-12">
              <DollarSign className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                {t('budget:noExpensesYet')}
              </p>
              {participants && participants.length > 0 ? (
                <button
                  onClick={() => {
                    setEditingExpense(null)
                    setIsExpenseModalOpen(true)
                  }}
                  className="btn btn-primary"
                >
                  <Plus className="w-4 h-4" />
                  Erste Ausgabe hinzufügen
                </button>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-500">
                  Füge zuerst Teilnehmer hinzu, um Ausgaben zu erfassen.
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {expenses.map((expense) => (
                <ExpenseCard
                  key={expense.id}
                  expense={expense}
                  participants={participants}
                  onEdit={handleEditExpense}
                  onDelete={handleDeleteExpense}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Expense Modal */}
      <ExpenseModal
        isOpen={isExpenseModalOpen}
        onClose={() => {
          setIsExpenseModalOpen(false)
          setEditingExpense(null)
        }}
        onSubmit={handleExpenseSubmit}
        initialData={editingExpense}
        participants={participants}
      />
    </>
  )
}
