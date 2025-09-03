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
    return response.json();
  }).then((data) => {
    localStorage.setItem("accessToken", data.accessToken);
    return Promise.resolve({ok: true});
  }).catch((error) => {
    // Check if this is a network error (backend down) vs auth error
    if (isNetworkError(error)) {
      // Don't log every refresh attempt when backend is down
      return Promise.reject({ type: 'NETWORK_ERROR', message: 'Backend offline', silent: true });
    } else {
      // This is likely an auth error - handle normally
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
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
    if (!response.ok) {
      // Return a rejected promise if the response is not successful
      throw new Error('HTTP Error: ' + response.status);
    }
    return response;
  }).catch(
    (error) => {
      // Check if this is a network error (backend down)
      if (isNetworkError(error)) {
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