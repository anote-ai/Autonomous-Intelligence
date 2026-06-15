# TypeScript SDK

The `@anote-ai/sdk` package provides a typed client for the Anote backend API.

## Installation

```bash
npm install @anote-ai/sdk
```

## Usage

```typescript
import AnoteClient from '@anote-ai/sdk';

const client = new AnoteClient({
  baseUrl: 'https://api.anote.ai',
  apiKey: 'your-api-key',
});

// Chat
const response = await client.chat({
  message: 'Explain this codebase',
  model: 'claude-sonnet-4-6',
});

// Search
const results = await client.search({ query: 'authentication logic', cwd: '.' });

// Health check
const health = await client.health();
```

## API Reference

| Method | Description |
|--------|-------------|
| `chat(options)` | Send a chat message |
| `listSessions()` | List chat sessions |
| `getSessionMessages(id)` | Get messages in a session |
| `deleteSession(id)` | Delete a session |
| `search(options)` | Search the codebase index |
| `getUsage()` | Get API usage stats |
| `health()` | Health check |
