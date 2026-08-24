# Yard

> A native campus marketplace that makes buying and selling within the Harvard community fast, trusted, and local.

Yard is an independent marketplace for members of the Harvard community to discover, reserve, and exchange useful items nearby. It is designed around fast listing creation, campus-specific trust, privacy-aware pickup coordination, and server-authoritative inventory.

> Yard is an independent community marketplace and is not affiliated with or endorsed by Harvard University.

## Project status

Yard is under active development. No production usage, reliability, or marketplace metrics are claimed. The implementation is being delivered in runnable vertical slices; see [the delivery plan](docs/delivery-plan.md) for current scope.

## Repository

This monorepo will contain:

- `ios/` — the native SwiftUI application
- `backend/` — the FastAPI service and background worker
- `admin/` — the moderation console
- `infra/` — deployment infrastructure
- `scripts/` — development and evaluation tools
- `docs/` — architecture, operations, privacy, and release documentation

## Local setup

Docker is the only requirement for the backend development stack:

```bash
cp .env.example .env
make dev
```

The API is then available at `http://localhost:8000`, interactive OpenAPI documentation at `http://localhost:8000/docs`, and the moderation console at `http://localhost:3000`. See [local development](docs/local-development.md) for service URLs and verification commands.

## Testing

```bash
make check
```

This runs backend and admin linting, formatting validation, strict type checking, tests, and the admin production build. Native iOS build and test commands are documented alongside the iOS project.

## Product principles

- Keep the buying and selling experience immediately understandable.
- Put transactional rigor behind scarce inventory actions.
- Treat community verification, privacy, reporting, and moderation as product fundamentals.
- Keep local workflows useful while making authoritative mutations explicit.
- Measure real marketplace outcomes without fabricating metrics.
