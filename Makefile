.PHONY: help dev up down build logs shell migrate test lint format \
        seed-demo beat-schedule redis-check

# ── Default target ────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Django SaaS Kit — available make targets"
	@echo ""
	@echo "  Development"
	@echo "    make dev           First-time setup: copy .env + start stack"
	@echo "    make up            Start the Docker Compose stack (detached)"
	@echo "    make down          Stop and remove containers"
	@echo "    make build         Rebuild Docker images"
	@echo "    make logs          Tail web-service logs  (Ctrl-C to stop)"
	@echo ""
	@echo "  Django"
	@echo "    make shell         Open Django shell inside the web container"
	@echo "    make migrate       Run database migrations"
	@echo "    make seed-demo     Seed demo tenants + admin user"
	@echo ""
	@echo "  Quality"
	@echo "    make test          Run pytest (local, no Docker)"
	@echo "    make lint          ruff check + mypy"
	@echo "    make format        ruff format (auto-fix)"
	@echo ""

# ── First-time developer setup ────────────────────────────────────────────────
dev:
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")
	docker compose up --build -d
	@echo ""
	@echo "Stack is up. API: http://localhost:8000"
	@echo "Swagger UI: http://localhost:8000/api/docs/"
	@echo ""

# ── Docker Compose shortcuts ──────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f web

# ── Django management ─────────────────────────────────────────────────────────
shell:
	docker compose exec web python manage.py shell

migrate:
	docker compose exec web python manage.py migrate

seed-demo:
	docker compose exec web python manage.py seed_demo

beat-schedule:
	docker compose exec web python manage.py sync_beat_schedule

redis-check:
	docker compose exec web python manage.py shell -c \
	    "from django.core.cache import cache; cache.set('ping','pong',10); print(cache.get('ping'))"

# ── Local quality checks (no Docker needed) ───────────────────────────────────
test:
	pytest

lint:
	ruff check .
	mypy .

format:
	ruff format .
	ruff check . --fix
