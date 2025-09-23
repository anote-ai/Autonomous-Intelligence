const API_ENDPOINT = process.env.REACT_APP_BACK_END_HOST;

// Enhanced error types for better error handling
export const ErrorTypes = {
  NETWORK_ERROR: "NETWORK_ERROR",
  AUTH_ERROR: "AUTH_ERROR",
  HTTP_ERROR: "HTTP_ERROR",
  TIMEOUT_ERROR: "TIMEOUT_ERROR",
  ABORT_ERROR: "ABORT_ERROR",
  UNKNOWN_ERROR: "UNKNOWN_ERROR",
};

// Configuration object for fetcher behavior
const FetcherConfig = {
  maxRetries: 2,
  retryDelay: 1000, // Base delay in ms
  maxRetryDelay: 5000, // Maximum delay in ms
  timeout: 30000, // 30 seconds
  enableLogging: process.env.NODE_ENV === "development",
  retryOnStatus: [429, 502, 503, 504], // HTTP status codes to retry on
  exponentialBackoff: true,
};

// Enhanced error creation utility
function createError(
  type,
  message,
  originalError = null,
  statusCode = null,
  url = null
) {
  return {
    type,
    message,
    originalError,
    statusCode,
    url,
    timestamp: new Date().toISOString(),
    silent: type === ErrorTypes.NETWORK_ERROR, // Network errors should be handled silently
  };
}

// Function to check if error is network-related (backend down) vs auth-related
function isNetworkError(error) {
  return (
    error.name === "TypeError" ||
    error.name === "AbortError" ||
    error.message.includes("fetch") ||
    error.message.includes("NetworkError") ||
    error.message.includes("Failed to fetch") ||
    error.code === "NETWORK_ERROR" ||
    error.type === ErrorTypes.NETWORK_ERROR
  );
}

// Check if HTTP status should trigger a retry
function shouldRetryStatus(status) {
  return FetcherConfig.retryOnStatus.includes(status);
}

// Calculate delay for exponential backoff
function calculateRetryDelay(retryCount) {
  if (!FetcherConfig.exponentialBackoff) {
    return FetcherConfig.retryDelay;
  }

  const delay = FetcherConfig.retryDelay * Math.pow(2, retryCount);
  return Math.min(delay, FetcherConfig.maxRetryDelay);
}

// Enhanced logging utility
function log(level, message, data = null) {
  if (!FetcherConfig.enableLogging) return;

  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}`;

  switch (level) {
    case "error":
      console.error(logMessage, data);
      break;
    case "warn":
      console.warn(logMessage, data);
      break;
    case "info":
      console.info(logMessage, data);
      break;
    default:
      console.log(logMessage, data);
  }
}

// Create AbortController with timeout
function createRequestController() {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, FetcherConfig.timeout);

  return { controller, timeoutId };
}

// Sleep utility for retry delays
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function defaultHeaders(isGuest = false) {
  // Skip authentication headers for guest mode
  if (isGuest) {
    return {};
  }

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

function updateOptions(options, isGuest = false) {
  const update = { ...options };
  const headers = defaultHeaders(isGuest);
  update.headers = {
    ...headers,
    ...update.headers,
  };
  update.credentials = "include";

  // Add guest mode flag to the request body if specified
  if (isGuest && update.body) {
    try {
      const bodyData = JSON.parse(update.body);
      bodyData.is_guest = true;
      update.body = JSON.stringify(bodyData);
    } catch (e) {
      // If body is not JSON, we'll add the flag in a different way
      log("warn", "Could not add is_guest flag to non-JSON body");
    }
  }

  return update;
}

export function refreshAccessToken() {
  log("info", "Attempting to refresh access token");

  const { controller, timeoutId } = createRequestController();

  return fetch(API_ENDPOINT + "/refresh", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("refreshToken")}`,
    },
    signal: controller.signal,
  })
    .then((response) => {
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw createError(
          ErrorTypes.HTTP_ERROR,
          "Token refresh failed",
          null,
          response.status,
          "/refresh"
        );
      }
      return response.json();
    })
    .then((data) => {
      localStorage.setItem("accessToken", data.accessToken);
      log("info", "Access token refreshed successfully");
      return Promise.resolve({ ok: true });
    })
    .catch((error) => {
      clearTimeout(timeoutId);

      // Handle different error types
      if (error.name === "AbortError") {
        const timeoutError = createError(
          ErrorTypes.TIMEOUT_ERROR,
          "Token refresh timed out",
          error,
          null,
          "/refresh"
        );
        log("error", "Token refresh timeout", timeoutError);
        return Promise.reject(timeoutError);
      }

      // Check if this is a network error (backend down) vs auth error
      if (isNetworkError(error)) {
        const networkError = createError(
          ErrorTypes.NETWORK_ERROR,
          "Backend offline during token refresh",
          error,
          null,
          "/refresh"
        );
        log("warn", "Network error during token refresh", networkError);
        return Promise.reject(networkError);
      } else {
        // This is likely an auth error - handle normally
        log("error", "Authentication error during token refresh", error);
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        window.location.replace("/");

        const authError = createError(
          ErrorTypes.AUTH_ERROR,
          "Authentication failed during refresh",
          error,
          error.statusCode,
          "/refresh"
        );
        return Promise.reject(authError);
      }
    });
}

// Enhanced fetcher with improved error handling, retry logic, and debugging
async function fetcher(url, options = {}, retryCount = 0) {
  const requestId = `req_${Date.now()}_${Math.random()
    .toString(36)
    .substr(2, 9)}`;
  const fullUrl = `${API_ENDPOINT}/${url}`;

  // Check if this is a guest mode request
  let isGuest = options.isGuest || false;

  // Also check if guest flag is in the request body
  if (!isGuest && options.body) {
    try {
      const bodyData = JSON.parse(options.body);
      isGuest = bodyData.is_guest || false;
    } catch (e) {
      // Body is not JSON, continue with isGuest = false
    }
  }

  log("info", `[${requestId}] Starting request to: ${url}`, {
    attempt: retryCount + 1,
    maxRetries: FetcherConfig.maxRetries + 1,
    isGuest: isGuest,
    options: { ...options, headers: "***" }, // Hide sensitive headers in logs
  });

  // Create abort controller with timeout
  const { controller, timeoutId } = createRequestController();

  try {
    // Make the actual request
    const response = await fetch(fullUrl, {
      ...updateOptions(options, isGuest),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Handle successful responses
    if (response.ok) {
      log("info", `[${requestId}] Request successful`, {
        status: response.status,
        statusText: response.statusText,
        isGuest: isGuest,
      });
      return response;
    }

    // Handle HTTP errors
    const httpError = createError(
      ErrorTypes.HTTP_ERROR,
      `HTTP Error: ${response.status} ${response.statusText}`,
      null,
      response.status,
      url
    );

    log("warn", `[${requestId}] HTTP error`, { ...httpError, isGuest });

    // Check if we should retry based on status code
    if (
      shouldRetryStatus(response.status) &&
      retryCount < FetcherConfig.maxRetries
    ) {
      return await retryRequest(url, options, retryCount, requestId, httpError);
    }

    throw httpError;
  } catch (error) {
    clearTimeout(timeoutId);

    // Handle different error types
    if (error.name === "AbortError") {
      const timeoutError = createError(
        ErrorTypes.TIMEOUT_ERROR,
        "Request timed out",
        error,
        null,
        url
      );
      log("error", `[${requestId}] Request timeout`, {
        ...timeoutError,
        isGuest,
      });
      throw timeoutError;
    }

    // Handle network errors
    if (isNetworkError(error)) {
      const networkError = createError(
        ErrorTypes.NETWORK_ERROR,
        "Backend offline",
        error,
        null,
        url
      );
      log("warn", `[${requestId}] Network error`, { ...networkError, isGuest });
      throw networkError;
    }

    // Handle HTTP errors that were already processed
    if (error.type) {
      throw error;
    }

    // Skip token refresh for guest mode requests
    if (isGuest) {
      log("info", `[${requestId}] Skipping token refresh for guest request`);
      const guestError = createError(
        ErrorTypes.AUTH_ERROR,
        "Guest mode - authentication not available",
        error,
        401,
        url
      );
      throw guestError;
    }

    // Handle authentication errors and retry with token refresh (non-guest only)
    if (retryCount < FetcherConfig.maxRetries) {
      return await retryWithTokenRefresh(
        url,
        options,
        retryCount,
        requestId,
        error
      );
    }

    // Unknown error
    const unknownError = createError(
      ErrorTypes.UNKNOWN_ERROR,
      "Unknown error occurred",
      error,
      null,
      url
    );
    log("error", `[${requestId}] Unknown error`, { ...unknownError, isGuest });
    throw unknownError;
  }
}

// Helper function to handle retries with exponential backoff
async function retryRequest(
  url,
  options,
  retryCount,
  requestId,
  originalError
) {
  const nextRetryCount = retryCount + 1;
  const delay = calculateRetryDelay(retryCount);

  log("info", `[${requestId}] Retrying request in ${delay}ms`, {
    attempt: nextRetryCount + 1,
    maxRetries: FetcherConfig.maxRetries + 1,
    reason: originalError.message,
  });

  await sleep(delay);
  return fetcher(url, options, nextRetryCount);
}

// Helper function to handle token refresh and retry
async function retryWithTokenRefresh(
  url,
  options,
  retryCount,
  requestId,
  originalError
) {
  log("info", `[${requestId}] Attempting token refresh before retry`);

  try {
    const refreshResponse = await refreshAccessToken();

    if (!refreshResponse.ok) {
      throw createError(
        ErrorTypes.AUTH_ERROR,
        "Token refresh failed",
        null,
        null,
        url
      );
    }

    log("info", `[${requestId}] Token refreshed, retrying original request`);
    return fetcher(url, options, retryCount + 1);
  } catch (refreshError) {
    // If token refresh failed due to network error, don't retry the original request
    if (refreshError.type === ErrorTypes.NETWORK_ERROR) {
      log("warn", `[${requestId}] Token refresh failed due to network error`);
      throw refreshError;
    }

    // For other refresh errors, throw the original error
    log(
      "error",
      `[${requestId}] Token refresh failed, giving up`,
      refreshError
    );
    throw originalError;
  }
}

// Export configuration for external modification if needed
export function updateFetcherConfig(newConfig) {
  Object.assign(FetcherConfig, newConfig);
  log("info", "Fetcher configuration updated", FetcherConfig);
}

// Get current configuration
export function getFetcherConfig() {
  return { ...FetcherConfig };
}

// Convenience function for GET requests
export function get(url, options = {}) {
  return fetcher(url, { method: "GET", ...options });
}

// Convenience function for POST requests
export function post(url, data, options = {}) {
  return fetcher(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    body: JSON.stringify(data),
    ...options,
  });
}

// Convenience function for PUT requests
export function put(url, data, options = {}) {
  return fetcher(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    body: JSON.stringify(data),
    ...options,
  });
}

// Convenience function for DELETE requests
export function del(url, options = {}) {
  return fetcher(url, { method: "DELETE", ...options });
}

// Guest mode convenience functions
export function guestGet(url, options = {}) {
  return fetcher(url, { method: "GET", isGuest: true, ...options });
}

export function guestPost(url, data, options = {}) {
  // Ensure data includes guest flag
  const guestData = { ...data, is_guest: true };

  return fetcher(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    body: JSON.stringify(guestData),
    isGuest: true,
    ...options,
  });
}

export function guestPut(url, data, options = {}) {
  // Ensure data includes guest flag
  const guestData = { ...data, is_guest: true };

  return fetcher(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    body: JSON.stringify(guestData),
    isGuest: true,
    ...options,
  });
}

export function guestDel(url, options = {}) {
  return fetcher(url, { method: "DELETE", isGuest: true, ...options });
}

// Function to create streaming requests (for chat/real-time features)
export function createStreamingRequest(url, options = {}) {
  const { controller } = createRequestController();
  const isGuest = options.isGuest || false;

  const streamOptions = {
    ...updateOptions(options, isGuest),
    signal: controller.signal,
  };

  log("info", `Creating streaming request to: ${url}`, { isGuest });

  return {
    request: fetch(`${API_ENDPOINT}/${url}`, streamOptions),
    controller,
    abort: () => {
      log("info", `Aborting streaming request to: ${url}`, { isGuest });
      controller.abort();
    },
  };
}

// Guest mode streaming request
export function createGuestStreamingRequest(url, options = {}) {
  return createStreamingRequest(url, { ...options, isGuest: true });
}

export default fetcher;
