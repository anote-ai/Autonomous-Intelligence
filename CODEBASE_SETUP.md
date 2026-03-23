# Codebase Development Environment

## Quick Start

There are now two supported local development paths:

1. Docker for the full app stack
2. Native frontend + native backend for faster iteration

The Docker path is the easiest way to get the app, database, Redis, and Tika running together.

## Option 1: Full Stack with Docker

Prerequisites:

- Docker Desktop

Setup:

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5000`
- MySQL: `localhost:3307`
- Redis: `localhost:6380`
- Tika: `http://localhost:9999`

Helpful commands:

```bash
make dev-up
make dev-down
make dev-logs
```

Notes:

- The root [`docker-compose.yml`](/Users/natanvidra/Workspace/Autonomous-Intelligence/docker-compose.yml) is the preferred Docker entry point.
- The frontend container uses `REACT_APP_BACK_END_HOST=http://localhost:5000`, so the browser talks to the backend directly on the host-mapped port.
- If you need credentials or API keys, populate them in `backend/.env`.

## Option 2: Native Local Development

### Frontend

Prerequisites:

- Node 20 recommended

Setup:

```bash
cd frontend
cp .env.example .env.local
npm install
npm start
```

The frontend will run at `http://localhost:3000`.

If `REACT_APP_BACK_END_HOST` is omitted, the frontend client now supports same-origin/proxy mode. With the current `package.json` proxy, local `npm start` expects the backend at `http://localhost:5000`.

### Backend

Prerequisites:

- Python 3.10 recommended
- MySQL
- JDK 8+ for Apache Tika workflows

Setup:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1
flask run --host=0.0.0.0 --port=5000
```

### MySQL

Create the database:

```bash
mysql -u root -p
create database agents;
```

Initialize schema:

```bash
cd backend/database
python init_db_dev.py
```

## Running Tests

Frontend build:

```bash
cd frontend
npm run build
```

Frontend tests:

```bash
cd frontend
npm run test:ci
```

Backend tests:

```bash
cd backend
pytest
```

## Common Issues

- If `vitest` fails locally with Node 16 errors, upgrade to Node 18+ or use the CRA/Jest runner shown above.
- If the frontend cannot reach the backend, confirm the backend is actually listening on `http://localhost:5000`.
- If Docker healthchecks fail, verify `backend/.env` exists and MySQL finished initializing.
- The backend container healthcheck relies on `curl`, which is now installed in the backend image.
- Tika is started as a dependency, but the backend no longer waits on a brittle container-local Tika healthcheck.
- If file upload flows fail, verify Tika is running.
