# Load and reliability testing

The k6 suite exercises anonymous browsing, natural-language search, listing detail, a real PostgreSQL row-lock race between six distinct verified buyers, WebSocket chat delivery, and the complete listing/image/moderation publication path.

Run it only against a disposable development database. It creates fictional `@harvard.edu` verification fixtures and published lamp listings; the fixture identity option is unavailable outside `YARD_ENVIRONMENT=development`.

```bash
docker compose up -d --build backend worker
make load-smoke
make load-benchmark
```

The Docker command uses `host.docker.internal` so k6 can reach the API and presigned MinIO uploads on macOS. Override `YARD_BASE_URL` when running k6 directly. Delete the local Docker volumes if you want a pristine dataset after benchmarking.

## Recorded local benchmark

The committed benchmark record is generated on a developer workstation against the Docker Compose PostgreSQL, Redis, MinIO, API, and worker services. It is a local correctness/bottleneck check, not a production traffic, latency, capacity, or uptime claim. See `results/local-baseline.md` for the date, command, hardware-visible conditions, thresholds, and observed values.
