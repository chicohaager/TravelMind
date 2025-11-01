import React, { useRef, useState } from 'react';
import { Camera, X, FlipHorizontal, ImagePlus } from 'lucide-react';
import toast from 'react-hot-toast';

const NativeCamera = ({ onPhotoTaken, disabled = false, className = '' }) => {
  const fileInputRef = useRef(null);
  const [isCameraSupported, setIsCameraSupported] = useState(true);
  const previewUrlsRef = useRef([]);

  const handleCameraClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Bitte wähle ein Bild aus');
      return;
    }

    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      toast.error('Bild ist zu groß (max. 10MB)');
      return;
    }

    try {
      // Create preview URL
      const previewUrl = URL.createObjectURL(file);

      // Track URL for cleanup
      previewUrlsRef.current.push(previewUrl);

      // Call callback with file and preview
      onPhotoTaken({
        file,
        previewUrl,
        name: file.name,
        size: file.size,
        type: file.type
      });

      toast.success('Foto aufgenommen!');

      // Reset input
      event.target.value = '';
    } catch (error) {
      console.error('Error processing photo:', error);
      toast.error('Fehler beim Verarbeiten des Fotos');
    }
  };

  // Cleanup blob URLs on unmount
  React.useEffect(() => {
    return () => {
      previewUrlsRef.current.forEach(url => {
        URL.revokeObjectURL(url);
      });
      previewUrlsRef.current = [];
    };
  }, []);

  // Check if camera/file input is supported
  React.useEffect(() => {
    const input = document.createElement('input');
    input.setAttribute('type', 'file');
    input.setAttribute('capture', 'camera');
    setIsCameraSupported('capture' in input);
  }, []);

  return (
    <div className={className}>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileChange}
        className="hidden"
        disabled={disabled}
      />

      <button
        type="button"
        onClick={handleCameraClick}
        disabled={disabled}
        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto justify-center"
      >
        <Camera size={20} />
        <span>Foto aufnehmen</span>
      </button>

      <p className="text-xs text-gray-500 mt-2">
        {isCameraSupported
          ? '📸 Öffnet deine Kamera oder Galerie'
          : '📁 Wähle ein Foto aus deiner Galerie'}
      </p>
    </div>
  );
};

export default NativeCamera;
