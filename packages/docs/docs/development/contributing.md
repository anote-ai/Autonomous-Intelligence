# Contributing

## Setup

```bash
git clone https://github.com/anote-ai/Autonomous-Intelligence
cd Autonomous-Intelligence

# Install Node.js packages
npm install

# Set up Python backend
cd packages/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys

# Start everything
cd ../.. 
docker compose up
```

## Development Workflow

1. Create a feature branch from `main`
2. Make your changes in the relevant `packages/` directory
3. Run tests: `make test`
4. Run linters: `make lint`
5. Open a pull request

## Testing

```bash
# All tests
make test

# Backend only
make test-backend

# TypeScript only
make test-ts
```

## Code Standards

### Python (backend)
- **Ruff** for linting (`ruff check .`)
- **Mypy** for type checking (`mypy .`)
- **Pytest** for tests (≥80% coverage)
- Type-annotate all new functions

### TypeScript (frontend/cli/sdk)
- **ESLint** for linting
- **Vitest** or **Jest** for tests
- Strict TypeScript (`"strict": true`)

## CI

GitHub Actions runs on every push:
1. Backend: ruff → mypy → pytest (80% coverage gate)
2. TypeScript: build → tests
3. VS Code: build extension
4. Docs: build MkDocs site
