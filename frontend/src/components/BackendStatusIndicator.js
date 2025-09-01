import React from 'react';
import { useBackendStatus } from '../hooks/useBackendStatus';

const BackendStatusIndicator = () => {
  const { isBackendOnline } = useBackendStatus();

  if (isBackendOnline) {
    return null; // Don't show anything when backend is online
  }

  return (
    <div className="fixed top-0 left-0 right-0 bg-red-600 text-white px-4 py-3 z-50 shadow-lg">
      <div className="flex items-center justify-center space-x-3">
        <div className="flex space-x-1">
          <div className="w-2 h-2 bg-red-300 rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-red-300 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
          <div className="w-2 h-2 bg-red-300 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
        </div>
        <div className="text-center">
          <div className="text-sm font-semibold">Backend Server Offline</div>
          <div className="text-xs opacity-90">Some features may not work until connection is restored</div>
        </div>
        <div className="flex space-x-1">
          <div className="w-2 h-2 bg-red-300 rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-red-300 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
          <div className="w-2 h-2 bg-red-300 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
        </div>
      </div>
    </div>
  );
};

export default BackendStatusIndicator;
