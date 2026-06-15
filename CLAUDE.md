# Anote AI — Claude Code Guide

## Project Overview

**Anote Autonomous Intelligence** is a unified AI assistant monorepo combining:
- A coding CLI tool
- A VS Code extension
- A web chatbot
- A mobile app (Expo)
- A private desktop app (Electron)
- A Python SDK
- A shared Python Flask backend
- MkDocs documentation

## Repository Structure

```
Autonomous-Intelligence/
├── packages/
│   ├── backend/        # Python Flask API (shared by all frontends)
│   ├── cli/            # TypeScript CLI tool (anote command)
│   ├── sdk/            # TypeScript SDK (@anote-ai/sdk)
│   ├── vscode/         # VS Code extension
│   ├── web/            # React web chatbot (Vite + Tailwind)
│   ├── mobile/         # Expo React Native app
│   ├── desktop/        # Electron private desktop app
│   └── docs/           # MkDocs Material documentation
├── package.json        # npm workspaces root
├── tsconfig.base.json  # Shared TypeScript config
├── Makefile            # Dev convenience commands
├── docker-compose.yml  # Full stack (MySQL, Redis, Tika, backend, web)
└── .github/workflows/ci.yml  # 4-job CI pipeline
```

## Architecture

- **Backend**: Flask 2 + JWT + Anthropic/OpenAI + ChromaDB + LangChain — `localhost:5000`
- **Web**: React 18 + Vite + Tailwind CSS (ChatGPT-style light/dark mode) — `localhost:3000`
- **Mobile**: Expo 51 + React Native with Expo Router
- **Desktop**: Electron 28 wrapping a React frontend + bundled Python backend (PyInstaller)
- **CLI**: TypeScript Commander CLI with 23 commands, TF-IDF search, multi-provider
- **VS Code**: Extension with chat sidebar, diff review, streaming responses
- **SDK**: TypeScript client for the backend API
- **Docs**: MkDocs Material at `packages/docs/`

## UI Design

All frontends (web, mobile, desktop) follow a ChatGPT-style design:
- **Light mode**: white (`#FFFFFF`) / light gray (`#F7F7F8`) backgrounds, black text
- **Dark mode**: black (`#212121`) / dark gray (`#2F2F2F`) backgrounds, white text
- **Rocket logo**: white body + light gray accent in dark mode; black body + dark gray accent in light mode
- Toggle button in header/toolbar

## Development

### Docker (recommended for full stack)
```bash
cp packages/backend/.env.example packages/backend/.env
docker compose up
```

Services: web → `localhost:3000`, backend → `localhost:5000`, MySQL → `3306`, Redis → `6379`

### Individual packages
```bash
make dev-backend   # Flask on :5000
make dev-web       # React/Vite on :3000
make dev           # Both in parallel
npm start --workspace=packages/cli  # CLI dev
code packages/vscode                # VS Code extension (F5 to launch)
```

### Makefile shortcuts
```bash
make dev           # backend + web
make dev-backend   # Flask only
make dev-web       # Vite only
make backend-test  # pytest
make build         # build all packages
make docs-serve    # mkdocs serve
make desktop-dev   # Electron dev mode
make desktop-build # Package desktop app
```

## Testing & Quality

### Backend (Python)
```bash
cd packages/backend
pytest tests/ -v --cov=. --cov-fail-under=80
```
- 80% coverage gate enforced in CI
- Tests use Flask test client (no MySQL required)
- Linting: `ruff check .`
- Type checking: `mypy . --ignore-missing-imports`

### TypeScript
```bash
npm test            # all workspaces
npm test --workspace=packages/cli
```

## CI/CD

Single workflow: `.github/workflows/ci.yml`  
Triggers on every push and PR to main.  
4 parallel jobs:
1. **Backend** — ruff → mypy → pytest (80% gate)
2. **TypeScript** — build + test all TS packages
3. **VS Code** — build extension
4. **Docs** — mkdocs build --strict

## Backend API Endpoints

| Blueprint | Prefix | Description |
|-----------|--------|-------------|
| auth | `/auth` | register, login, refresh, me |
| chat | `/api/chat` | stream, sessions CRUD |
| documents | `/api/documents` | upload, list, get, delete, ask |
| search | `/api/search` | TF-IDF codebase search |
| user | `/api/user` | profile, API keys |
| payments | `/api/payments` | Stripe checkout/portal/webhook |
| workspaces | `/api/workspaces` | hosted-mode workspace management |

## Environment Variables

Copy `packages/backend/.env.example` → `packages/backend/.env`:

| Variable | Purpose |
|---|---|
| `JWT_SECRET_KEY` | JWT signing |
| `ANTHROPIC_API_KEY` | Claude LLM |
| `OPENAI_API_KEY` | GPT / embeddings |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | MySQL |
| `STRIPE_SECRET_KEY` | Payments (optional) |
| `APP_ENV` | `local` / `test` / `production` |

## Key Docs

- `packages/docs/` — Full MkDocs Material documentation site
- `packages/backend/README.md` — Backend-specific guide
- `CODEBASE_SETUP.md` — Full installation walkthrough

## Source Repositories (preserved, not deleted)

This monorepo consolidates:
- `anote-ai/AI-Assisted-Coding-Tool` → `packages/cli/`, `packages/sdk/`, `packages/vscode/`
- `anote-ai/Autonomous-Intelligence` (original) → `packages/backend/`, `packages/web/`
- `anote-ai/PrivateGPT` → `packages/desktop/`
