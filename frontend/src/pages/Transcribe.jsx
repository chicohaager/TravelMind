import { useState } from 'react'
import { motion } from 'framer-motion'
import { Mic, Upload, FileAudio, Copy, Download, Trash2 } from 'lucide-react'
import AudioRecorder from '@/components/AudioRecorder'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'

export default function Transcribe() {
  const { t } = useTranslation()
  const [transcribedText, setTranscribedText] = useState('')
  const [history, setHistory] = useState([])

  const handleTranscriptReceived = (text) => {
    setTranscribedText(text)

    // Add to history
    const newEntry = {
      id: Date.now(),
      text: text,
      timestamp: new Date().toLocaleString('de-DE'),
      length: text.length
    }
    setHistory(prev => [newEntry, ...prev])

    toast.success(t('transcribe.audioTranscribedSuccess'))
  }

  const handleCopyText = () => {
    navigator.clipboard.writeText(transcribedText)
    toast.success(t('transcribe.textCopied'))
  }

  const handleDownloadText = () => {
    const blob = new Blob([transcribedText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `transkription-${Date.now()}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast.success(t('transcribe.textDownloaded'))
  }

  const handleClearText = () => {
    setTranscribedText('')
    toast.success(t('transcribe.textDeleted'))
  }

  const handleLoadFromHistory = (text) => {
    setTranscribedText(text)
    toast.success(t('transcribe.textLoadedFromHistory'))
  }

  const handleClearHistory = () => {
    setHistory([])
    toast.success(t('transcribe.historyCleared'))
  }

  return (
    <div className="max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold mb-2">{t('transcribe.title')}</h1>
        <p className="text-gray-600 dark:text-gray-400">
          {t('transcribe.description')}
        </p>
      </motion.div>

      {/* Audio Recorder */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card mb-8"
      >
        <div className="flex items-center gap-2 mb-4">
          <Mic className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          <h2 className="text-xl font-bold">{t('transcribe.record')}</h2>
        </div>

        <AudioRecorder onTranscriptReceived={handleTranscriptReceived} />
      </motion.div>

      {/* Transcribed Text */}
      {transcribedText && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card mb-8"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">{t('transcribe.transcribedText')}</h2>
            <div className="flex gap-2">
              <button
                onClick={handleCopyText}
                className="btn-outline flex items-center gap-2"
                title={t('transcribe.copyText')}
              >
                <Copy className="w-4 h-4" />
              </button>
              <button
                onClick={handleDownloadText}
                className="btn-outline flex items-center gap-2"
                title={t('transcribe.downloadText')}
              >
                <Download className="w-4 h-4" />
              </button>
              <button
                onClick={handleClearText}
                className="btn-outline text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2"
                title={t('transcribe.deleteText')}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          <textarea
            value={transcribedText}
            onChange={(e) => setTranscribedText(e.target.value)}
            className="input w-full min-h-[200px] font-mono text-sm"
            placeholder={t('transcribe.placeholder')}
          />

          <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {t('transcribe.charactersWords', {
              chars: transcribedText.length,
              words: transcribedText.split(/\s+/).filter(w => w).length
            })}
          </div>
        </motion.div>
      )}

      {/* History */}
      {history.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <FileAudio className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              <h2 className="text-xl font-bold">{t('transcribe.history')}</h2>
            </div>
            <button
              onClick={handleClearHistory}
              className="btn-outline text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 text-sm"
            >
              {t('transcribe.clearHistory')}
            </button>
          </div>

          <div className="space-y-3">
            {history.map((entry) => (
              <div
                key={entry.id}
                className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                onClick={() => handleLoadFromHistory(entry.text)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {entry.timestamp}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-500">
                    {t('transcribe.characters', { count: entry.length })}
                  </div>
                </div>
                <p className="text-sm line-clamp-2">
                  {entry.text}
                </p>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Info Box */}
      {!transcribedText && history.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card bg-primary-50 dark:bg-primary-900/20 border-primary-200 dark:border-primary-800"
        >
          <h3 className="font-semibold mb-2 text-primary-900 dark:text-primary-100">
            {t('transcribe.howItWorks')}
          </h3>
          <ul className="space-y-2 text-sm text-primary-800 dark:text-primary-200">
            <li className="flex items-start gap-2">
              <Mic className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{t('transcribe.clickMicrophone')}</span>
            </li>
            <li className="flex items-start gap-2">
              <Upload className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{t('transcribe.uploadFile')}</span>
            </li>
            <li className="flex items-start gap-2">
              <FileAudio className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{t('transcribe.autoTranscribe')}</span>
            </li>
          </ul>
          <div className="mt-4 pt-4 border-t border-primary-200 dark:border-primary-800 text-xs text-primary-700 dark:text-primary-300">
            {t('transcribe.poweredBy')}
          </div>
        </motion.div>
      )}
    </div>
  )
}
