import { useState } from 'react'
import { X, Upload, UserPlus, Users as UsersIcon } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { participantsService } from '@services/api'
import toast from 'react-hot-toast'

export default function ParticipantsManager({ tripId, participants = [], isEditing = false }) {
  const [newParticipant, setNewParticipant] = useState({ name: '', email: '', role: '' })
  const [selectedPhoto, setSelectedPhoto] = useState(null)
  const [uploadingForId, setUploadingForId] = useState(null)
  const queryClient = useQueryClient()

  // Add participant mutation
  const addParticipantMutation = useMutation({
    mutationFn: async (data) => {
      const response = await participantsService.create(tripId, data)
      return response.data
    },
    onSuccess: async (newParticipant) => {
      queryClient.invalidateQueries(['participants', tripId])

      // Upload photo if one was selected
      if (selectedPhoto) {
        await uploadPhotoMutation.mutateAsync({
          participantId: newParticipant.id,
          file: selectedPhoto
        })
      }

      setNewParticipant({ name: '', email: '', role: '' })
      setSelectedPhoto(null)
      toast.success('Teilnehmer hinzugefügt')
    },
    onError: () => {
      toast.error('Fehler beim Hinzufügen')
    }
  })

  // Upload photo mutation
  const uploadPhotoMutation = useMutation({
    mutationFn: async ({ participantId, file }) => {
      const response = await participantsService.uploadPhoto(participantId, file)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['participants', tripId])
      setUploadingForId(null)
      toast.success('Foto hochgeladen')
    },
    onError: () => {
      toast.error('Fehler beim Hochladen')
      setUploadingForId(null)
    }
  })

  // Delete participant mutation
  const deleteParticipantMutation = useMutation({
    mutationFn: async (participantId) => {
      await participantsService.delete(participantId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['participants', tripId])
      toast.success('Teilnehmer entfernt')
    },
    onError: () => {
      toast.error('Fehler beim Entfernen')
    }
  })

  const handlePhotoSelect = (e, participantId) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate
      const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
      if (!allowedTypes.includes(file.type)) {
        toast.error('Nur Bilder erlaubt')
        return
      }
      if (file.size > 5 * 1024 * 1024) {
        toast.error('Bild zu groß (max. 5MB)')
        return
      }

      setUploadingForId(participantId)
      uploadPhotoMutation.mutate({ participantId, file })
    }
  }

  const handleNewPhotoSelect = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
      if (!allowedTypes.includes(file.type)) {
        toast.error('Nur Bilder erlaubt')
        return
      }
      if (file.size > 5 * 1024 * 1024) {
        toast.error('Bild zu groß (max. 5MB)')
        return
      }
      setSelectedPhoto(file)
    }
  }

  const handleAddParticipant = () => {
    if (!newParticipant.name.trim()) {
      toast.error('Name erforderlich')
      return
    }
    addParticipantMutation.mutate(newParticipant)
  }

  const getPhotoUrl = (photoUrl) => {
    return photoUrl || null
  }

  return (
    <div>
      <label className="block text-sm font-medium mb-3">
        <UsersIcon className="w-4 h-4 inline mr-2" />
        Teilnehmer
      </label>

      {/* Existing Participants */}
      {participants.length > 0 && (
        <div className="space-y-2 mb-4">
          {participants.map((participant) => (
            <div
              key={participant.id}
              className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
            >
              {/* Photo */}
              <div className="relative">
                {participant.photo_url ? (
                  <img
                    src={getPhotoUrl(participant.photo_url)}
                    alt={participant.name}
                    className="w-12 h-12 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-full bg-primary-200 dark:bg-primary-700 flex items-center justify-center">
                    <span className="text-primary-700 dark:text-primary-200 font-semibold">
                      {participant.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                )}

                {/* Upload button overlay */}
                <label className="absolute inset-0 rounded-full bg-black/50 opacity-0 hover:opacity-100 transition-opacity cursor-pointer flex items-center justify-center">
                  <Upload className="w-5 h-5 text-white" />
                  <input
                    type="file"
                    className="hidden"
                    accept="image/*"
                    onChange={(e) => handlePhotoSelect(e, participant.id)}
                    disabled={uploadingForId === participant.id}
                  />
                </label>
              </div>

              {/* Info */}
              <div className="flex-1">
                <div className="font-medium">{participant.name}</div>
                {participant.email && (
                  <div className="text-xs text-gray-600 dark:text-gray-400">{participant.email}</div>
                )}
                {participant.role && (
                  <div className="text-xs text-gray-500">{participant.role}</div>
                )}
              </div>

              {/* Delete button */}
              {isEditing && (
                <button
                  type="button"
                  onClick={() => deleteParticipantMutation.mutate(participant.id)}
                  className="p-2 hover:bg-red-100 dark:hover:bg-red-900 rounded-lg transition-colors"
                  disabled={deleteParticipantMutation.isPending}
                >
                  <X className="w-4 h-4 text-red-600" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add New Participant */}
      {isEditing && (
        <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <input
                type="text"
                placeholder="Name *"
                value={newParticipant.name}
                onChange={(e) => setNewParticipant({ ...newParticipant, name: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <input
                type="email"
                placeholder="E-Mail (optional)"
                value={newParticipant.email}
                onChange={(e) => setNewParticipant({ ...newParticipant, email: e.target.value })}
                className="input"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Rolle (z.B. Freund, Familie)"
              value={newParticipant.role}
              onChange={(e) => setNewParticipant({ ...newParticipant, role: e.target.value })}
              className="input flex-1"
            />

            {/* Photo upload */}
            <label className="btn btn-secondary cursor-pointer">
              {selectedPhoto ? '📷' : <Upload className="w-4 h-4" />}
              <input
                type="file"
                className="hidden"
                accept="image/*"
                onChange={handleNewPhotoSelect}
              />
            </label>

            <button
              type="button"
              onClick={handleAddParticipant}
              disabled={addParticipantMutation.isPending}
              className="btn btn-primary"
            >
              <UserPlus className="w-4 h-4" />
              Hinzufügen
            </button>
          </div>

          {selectedPhoto && (
            <div className="text-xs text-gray-600 dark:text-gray-400">
              Foto ausgewählt: {selectedPhoto.name}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
