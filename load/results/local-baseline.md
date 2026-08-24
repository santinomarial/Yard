# Local baseline — 2026-08-24

This is a local development measurement, not a production capacity, latency, uptime, or user-traffic claim.

- Host: Apple M4, arm64, 16 GiB RAM
- Runtime: Docker 29.6.2 and Docker Compose 5.3.1 on macOS
- Services: one local FastAPI container plus Docker Compose PostgreSQL 16/pgvector, Redis 7.4, MinIO, and worker
- Generator: `grafana/k6:0.54.0`, also running in Docker
- Command: `make load-benchmark`
- Workload: four browsing VUs for 30 seconds; six distinct buyers racing for one listing; two WebSocket messages/second for 20 seconds; four full listing publications across two VUs

Observed results:

- 393 HTTP requests and 166 completed scenario iterations
- HTTP failures: 0/393 (0.00%)
- Overall HTTP duration: 18.05 ms average, 39.07 ms p95, 109.42 ms maximum
- Browse: 28.91 ms average, 66.07 ms p95
- Natural-language search: 19.52 ms average, 27.57 ms p95
- Listing detail: 7.13 ms average, 9.38 ms p95
- Reservation contention: exactly one winner, five clean conflicts, zero unexpected outcomes
- WebSocket delivery: 40/40 messages; 21.68 ms average session duration, 35 ms p95
- Listing publication: 4/4 completed through draft, presigned image upload, image moderation, and submit
- Checks: 398/398 passed; every configured threshold passed

The earlier smoke run found a PostgreSQL-only `FOR UPDATE`/outer-join incompatibility in listing submission. The listing query was corrected to lock only the inventory row and a PostgreSQL regression test was added before this successful baseline was recorded.
