import { useState } from 'react'
import { Sparkles, Send, MapPin, Compass, Coffee, Camera } from 'lucide-react'
import { motion } from 'framer-motion'
import { aiService } from '@services/api'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'

export default function AIAssistant() {
  const { t } = useTranslation()

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: t('ai:greeting')
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const quickActions = [
    {
      icon: MapPin,
      label: t('ai:suggestDestinations'),
      prompt: t('ai:destinationsPrompt'),
      color: 'bg-blue-500'
    },
    {
      icon: Compass,
      label: t('ai:trip7Days'),
      prompt: t('ai:tripPlanPrompt'),
      color: 'bg-purple-500'
    },
    {
      icon: Coffee,
      label: t('ai:localTips'),
      prompt: t('ai:secretTipsPrompt'),
      color: 'bg-orange-500'
    },
    {
      icon: Camera,
      label: t('ai:bestPhotoSpots'),
      prompt: t('ai:photoSpotsPrompt'),
      color: 'bg-pink-500'
    }
  ]

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage = input.trim()
    setInput('')
    setMessages([...messages, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      // Erstelle Kontext aus bisherigen Nachrichten
      const context = messages.slice(1).map(msg => ({
        role: msg.role,
        content: msg.content
      }))

      const response = await aiService.chat(userMessage, context)

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.data.answer || response.data.response
      }])
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error(t('ai:errorMessage'))

      // Remove last user message on error
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }

  const handleQuickAction = (prompt) => {
    setInput(prompt)
    // Könnte auch direkt absenden:
    // handleSubmit({ preventDefault: () => {} })
  }

  return (
    <div className="space-y-6 h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-3xl font-bold">{t('ai:title')}</h1>
          <p className="text-gray-600 dark:text-gray-400">
            {t('ai:personalTravelAdvisor')}
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      {messages.length <= 1 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          {quickActions.map((action, index) => (
            <motion.button
              key={action.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 }}
              onClick={() => handleQuickAction(action.prompt)}
              className="card hover:shadow-lg transition-all duration-200 text-left group"
            >
              <div className={`w-10 h-10 ${action.color} rounded-lg flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
                <action.icon className="w-5 h-5 text-white" />
              </div>
              <h3 className="font-semibold mb-1">{action.label}</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                {action.prompt}
              </p>
            </motion.button>
          ))}
        </motion.div>
      )}

      {/* Chat Messages */}
      <div className="card flex-1 flex flex-col h-[calc(100%-12rem)]">
        <div className="flex-1 overflow-y-auto space-y-4 p-4">
          {messages.map((message, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-primary-500" />
                    <span className="text-xs font-semibold text-primary-500">
                      {t('ai:assistantLabel')}
                    </span>
                  </div>
                )}
                <div className="whitespace-pre-wrap">{message.content}</div>
              </div>
            </motion.div>
          ))}

          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-gray-100 dark:bg-gray-700 rounded-2xl px-4 py-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary-500 animate-pulse" />
                  <span className="text-sm">{t('ai:thinking')}</span>
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="border-t border-gray-200 dark:border-gray-700 p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('ai:askAnything')}
              className="input flex-1"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="btn btn-primary"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            {t('ai:tipMessage')}
          </p>
        </form>
      </div>
    </div>
  )
}
