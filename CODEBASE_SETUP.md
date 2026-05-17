# Autonomous Intelligence (Panacea) — Codebase Setup

## What is Autonomous Intelligence?

Autonomous Intelligence, also known as **Panacea**, is a multi-agent orchestration framework hosted at [chat.anote.ai](https://chat.anote.ai). It coordinates multiple AI agents to autonomously complete complex, multi-step tasks.

## Architecture

| Layer | Technology | Location |
|-------|-----------|----------|
| Frontend | React (Create React App) | `frontend/` |
| Backend | Python 3.11, FastAPI | `backend/` |
| Container orchestration | Docker Compose | `docker-compose.yml` |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (recommended path)
- Node 18+ (manual frontend setup)
- Python 3.11+ (manual backend setup)

## Quick Start with Docker Compose (RECOMMENDED)

```bash
# 1. Clone the repo
git clone https://github.com/anote-ai/Autonomous-Intelligence.git
cd Autonomous-Intelligence

# 2. Create your local env file and fill in values
cp .env.example .env

# 3. Start all services
docker-compose up --build

# 4. Open the app
open http://localhost:3000
```

The backend API will be available at `http://localhost:8000`.

## Manual Setup (without Docker)

### Backend

```bash
cd backend
pip install -e ".[dev]"
uvicorn app:app --reload --port 8000
```

Dependencies are declared in `pyproject.toml` at the repo root. The `[dev]` extra includes linters and test tools.

### Frontend

```bash
cd frontend
npm install
npm start   # starts on http://localhost:3000
```

## Environment Variables

Copy `.env.example` to `.env` and set the following:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for agent LLM calls |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude-based agents |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Random secret used for JWT signing |
| `REACT_APP_BACK_END_HOST` | Backend URL consumed by the React app |

## Dependency Management

Python dependencies are managed via `pyproject.toml` (PEP 517/518). Install everything including dev tools with:

```bash
pip install -e ".[dev]"
```

## CI / CD

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| CI workflow(s) | Pull request | Runs lint, type-check, and tests — blocks merge on failure |
| `deploy.yml` | Manual (`workflow_dispatch`) | Builds Docker image (ECR repository: `autonomous-intelligence-backend`) → pushes to ECR → updates ECS; syncs frontend to S3 and invalidates CloudFront |

### Required GitHub Secrets for Deployment

Set these in **Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM access key with ECS/ECR/S3/CloudFront permissions |
| `AWS_SECRET_ACCESS_KEY` | Corresponding IAM secret |
| `AWS_REGION` | AWS region, e.g. `us-east-1` |
| `ECS_CLUSTER` | Name of the ECS cluster |
| `ECS_SERVICE_BACKEND` | Name of the ECS service for the backend |
| `S3_BUCKET_FRONTEND` | S3 bucket name for the frontend static files |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront distribution ID to invalidate after deploy |
| `REACT_APP_BACK_END_HOST` | Backend URL injected at React build time |
| `SLACK_WEBHOOK_URL` | (Optional) Slack incoming webhook for failure notifications |
