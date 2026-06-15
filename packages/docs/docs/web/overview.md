# Web App Overview

The Anote AI web app is a ChatGPT-style chat interface that connects to the Anote backend.

## Features

- Light and dark mode (auto-detects system preference)
- Streaming responses via SSE
- Chat session history in a collapsible sidebar
- Model selector (Claude, GPT-4o, etc.)
- Document upload and Q&A
- Responsive design

## Running Locally

```bash
cd packages/web
npm install
npm run dev
```

The app runs at `http://localhost:3000` and proxies API calls to `http://localhost:5000`.
