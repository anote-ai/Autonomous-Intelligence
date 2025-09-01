import React from 'react';

const BackendStatus = ({ isOnline, isChecking }) => {
  if (isOnline) return null;

  return (
    <div className="fixed top-0 left-0 right-0 bg-red-600 text-white px-4 py-2 z-50 flex items-center justify-center">
      <div className="flex items-center space-x-2">
        <div className="w-2 h-2 bg-red-300 rounded-full animate-pulse"></div>
        <span className="text-sm font-medium">
          {isChecking ? 'Checking backend connection...' : 'Backend server is offline'}
        </span>
        <div className="w-2 h-2 bg-red-300 rounded-full animate-pulse"></div>
      </div>
    </div>
  );
};

export default BackendStatus;
