.PHONY: help dev up down build logs shell migrate seed-demo beat-schedule redis-check test lint

help:
	@echo "Available commands:"
	@echo "  make dev      - First-time setup: .env + Docker stack (recommended)"
	@echo "  make up       - Start local Docker stack"
	@echo "  make down     - Stop local Docker stack"
	@echo "  make build    - Build Docker images"
	@echo "  make logs     - Tail web service logs"
	@echo "  make shell    - Open Django shell in web container"
	@echo "  make migrate  - Run database migrations"
	@echo "  make seed-demo - Seed demo tenants and admin user"
	@echo "  make beat-schedule - Register Celery Beat periodic tasks in DB"
	@echo "  make redis-check   - Verify Redis via Django cache"
	@echo "  make test     - Run pytest locally"
	@echo "  make lint     - Run ruff and mypy"

dev:
	@test -f .env || cp .env.example .env
	docker compose up -d --build
	@echo ""
	@echo "Django SaaS Kit is starting (migrations run on container boot)."
	@echo "  Health:  http://localhost:8000/health/"
	@echo "  Swagger: http://localhost:8000/api/docs/"
	@echo "  Optional demo data: make seed-demo"

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f web

shell:
	docker compose exec web python manage.py shell

migrate:
	docker compose exec web python manage.py migrate

seed-demo:
	docker compose exec web python manage.py seed_demo

beat-schedule:
	docker compose exec web python manage.py sync_beat_schedule

redis-check:
	docker compose exec web python manage.py check_redis

test:
	pytest -v

lint:
	ruff check .
	ruff format --check .
	mypy .
