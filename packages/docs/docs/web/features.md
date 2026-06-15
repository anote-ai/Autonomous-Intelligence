# Web App Features

## Chat Interface

The main chat view mirrors ChatGPT's design: a collapsible left sidebar with session history, and a centered message thread with a bottom input bar.

## Light / Dark Mode

Toggle with the button in the top-right. Preference is persisted in `localStorage`.

- **Light**: white/light-gray backgrounds, black text
- **Dark**: `#212121`/`#2F2F2F` backgrounds, white text

## Streaming

The input sends a `POST /api/chat/stream` request and reads the SSE response. A stop button aborts mid-stream.

## Sessions

Each conversation is a session stored server-side. Sessions are listed in the sidebar and persist across page loads.
