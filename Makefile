COMPOSE = docker compose

.PHONY: dev-up dev-down dev-logs frontend-install frontend-start frontend-build frontend-test

dev-up:
	$(COMPOSE) up --build

dev-down:
	$(COMPOSE) down --remove-orphans

dev-logs:
	$(COMPOSE) logs -f

frontend-install:
	cd frontend && npm install

frontend-start:
	cd frontend && npm start

frontend-build:
	cd frontend && npm run build

frontend-test:
	cd frontend && CI=true npx react-scripts test --runInBand --watch=false
