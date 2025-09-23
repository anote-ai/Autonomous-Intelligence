// Simple test file to verify the revamped fetcher functionality
import {
  ErrorTypes,
  get,
  post,
  put,
  del,
  guestGet,
  guestPost,
  guestPut,
  guestDel,
  updateFetcherConfig,
  getFetcherConfig,
  createStreamingRequest,
  createGuestStreamingRequest,
} from "./RequestConfig";

// Mock test scenarios
console.log("🧪 Testing revamped fetcher with guest mode...");

// Test 1: Configuration
console.log("📋 Testing configuration management...");
const originalConfig = getFetcherConfig();
console.log("Original config:", originalConfig);

updateFetcherConfig({ maxRetries: 5, timeout: 60000 });
const updatedConfig = getFetcherConfig();
console.log("Updated config:", updatedConfig);

// Test 2: Error types
console.log("🚨 Testing error types...");
console.log("Available error types:", ErrorTypes);

// Test 3: Regular convenience methods
console.log("🛠 Testing regular convenience methods...");
console.log("Regular methods available:", {
  get: typeof get,
  post: typeof post,
  put: typeof put,
  del: typeof del,
  createStreamingRequest: typeof createStreamingRequest,
});

// Test 4: Guest convenience methods
console.log("👤 Testing guest convenience methods...");
console.log("Guest methods available:", {
  guestGet: typeof guestGet,
  guestPost: typeof guestPost,
  guestPut: typeof guestPut,
  guestDel: typeof guestDel,
  createGuestStreamingRequest: typeof createGuestStreamingRequest,
});

// Test 5: Streaming request creation (mock)
console.log("🌊 Testing streaming request creation...");
try {
  const streamRequest = createStreamingRequest("test-endpoint");
  console.log("Regular streaming request created:", {
    hasRequest: !!streamRequest.request,
    hasController: !!streamRequest.controller,
    hasAbort: typeof streamRequest.abort === "function",
  });
  streamRequest.abort(); // Clean up
} catch (error) {
  console.log(
    "Streaming test failed (expected in test environment):",
    error.message
  );
}

// Test 6: Guest streaming request creation (mock)
console.log("👤🌊 Testing guest streaming request creation...");
try {
  const guestStreamRequest = createGuestStreamingRequest("test-endpoint");
  console.log("Guest streaming request created:", {
    hasRequest: !!guestStreamRequest.request,
    hasController: !!guestStreamRequest.controller,
    hasAbort: typeof guestStreamRequest.abort === "function",
  });
  guestStreamRequest.abort(); // Clean up
} catch (error) {
  console.log(
    "Guest streaming test failed (expected in test environment):",
    error.message
  );
}

console.log("✅ Fetcher tests with guest mode completed!");

const testExports = {
  ErrorTypes,
  getFetcherConfig,
  updateFetcherConfig,
  guestGet,
  guestPost,
  guestPut,
  guestDel,
  createGuestStreamingRequest,
};

export default testExports;
