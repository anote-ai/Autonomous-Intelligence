const API_ENDPOINT = process.env.REACT_APP_BACK_END_HOST;

// Global state for backend connectivity
let isBackendOnline = true;
let lastOfflineLog = 0;
const OFFLINE_LOG_INTERVAL = 30000; // Only log offline status every 30 seconds

// Function to check if error is network-related (backend down) vs auth-related
function isNetworkError(error) {
  return (
    error.name === 'TypeError' || 
    error.message.includes('fetch') ||
    error.message.includes('NetworkError') ||
    error.message.includes('Failed to fetch') ||
    error.code === 'NETWORK_ERROR'
  );
}

// Function to handle backend connectivity status
function updateBackendStatus(isOnline) {
  const wasOffline = !isBackendOnline;
  isBackendOnline = isOnline;
  
  // Only log status changes, not every failed request
  if (isOnline && wasOffline) {
    console.log('✅ Backend is back online');
  } else if (!isOnline && wasOffline) {
    const now = Date.now();
    if (now - lastOfflineLog > OFFLINE_LOG_INTERVAL) {
      console.warn('🔴 Backend is offline');
      lastOfflineLog = now;
    }
  }
  
  // Dispatch custom event for UI components to listen to
  window.dispatchEvent(new CustomEvent('backendStatusChange', { 
    detail: { isOnline, wasOffline } 
  }));
}

export function defaultHeaders() {
  const accessToken = localStorage.getItem("accessToken");
  const sessionToken = localStorage.getItem("sessionToken");

  if (accessToken) {
    return {
      Authorization: `Bearer ${accessToken}`,
    };
  } else {
    return {
      Authorization: `Bearer ${sessionToken}`,
    };
  }
}


function updateOptions(options) {
  const update = { ...options };
  const headers = defaultHeaders();
  update.headers = {
    ...headers,
    ...update.headers,
  };
  update.credentials = "include";
  return update;
}

export function refreshAccessToken() {
  return fetch(API_ENDPOINT + "/refresh", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("refreshToken")}`,
    },
  }).then((response) => {
    if (!response.ok) {
      // Return a rejected promise if the response is not successful
      throw new Error('Token refresh failed');
    }
    updateBackendStatus(true); // Backend is working
    return response.json();
  }).then((data) => {
    localStorage.setItem("accessToken", data.accessToken);
    return Promise.resolve({ok: true});
  }).catch((error) => {
    // Check if this is a network error (backend down) vs auth error
    if (isNetworkError(error)) {
      updateBackendStatus(false);
      // Don't log every refresh attempt when backend is down
      return Promise.reject({ type: 'NETWORK_ERROR', message: 'Backend offline', silent: true });
    } else {
      // This is likely an auth error - handle normally
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      updateBackendStatus(true); // Backend is up, but auth failed
      window.location.replace("/");
      return Promise.reject(error);
    }
  });
}

function fetcher(url, options = {}, retryCount = 0) {
  // Hardcode the maximum number of retries
  const maxRetries = 1;

  // Reduce console noise - only log in development mode
  if (process.env.NODE_ENV === 'development') {
    console.log("Making request to:", url);
  }

  return fetch(API_ENDPOINT + "/" + url, updateOptions(options)).then((response) => {
    updateBackendStatus(true); // Backend is responding
    if (!response.ok) {
      // Return a rejected promise if the response is not successful
      throw new Error('HTTP Error: ' + response.status);
    }
    return response;
  }).catch(
    (error) => {
      // Check if this is a network error (backend down)
      if (isNetworkError(error)) {
        updateBackendStatus(false);
        // Don't spam console with offline errors
        
        return Promise.reject({ 
          type: 'NETWORK_ERROR', 
          message: 'Backend offline',
          originalUrl: url,
          silent: true // Flag to indicate this should be handled silently
        });
      }

      // For non-network errors, try token refresh if we haven't exceeded retries
      if (retryCount <= maxRetries) {
        return refreshAccessToken().then((response) => {
          if (!response.ok) {
            // Return a rejected promise if the response is not successful
            throw new Error('Token refresh failed');
          }
          return fetcher(url, options, retryCount + 1);
        }).catch(
          (error) => {
            // If token refresh failed due to network error, don't retry
            if (error.type === 'NETWORK_ERROR') {
              return Promise.reject(error);
            }
            return Promise.reject(error);
          }
        );
      } else {
        return Promise.reject(error);
      }
    }
  );
}

export default fetcher;