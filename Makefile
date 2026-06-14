.PHONY: dev dev-backend dev-frontend dev-cli build test lint docker-up docker-down docs

# ── Development ────────────────────────────────────────────────────────────────

dev: docker-up

dev-backend:
	cd packages/backend && python -m uvicorn app:app --reload --port 5000 2>/dev/null || \
	cd packages/backend && python app.py

dev-frontend:
	cd packages/web && npm start

dev-cli:
	cd packages/cli && npm run build:watch

# ── Build ──────────────────────────────────────────────────────────────────────

build:
	npm run build --workspaces

build-backend:
	cd packages/backend && pip install -r requirements.txt

# ── Test ───────────────────────────────────────────────────────────────────────

test: test-backend test-ts

test-backend:
	cd packages/backend && python -m pytest tests/ -v --cov=. --cov-report=term-missing

test-ts:
	npm run test --workspaces --if-present

# ── Lint ───────────────────────────────────────────────────────────────────────

lint: lint-backend lint-ts

lint-backend:
	cd packages/backend && ruff check . && mypy .

lint-ts:
	npm run lint --workspaces --if-present

# ── Docker ─────────────────────────────────────────────────────────────────────

docker-up:
	docker compose up

docker-up-d:
	docker compose up -d

docker-down:
	docker compose down

docker-rebuild:
	docker compose up --build

# ── Docs ───────────────────────────────────────────────────────────────────────

docs:
	cd packages/docs && mkdocs serve

docs-build:
	cd packages/docs && mkdocs build

docs-deploy:
	cd packages/docs && mkdocs gh-deploy

# ── Desktop ────────────────────────────────────────────────────────────────────

desktop-dev:
	cd packages/desktop && npm start

desktop-build:
	cd packages/desktop && npm run make
