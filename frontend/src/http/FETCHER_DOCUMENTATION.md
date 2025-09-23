# Revamped Fetcher Documentation

## Overview

The fetcher has been completely revamped with enhanced error handling, retry logic, logging, and additional convenience features.

## Key Improvements

### 🚨 Enhanced Error Handling

- **Structured Error Types**: `NETWORK_ERROR`, `AUTH_ERROR`, `HTTP_ERROR`, `TIMEOUT_ERROR`, `ABORT_ERROR`, `UNKNOWN_ERROR`
- **Detailed Error Objects**: Include timestamp, status codes, original errors, and URL context
- **Silent Error Handling**: Network errors are flagged as silent to reduce UI noise

### 🔄 Intelligent Retry Logic

- **Configurable Retries**: Default 2 retries, configurable via `updateFetcherConfig()`
- **Exponential Backoff**: Automatic delay calculation with maximum caps
- **Status-Based Retries**: Retries on specific HTTP status codes (429, 502, 503, 504)
- **Token Refresh Integration**: Automatic retry after successful token refresh

### 📊 Enhanced Logging

- **Request Tracking**: Unique request IDs for debugging
- **Detailed Logs**: Request/response details, retry attempts, error contexts
- **Development Mode**: Logging automatically enabled in development
- **Log Levels**: Info, warn, error levels for different scenarios

### ⚙️ Configurable Behavior

```javascript
import { updateFetcherConfig, getFetcherConfig } from "./http/RequestConfig";

// Update configuration
updateFetcherConfig({
  maxRetries: 3,
  timeout: 45000,
  retryDelay: 2000,
  enableLogging: true,
});

// Get current configuration
const config = getFetcherConfig();
```

### 🛠 Convenience Methods

```javascript
import { get, post, put, del } from "./http/RequestConfig";

// GET request
const users = await get("users");

// POST request
const newUser = await post("users", {
  name: "John",
  email: "john@example.com",
});

// PUT request
const updatedUser = await put("users/1", { name: "Jane" });

// DELETE request
await del("users/1");
```

### 👤 Guest Mode Support

The fetcher now supports guest mode for unauthenticated users:

```javascript
import { guestGet, guestPost, guestPut, guestDel } from "./http/RequestConfig";

// Guest mode requests (no authentication headers)
const publicData = await guestGet("public/data");

// Guest POST with automatic is_guest flag
const guestChat = await guestPost("chat", {
  message: "Hello in guest mode",
  // is_guest: true is automatically added
});

// Manual guest mode flag
const response = await post("endpoint", data, { isGuest: true });
```

**Guest Mode Features:**

- **No Authentication**: Skips authorization headers
- **Auto Guest Flag**: Automatically adds `is_guest: true` to request body
- **Skip Token Refresh**: Bypasses token refresh logic for guest requests
- **Guest Streaming**: Dedicated guest streaming request methods

### 🌊 Streaming Support

```javascript
import {
  createStreamingRequest,
  createGuestStreamingRequest,
} from "./http/RequestConfig";

// Regular authenticated streaming
const streamRequest = createStreamingRequest("chat/stream", {
  method: "POST",
  body: JSON.stringify({ message: "Hello" }),
});

// Guest mode streaming
const guestStreamRequest = createGuestStreamingRequest("guest/chat/stream", {
  method: "POST",
  body: JSON.stringify({ message: "Hello from guest" }),
});

// Use the streaming request
streamRequest.request
  .then((response) => {
    // Handle streaming response
  })
  .catch((error) => {
    // Handle errors
  });

// Abort if needed
streamRequest.abort();
```

## Error Handling

### Error Object Structure

```javascript
{
  type: 'NETWORK_ERROR',           // Error type from ErrorTypes
  message: 'Backend offline',      // Human-readable message
  originalError: Error,            // Original error object
  statusCode: 503,                 // HTTP status code (if applicable)
  url: 'api/users',               // Request URL
  timestamp: '2025-01-15T10:30:00Z', // ISO timestamp
  silent: true                     // Whether to handle silently
}
```

### Handling Different Error Types

```javascript
import { ErrorTypes } from "./http/RequestConfig";

try {
  const response = await fetcher("api/data");
  // Handle success
} catch (error) {
  switch (error.type) {
    case ErrorTypes.NETWORK_ERROR:
      // Backend is down, show offline message
      break;
    case ErrorTypes.AUTH_ERROR:
      // Authentication failed, redirect to login
      break;
    case ErrorTypes.HTTP_ERROR:
      // Server error, show error message
      break;
    case ErrorTypes.TIMEOUT_ERROR:
      // Request timed out, offer retry
      break;
    default:
    // Unknown error, show generic message
  }
}
```

## Configuration Options

| Option               | Default              | Description                                |
| -------------------- | -------------------- | ------------------------------------------ |
| `maxRetries`         | 2                    | Maximum number of retry attempts           |
| `retryDelay`         | 1000                 | Base delay between retries (ms)            |
| `maxRetryDelay`      | 5000                 | Maximum delay for exponential backoff (ms) |
| `timeout`            | 30000                | Request timeout (ms)                       |
| `enableLogging`      | development mode     | Enable detailed logging                    |
| `retryOnStatus`      | [429, 502, 503, 504] | HTTP status codes to retry on              |
| `exponentialBackoff` | true                 | Use exponential backoff for retries        |

## Migration Guide

### Before (Old Fetcher)

```javascript
import fetcher from "./http/RequestConfig";

fetcher("api/users", { method: "GET" })
  .then((response) => response.json())
  .catch((error) => {
    if (error.type === "NETWORK_ERROR") {
      // Handle network error
    }
  });
```

### After (New Fetcher)

```javascript
import { get, ErrorTypes } from "./http/RequestConfig";

try {
  const response = await get("api/users");
  const data = await response.json();
} catch (error) {
  if (error.type === ErrorTypes.NETWORK_ERROR) {
    // Handle network error with structured error object
  }
}
```

## Best Practices

1. **Use Convenience Methods**: Prefer `get()`, `post()`, etc. over raw `fetcher()`
2. **Handle Error Types**: Check `error.type` for specific error handling
3. **Configure Appropriately**: Adjust retry and timeout settings based on use case
4. **Use Streaming**: Use `createStreamingRequest()` for real-time features
5. **Monitor Logs**: Enable logging in development for debugging

## Backward Compatibility

The revamped fetcher maintains full backward compatibility. Existing code will continue to work without modifications, but can be enhanced to use the new features gradually.
