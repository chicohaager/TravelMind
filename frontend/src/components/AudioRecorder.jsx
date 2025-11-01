import React, { useState, useRef } from 'react';
import { Mic, Square, Upload, X, Loader } from 'lucide-react';
import api from '../services/api';

const AudioRecorder = ({ onTranscriptReceived, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  const startRecording = async () => {
    try {
      setError(null);

      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      // Handle data available
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // Handle recording stop
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setAudioBlob(audioBlob);

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      // Start recording
      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (err) {
      console.error('Error starting recording:', err);
      setError('Mikrofon-Zugriff verweigert. Bitte erlaube den Zugriff in deinem Browser.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const uploadAndTranscribe = async () => {
    if (!audioBlob) return;

    try {
      setIsProcessing(true);
      setError(null);

      // Create FormData
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      // Send to backend
      const response = await api.post('/diary/transcribe-audio', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.success) {
        // Call callback with transcribed text
        onTranscriptReceived(response.data.text);

        // Reset
        setAudioBlob(null);
        setRecordingTime(0);
      } else {
        setError('Transkription fehlgeschlagen.');
      }

    } catch (err) {
      console.error('Error transcribing audio:', err);
      setError(err.response?.data?.detail || 'Fehler bei der Transkription. Bitte prüfe ob OPENAI_API_KEY konfiguriert ist.');
    } finally {
      setIsProcessing(false);
    }
  };

  const cancelRecording = () => {
    setAudioBlob(null);
    setRecordingTime(0);
    setError(null);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="audio-recorder">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          <p className="text-sm">{error}</p>
        </div>
      )}

      <div className="flex items-center gap-3">
        {!audioBlob ? (
          <>
            {!isRecording ? (
              <button
                type="button"
                onClick={startRecording}
                disabled={disabled || isProcessing}
                className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Mic size={20} />
                <span>Aufnahme starten</span>
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={stopRecording}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-800 text-white rounded-lg transition"
                >
                  <Square size={20} />
                  <span>Stop</span>
                </button>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                  <span className="text-gray-700 font-mono">{formatTime(recordingTime)}</span>
                </div>
              </>
            )}
          </>
        ) : (
          <>
            <div className="flex-1">
              <div className="flex items-center gap-2 text-gray-600">
                <Mic size={18} />
                <span className="text-sm">Aufnahme: {formatTime(recordingTime)}</span>
              </div>
            </div>

            <button
              type="button"
              onClick={uploadAndTranscribe}
              disabled={isProcessing}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition disabled:opacity-50"
            >
              {isProcessing ? (
                <>
                  <Loader size={20} className="animate-spin" />
                  <span>Transkribiere...</span>
                </>
              ) : (
                <>
                  <Upload size={20} />
                  <span>Transkribieren</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={cancelRecording}
              disabled={isProcessing}
              className="p-2 text-gray-400 hover:text-gray-600 transition disabled:opacity-50"
            >
              <X size={20} />
            </button>
          </>
        )}
      </div>

      <p className="text-xs text-gray-500 mt-2">
        💡 Tipp: Klicke auf "Aufnahme starten", sprich deinen Tagebucheintrag und klicke dann auf "Transkribieren". Der Text wird automatisch eingefügt.
      </p>
    </div>
  );
};

export default AudioRecorder;
