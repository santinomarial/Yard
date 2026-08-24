.DEFAULT_GOAL := help

.PHONY: help dev dev-detached stop logs migrate seed test integration-test lint format typecheck admin-check check

help:
	@echo "Yard development commands"
	@echo "  make dev           Start the local stack in the foreground"
	@echo "  make dev-detached  Start the local stack in the background"
	@echo "  make stop          Stop local services"
	@echo "  make test          Run backend tests"
	@echo "  make check         Run backend and admin validation"
	@echo "  make admin-check   Run admin lint, types, tests, and production build"

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
	docker compose run --rm --no-deps backend python -m pytest -q

integration-test:
	docker compose run --rm -e PYTEST_ADDOPTS= backend python -m pytest -q -p no:cacheprovider -m integration

lint:
	docker compose run --rm --no-deps backend ruff check .

format:
	docker compose run --rm --no-deps backend ruff format .

typecheck:
	docker compose run --rm --no-deps backend mypy app

admin-check:
	docker run --rm -v "$(CURDIR)/admin:/app" -w /app node:22-alpine sh -c "npm ci && npm run lint && npm run typecheck && npm test && npm run build"

check:
	docker compose build backend
	docker compose run --rm --no-deps backend ruff check .
	docker compose run --rm --no-deps backend ruff format --check .
	docker compose run --rm --no-deps backend mypy app
	docker compose run --rm --no-deps backend python -m pytest -q
	$(MAKE) admin-check
