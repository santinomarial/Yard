# Yard API

FastAPI and SQLAlchemy service for Yard's authoritative marketplace state.

The development container uses PostgreSQL. Tests use SQLite only for fast API contract checks; transactional PostgreSQL integration tests are added with the reservation phase where database locking semantics become part of the product contract.

## Commands

```bash
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m scripts.seed
docker compose run --rm backend pytest
```

