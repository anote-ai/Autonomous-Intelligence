import React, { useEffect, useRef } from 'react';
import { useBackendStatus } from '../hooks/useBackendStatus';
import { useToast } from './Toast';

const BackendStatusToast = () => {
  const { isBackendOnline } = useBackendStatus();
  const { showError, showSuccess } = useToast();
  const previousStatus = useRef(true);
  const offlineToastId = useRef(null);

  useEffect(() => {
    // Don't show toast on initial load
    if (previousStatus.current === isBackendOnline) {
      return;
    }

    if (!isBackendOnline && previousStatus.current) {
      // Backend went offline
      offlineToastId.current = showError(
        'Backend server is offline. Some features may not work.',
        0 // Keep it persistent until backend comes back
      );
    } else if (isBackendOnline && !previousStatus.current) {
      // Backend came back online
      showSuccess('Backend server is back online!', 3000);
      
      // Remove the persistent offline toast if it exists
      if (offlineToastId.current) {
        // Note: We'd need to implement removeToast in the toast context for this
        offlineToastId.current = null;
      }
    }

    previousStatus.current = isBackendOnline;
  }, [isBackendOnline, showError, showSuccess]);

  return null; // This component doesn't render anything itself
};

export default BackendStatusToast;
