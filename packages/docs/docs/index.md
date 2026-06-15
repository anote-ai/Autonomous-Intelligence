# Anote AI

**Anote AI** is a unified AI coding assistant and private chatbot platform. It ships as:

- **CLI** — `anote` command for your terminal
- **VS Code Extension** — inline AI assistance in your editor  
- **Web App** — browser-based chatbot with document RAG
- **Desktop App** — private, offline-capable Electron app
- **Mobile App** — iOS and Android chatbot
- **SDK** — TypeScript and Python clients

## Quick Start

```bash
# Install the CLI
npm install -g @anote-ai/anote

# Authenticate
anote init

# Ask a question about your code
anote ask "explain this codebase"

# Index for semantic search
anote index && anote search "authentication middleware"
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Client Surfaces                     │
│  CLI │ VS Code │ Web │ Desktop │ Mobile │ SDK        │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP / SSE / WebSocket
┌───────────────────────▼─────────────────────────────┐
│              Unified Flask Backend                   │
│  Agent Chat │ RAG │ Auth │ Documents │ Search        │
└─────────────────────────────────────────────────────┘
         │              │              │
    ┌────▼───┐    ┌─────▼──┐    ┌─────▼──┐
    │ MySQL  │    │ Redis  │    │Chroma  │
    └────────┘    └────────┘    └────────┘
```

## Features

| Feature | CLI | VS Code | Web | Desktop | Mobile |
|---------|-----|---------|-----|---------|--------|
| AI Chat | ✓ | ✓ | ✓ | ✓ | ✓ |
| Codebase Search | ✓ | ✓ | | | |
| Document RAG | | | ✓ | ✓ | |
| Local Models (Ollama) | ✓ | ✓ | | ✓ | |
| Offline Mode | | | | ✓ | |
| PR Review | ✓ | | | | |
| Auto-fix loop | ✓ | | | | |

## Supported LLM Providers

- **Anthropic** Claude (claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5)
- **OpenAI** GPT-4o, GPT-4o-mini
- **Google** Gemini 2.0 Flash, Gemini 1.5 Pro
- **Ollama** — any local model (Llama3, Mistral, etc.)
- **xAI** Grok
