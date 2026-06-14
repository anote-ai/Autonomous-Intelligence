# Autonomous Intelligence (Panacea) — Codebase Setup

## What is Autonomous Intelligence?

Autonomous Intelligence, also known as **Panacea**, is a multi-agent orchestration framework hosted at [chat.anote.ai](https://chat.anote.ai). It coordinates multiple AI agents to autonomously complete complex, multi-step tasks.

## Architecture

| Layer | Technology | Location |
|-------|-----------|----------|
| Frontend | React (Create React App) | `frontend/` |
| Backend | Python 3.11, **Flask** | `backend/` |
| Database | **MySQL 8.0** | schema in `backend/database/schema.sql` |
| Container orchestration | Docker Compose | `docker-compose.yml` (default) · `docker-compose.local.yml` (host-port-shifted) |

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

# 3. Start all services (default: frontend :3000, backend :5000)
docker-compose up --build

#    macOS note: port 5000 is often taken by AirPlay Receiver / Control Center.
#    Use the local override, which maps frontend :3001 and backend :5001:
docker-compose -f docker-compose.local.yml up --build

# 4. Open the app
open http://localhost:3000     # or http://localhost:3001 with the .local override
```

The backend API is available at `http://localhost:5000` (`:5001` with the `.local` override); health check at `/health`.

## Manual Setup (without Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
flask --app app run --port 5000        # Flask app (FLASK_APP=app.py)
```

Runtime dependencies are in `backend/requirements.txt`. Lint/type/test tooling (ruff, mypy, pytest) is configured in the repo-root `pyproject.toml`.

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
| MySQL settings | DB is **MySQL 8.0** (not Postgres); connection is provided by the compose files locally and read in `backend/database/db_pool.py` |
| `SECRET_KEY` | Random secret used for JWT signing |
| `REACT_APP_BACK_END_HOST` | Backend URL consumed by the React app |

## Dependency Management

Runtime Python dependencies are in `backend/requirements.txt`; lint/type/test tooling (ruff, mypy, pytest) is configured in the repo-root `pyproject.toml`. Install the backend deps with:

```bash
pip install -r backend/requirements.txt
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
