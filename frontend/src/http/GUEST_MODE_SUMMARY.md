# Guest Mode Integration Summary

## Overview

The fetcher has been enhanced with comprehensive guest mode support, allowing unauthenticated users to interact with the API without authentication requirements.

## Key Features Implemented

### 🔓 **Authentication Bypass**

- **No Auth Headers**: Guest requests skip authorization headers completely
- **Token Refresh Skip**: Bypasses token refresh logic for guest users
- **Credential Handling**: Maintains existing authenticated user functionality

### 🏷️ **Automatic Guest Flagging**

- **Request Body Flag**: Automatically adds `is_guest: true` to POST/PUT request bodies
- **Option Flag**: Supports `isGuest: true` in options for explicit guest mode
- **Backend Integration**: Seamlessly integrates with backend guest handling

### 🛠️ **Guest Convenience Methods**

```javascript
// Dedicated guest methods
import { guestGet, guestPost, guestPut, guestDel } from "./http/RequestConfig";

// All automatically handle guest mode
await guestGet("public/data");
await guestPost("guest/chat", { message: "Hello" });
```

### 🌊 **Guest Streaming Support**

```javascript
import { createGuestStreamingRequest } from "./http/RequestConfig";

const guestStream = createGuestStreamingRequest("guest/chat/stream", {
  method: "POST",
  body: JSON.stringify({ message: "Stream in guest mode" }),
});
```

## Technical Implementation

### 1. **Option Detection**

```javascript
// Multiple ways to enable guest mode
const response = await post("endpoint", data, { isGuest: true });
const response = await guestPost("endpoint", data);
const response = await post("endpoint", { ...data, is_guest: true });
```

### 2. **Header Management**

```javascript
export function defaultHeaders(isGuest = false) {
  if (isGuest) {
    return {}; // No auth headers for guests
  }
  // Regular auth headers for authenticated users
}
```

### 3. **Request Processing**

- Guest detection from options or body data
- Skips token refresh attempts for guest requests
- Maintains full error handling and retry logic
- Preserves logging with guest mode indicators

### 4. **Error Handling**

- Guest requests get `AUTH_ERROR` instead of token refresh attempts
- Network errors handled identically to authenticated requests
- Clear logging distinguishes guest vs. authenticated requests

## Usage Examples

### Basic Guest Request

```javascript
import { guestPost } from "./http/RequestConfig";

try {
  const response = await guestPost("process-message-pdf", {
    message: "Hello from guest",
    chat_id: 0,
    model_type: 0,
  });
  const data = await response.json();
} catch (error) {
  if (error.type === ErrorTypes.AUTH_ERROR) {
    // Handle guest authentication limitation
    console.log("Guest mode - full features require login");
  }
}
```

### Guest Streaming Chat

```javascript
import { createGuestStreamingRequest } from "./http/RequestConfig";

const streamRequest = createGuestStreamingRequest("process-message-pdf", {
  method: "POST",
  body: JSON.stringify({
    message: "Stream chat in guest mode",
    chat_id: 0,
    is_guest: true,
  }),
});

// Handle Server-Sent Events
streamRequest.request
  .then((response) => {
    const reader = response.body.getReader();
    // Process streaming response
  })
  .catch((error) => {
    // Handle streaming errors
  });
```

## Integration Points

### Frontend Components

- Chatbot components can use `guestPost()` for guest users
- No code changes needed for existing authenticated functionality
- Gradual migration to guest-specific methods where appropriate

### Backend Compatibility

- Automatically sets `is_guest: true` flag in request bodies
- Backend can detect guest mode from request options
- Seamless integration with existing guest handling logic

## Benefits

1. **🔒 Security**: No unauthorized token usage attempts
2. **🎯 Clarity**: Clear separation between guest and authenticated requests
3. **🚀 Performance**: Skips unnecessary auth processes for guests
4. **🛡️ Robust**: Maintains full error handling and retry logic
5. **🔄 Compatible**: Fully backward compatible with existing code

## Migration Guide

### Before (Manual Guest Handling)

```javascript
const response = await post("endpoint", {
  ...data,
  is_guest: true,
});
```

### After (Dedicated Guest Methods)

```javascript
const response = await guestPost("endpoint", data);
// is_guest flag automatically added
```

The fetcher now provides a complete, robust solution for both authenticated and guest user interactions with the API!
