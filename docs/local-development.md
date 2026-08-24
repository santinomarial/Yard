# Local development

## Requirements

- Docker Desktop with Compose v2
- Xcode 26 or later for the iOS application

No production credentials are needed for the core local marketplace.

## Start the service stack

```bash
cp .env.example .env
make dev
```

The backend migrates and seeds the database before serving requests. Local services are available at:

| Service | URL | Purpose |
| --- | --- | --- |
| Yard API | `http://localhost:8000` | FastAPI service |
| OpenAPI | `http://localhost:8000/docs` | Interactive API contract |
| Mailpit | `http://localhost:8025` | Development email capture |
| MinIO API | `http://localhost:9000` | S3-compatible storage |
| MinIO console | `http://localhost:9001` | Storage inspection |

PostgreSQL and Redis are exposed on their default local ports. Development passwords in `docker-compose.yml` are intentionally local-only and must never be reused outside local development.

## Verify

```bash
make check
curl http://localhost:8000/api/v1/health
curl 'http://localhost:8000/api/v1/listings?query=monitor'
```

`make integration-test` creates, migrates, tests, and removes a dedicated
`yard_integration_test` database. Race fixtures never share the normal `yard`
development database.

## Stop

```bash
make stop
```

Named Docker volumes preserve local data. Use `docker compose down --volumes` only when you intentionally want to discard all local Yard data.
