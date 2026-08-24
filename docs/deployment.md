# Deployment

Yard’s production target is AWS ECS/Fargate with RDS PostgreSQL/pgvector, ElastiCache Redis, private S3 behind CloudFront Origin Access Control, SES, Rekognition, CloudWatch, and Secrets Manager. Terraform describes resources but never applies them automatically.

## Prerequisites

1. Own the API, admin, asset, support, privacy, terms, and associated-link domains.
2. Create an AWS account/role and an encrypted remote Terraform backend with state locking.
3. Build immutable backend/worker/admin images and push their digests to ECR.
4. Issue an ACM certificate for the public ALB domain and configure DNS.
5. Verify the SES sender and production access; create Rekognition permissions.
6. Create Apple Developer identifiers, associated domains, an APNs `.p8` key, and App Store Connect records.

## Apply and initialize

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan -out yard.tfplan
terraform apply yard.tfplan
```

Populate the created application secret JSON with `database_url`, strong independent `access_token_secret` and `verification_pepper`, and the APNs team/key/private-key values. Run `alembic upgrade head` as a one-off task, run the seed only in non-production environments, then start API/worker/admin services and verify `/ready`, `/metrics`, and structured logs.

## Domains and iOS links

Set the Release `YARD_API_BASE_URL` and admin build-time API URL to owned HTTPS domains. Replace the associated-domain placeholder in `Yard-Release.entitlements`. Host an `apple-app-site-association` file on the web domain that maps the application identifier to `/listing/*`, `/conversation/*`, and `/reservation/*`; retain the custom `yard://` scheme as a fallback. Replace support and policy placeholder URLs/email before review.

## Release verification

- Restore a production-like RDS snapshot into staging and run migrations.
- Upload, moderate, publish, and read an approved photo through CloudFront; verify rejected objects are never serialized.
- Deliver a real verification email and APNs notification, including deep-link behavior.
- Run reservation/bundle races against staging PostgreSQL and the k6 smoke suite through the load balancer.
- Exercise report, takedown, suspension, deletion, secret rotation, backup restore, and rollback runbooks.
- Enable alarms for task health, ALB errors/latency, database capacity, job failures, moderation backlog, and notification failures.

The default topology uses one NAT gateway, a small single-AZ database, and one task per service. It is appropriate for a controlled beta, not a high-availability launch claim. Cost and resilience changes are detailed in [the infrastructure README](../infra/README.md).
