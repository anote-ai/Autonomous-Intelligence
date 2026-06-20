# Architecture

## Monorepo Structure

```
panacea/
├── packages/
│   ├── backend/    # Python Flask — unified API + agent streaming + RAG
│   ├── cli/        # TypeScript — anote terminal CLI
│   ├── vscode/     # TypeScript — VS Code extension
│   ├── web/        # TypeScript/React — browser chatbot app
│   ├── mobile/     # TypeScript/React Native (Expo) — iOS + Android
│   ├── desktop/    # TypeScript/Electron — private desktop app
│   ├── sdk/        # TypeScript — JS/TS client SDK
│   └── docs/       # MkDocs Material — documentation site
├── docker-compose.yml
├── package.json    # npm workspaces
└── Makefile
```

## Backend Architecture

The Python Flask backend handles all server-side logic:

```
packages/backend/
├── app.py                    # Flask entry point, route registration
├── api_endpoints/
│   ├── chat/                 # Agent streaming (SSE), session management
│   ├── documents/            # Upload, RAG pipeline, Q&A
│   ├── search/               # Semantic search index queries
│   ├── auth/                 # JWT, Google OAuth
│   ├── user/                 # Profile, settings
│   └── payments/             # Stripe webhooks + checkout
├── agents/                   # LangChain/LangGraph agent definitions
├── services/
│   ├── rag.py                # Document chunking + Chroma embeddings
│   ├── streaming.py          # SSE streaming to Claude/OpenAI/Gemini
│   └── search.py             # TF-IDF semantic search
├── database/
│   ├── db.py                 # MySQL connection + queries
│   └── schema.sql            # Database schema
└── models/                   # LLM provider wrappers
```

## Data Flow: Agent Chat

```
Client (CLI / VS Code / Web / Mobile)
    │  POST /api/chat/stream {message, cwd, model}
    ▼
Flask Backend (app.py → chat/handler.py)
    │  SSE stream
    ▼
LLM Provider (Anthropic / OpenAI / Gemini / Ollama)
    │  tool calls ↔ execute (Read/Write/Edit/Bash/Glob/Grep)
    ▼
Filesystem (cwd) + Chroma (RAG context)
```

## Technology Choices

| Layer | Technology | Why |
|---|---|---|
| Backend | Python Flask | Rich ML/AI ecosystem, existing agents |
| Agent streaming | Anthropic Python SDK | Native SSE, tool use |
| Vector DB | ChromaDB | Local-first, no infra needed |
| Database | MySQL | ACID, existing schema |
| Cache | Redis | Session + rate limiting |
| Frontend | React 18 + TypeScript | Type safety, ecosystem |
| Desktop | Electron | Cross-platform, bundles Python |
| Mobile | Expo (React Native) | Code sharing with web |
| CLI | Commander.js | Mature, TypeScript-friendly |
| Docs | MkDocs Material | Beautiful, fast, markdown |
