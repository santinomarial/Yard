.DEFAULT_GOAL := help

.PHONY: help dev dev-detached stop logs migrate seed test lint format typecheck check

help:
	@echo "Yard development commands"
	@echo "  make dev           Start the local stack in the foreground"
	@echo "  make dev-detached  Start the local stack in the background"
	@echo "  make stop          Stop local services"
	@echo "  make test          Run backend tests"
	@echo "  make check         Run backend lint, format, types, and tests"

dev:
	docker compose up --build

dev-detached:
	docker compose up --build --detach

stop:
	docker compose down

logs:
	docker compose logs --follow backend

migrate:
	docker compose run --rm backend alembic upgrade head

seed:
	docker compose run --rm backend python -m scripts.seed

test:
	docker compose run --rm --no-deps backend pytest -q

lint:
	docker compose run --rm --no-deps backend ruff check .

format:
	docker compose run --rm --no-deps backend ruff format .

typecheck:
	docker compose run --rm --no-deps backend mypy app

check:
	docker compose build backend
	docker compose run --rm --no-deps backend ruff check .
	docker compose run --rm --no-deps backend ruff format --check .
	docker compose run --rm --no-deps backend mypy app
	docker compose run --rm --no-deps backend pytest -q

