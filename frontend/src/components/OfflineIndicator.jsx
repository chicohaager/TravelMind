import { useState, useEffect } from 'react';
import { WifiOff, Wifi } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const OfflineIndicator = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [showNotification, setShowNotification] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setShowNotification(true);
      setTimeout(() => setShowNotification(false), 3000);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowNotification(true);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return (
    <AnimatePresence>
      {showNotification && (
        <motion.div
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -50 }}
          className={`fixed top-20 left-1/2 transform -translate-x-1/2 z-[100] px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 ${
            isOnline
              ? 'bg-green-500 text-white'
              : 'bg-red-500 text-white'
          }`}
        >
          {isOnline ? (
            <>
              <Wifi size={20} />
              <span className="font-medium">Du bist wieder online!</span>
            </>
          ) : (
            <>
              <WifiOff size={20} />
              <span className="font-medium">Offline-Modus</span>
            </>
          )}
        </motion.div>
      )}

      {/* Permanent indicator when offline */}
      {!isOnline && !showNotification && (
        <div className="fixed bottom-4 right-4 z-50 bg-red-500 text-white px-3 py-2 rounded-full shadow-lg flex items-center gap-2 text-sm">
          <WifiOff size={16} />
          <span className="hidden sm:inline">Offline</span>
        </div>
      )}
    </AnimatePresence>
  );
};

export default OfflineIndicator;
