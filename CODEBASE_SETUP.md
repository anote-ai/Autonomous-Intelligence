# Autonomous Intelligence (Panacea) — Codebase Setup

## What is Autonomous Intelligence?

Autonomous Intelligence, also known as Panacea, is a multi-agent orchestration framework available at [chat.anote.ai](https://chat.anote.ai). It enables building, deploying, and monitoring autonomous AI agents that can reason, plan, and execute complex multi-step tasks.

## Architecture

| Layer | Technology | Location |
|-------|-----------|----------|
| Frontend | React (Node 18) | `frontend/` |
| Backend | Python 3.11, FastAPI | `backend/` |
| Container orchestration | Docker Compose | `docker-compose.yml` |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- Node 18 (only needed for manual frontend setup)
- Python 3.11 (only needed for manual backend setup)

## Quick Start with Docker Compose (RECOMMENDED)

```bash
# 1. Clone the repo
git clone https://github.com/anote-ai/Autonomous-Intelligence.git
cd Autonomous-Intelligence

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env and set required values (see Environment Variables below)

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
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Dependencies are declared in `pyproject.toml`. The `[dev]` extra includes linting and testing tools.

### Frontend

```bash
cd frontend
npm install
npm start
```

The dev server starts at `http://localhost:3000`.

## Environment Variables

Copy `.env.example` to `.env` and fill in the values.

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for agent execution |
| `ANTHROPIC_API_KEY` | No | Anthropic API key for Claude models |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | Random secret for session signing |
| `REACT_APP_BACK_END_HOST` | Yes | Backend URL seen by the browser |

## Python Dependency Management

Python dependencies live in `pyproject.toml`. To add a dependency:

```bash
# Add to [project.dependencies] or [project.optional-dependencies] in pyproject.toml
pip install -e ".[dev]"  # reinstall in editable mode to pick up changes
```

## CI/CD

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| CI workflow(s) | PR / push to main | Runs lint, type checks, and tests — blocks merging bad PRs |
| `deploy.yml` | Manual (`workflow_dispatch`) | Builds Docker image → ECR → ECS (backend); React build → S3 → CloudFront (frontend) |

### Required GitHub Secrets for Deployment

Configure these in **Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM access key with ECR/ECS/S3/CloudFront permissions |
| `AWS_SECRET_ACCESS_KEY` | Corresponding IAM secret key |
| `AWS_REGION` | AWS region (defaults to `us-east-1`) |
| `ECS_CLUSTER` | ECS cluster name |
| `ECS_SERVICE_BACKEND` | ECS service name (ECR repository: `autonomous-intelligence-backend`) |
| `S3_BUCKET_FRONTEND` | S3 bucket for the React build |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront distribution ID |
| `REACT_APP_BACK_END_HOST` | Backend URL injected at React build time |
| `SLACK_WEBHOOK_URL` | (Optional) Slack webhook for failure alerts |
