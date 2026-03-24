# Anote AI — Claude Code Guide

## Project Overview
Full-stack private document Q&A / chatbot SaaS platform. Users upload documents, ask questions via chat, and get AI-powered answers using RAG (Retrieval Augmented Generation). Supports OpenAI and Anthropic Claude as LLM providers.

## Architecture
- **Frontend:** React 18 + Redux Toolkit + Tailwind CSS — served at `localhost:3000`
- **Backend:** Python Flask + LangChain/LangGraph agents — served at `localhost:5000`
- **Database:** MySQL 8.0 (schema at [backend/database/schema.sql](backend/database/schema.sql))
- **Cache:** Redis
- **Document parsing:** Apache Tika
- **Payments:** Stripe
- **Auth:** JWT + Google OAuth

## Running the Stack

### Docker (recommended)
```bash
cp backend/.env.example backend/.env  # fill in secrets
docker compose up --build
```

| Service  | URL                    |
|----------|------------------------|
| Frontend | http://localhost:3000  |
| Backend  | http://localhost:5000  |
| MySQL    | localhost:3307         |
| Redis    | localhost:6380         |
| Tika     | http://localhost:9999  |

### Native dev
```bash
# Frontend
cd frontend && npm install && npm start

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app.py FLASK_ENV=development FLASK_DEBUG=1
flask run --host=0.0.0.0 --port=5000
```

### Makefile shortcuts
```bash
make dev-up        # start Docker containers
make dev-down      # stop Docker containers
make dev-logs      # tail Docker logs
make frontend-start
make frontend-build
make frontend-test
```

## Testing

### Backend (pytest — 92% coverage required by CI)
```bash
cd backend
pytest              # run all tests
pytest -v           # verbose
pytest --cov        # with coverage report
```

### Frontend (Vitest)
```bash
cd frontend
npm test            # watch mode
npm run test:ci     # CI mode (no watch)
npm run test:coverage
```

## Linting & Type Checking
```bash
cd backend
ruff check .        # linting
mypy .              # type checking
```

CI runs both on every push. Fix all Ruff and MyPy errors before opening a PR.

## Key Environment Variables

### Backend (`backend/.env`)
| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI LLM / embeddings |
| `ANTHROPIC_API_KEY` | Anthropic Claude LLM |
| `STRIPE_SECRET_KEY` | Stripe payments |
| `SEC_API_KEY` | SEC/finance data |
| `DB_NAME`, `DB_HOST`, `DB_USER`, `DB_PASSWORD` | MySQL connection |
| `REDIS_URL` | Redis connection |
| `PERSIST_DIRECTORY` | Vector store path |
| `MODEL_TYPE`, `MODEL_PATH` | Local LLM config |
| `EMBEDDINGS_MODEL_NAME` | Embedding model |

### Frontend (`frontend/.env.local`)
| Variable | Purpose |
|---|---|
| `REACT_APP_BACK_END_HOST` | Backend URL (default: proxied to `localhost:5000`) |

## Important Directories

### Backend
| Path | Purpose |
|---|---|
| [backend/app.py](backend/app.py) | Flask app entry point |
| [backend/api_endpoints/](backend/api_endpoints/) | Route handlers by feature |
| [backend/database/db.py](backend/database/db.py) | Database operations |
| [backend/agents/](backend/agents/) | LangChain/LangGraph agent system |
| [backend/services/](backend/services/) | Business logic (RAG, finance GPT) |
| [backend/mcp/](backend/mcp/) | MCP server definitions |
| [backend/sdk/](backend/sdk/) | Public Python SDK (`anoteai` pip package) |
| [backend/tests/](backend/tests/) | pytest test suite |

### Frontend
| Path | Purpose |
|---|---|
| [frontend/src/App.js](frontend/src/App.js) | React entry point |
| [frontend/src/app/routes.js](frontend/src/app/routes.js) | Route definitions |
| [frontend/src/components/](frontend/src/components/) | Shared UI components |
| [frontend/src/redux/](frontend/src/redux/) | Redux slices (User, Chat) |
| [frontend/src/http/RequestConfig.js](frontend/src/http/RequestConfig.js) | Axios configuration |
| [frontend/src/financeGPT/](frontend/src/financeGPT/) | Finance-specific chatbot feature |

## CI/CD
GitHub Actions ([.github/workflows/main.yml](.github/workflows/main.yml)) runs on every push:
1. Frontend build + unit tests
2. Backend: Ruff lint → MyPy type check → pytest (≥92% coverage)
3. CodeQL security analysis (Python + JavaScript)
