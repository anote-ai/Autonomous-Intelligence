import { useState, useEffect } from 'react';

export const useBackendStatus = () => {
  const [isBackendOnline, setIsBackendOnline] = useState(true);

  useEffect(() => {
    const handleBackendStatusChange = (event) => {
      setIsBackendOnline(event.detail.isOnline);
      
      if (event.detail.isOnline && event.detail.wasOffline) {
        console.log('Backend is back online');
      } else if (!event.detail.isOnline) {
        console.log('Backend went offline');
      }
    };

    // Listen for backend status changes
    window.addEventListener('backendStatusChange', handleBackendStatusChange);

    return () => {
      window.removeEventListener('backendStatusChange', handleBackendStatusChange);
    };
  }, []);

  return { isBackendOnline };
};