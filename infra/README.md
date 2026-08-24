# Yard AWS infrastructure

This Terraform describes a small production deployment without creating anything automatically. It uses two availability zones, ECS/Fargate for the API, worker, and admin site, RDS PostgreSQL 16, encrypted ElastiCache Redis, a private S3 asset bucket behind CloudFront Origin Access Control, Rekognition/SES IAM permissions, CloudWatch logs, and Secrets Manager.

## Before applying

1. Build and push immutable API, worker, and admin images to ECR. Build the admin image with `NEXT_PUBLIC_YARD_API_URL` set to the public HTTPS API `/api/v1` URL because browser-visible Next.js variables are compiled into the image.
2. Verify the SES sender identity and request production SES access if needed.
3. Copy `terraform.tfvars.example` to an untracked `terraform.tfvars` and pin the image digests.
4. Supply an ACM certificate. The HTTP-only listener is intended only for initial bootstrap; production clients must use HTTPS.
5. Run `terraform init`, `terraform plan -out yard.tfplan`, review the full plan, then explicitly run `terraform apply yard.tfplan`.
6. Read the RDS-managed credential secret and populate the application Secrets Manager value with a JSON object containing `database_url`, strong `access_token_secret` and `verification_pepper` values, plus `apns_team_id`, `apns_key_id`, and `apns_private_key`. The ECS task definition injects individual JSON keys as environment variables; secret values never enter Terraform state.
7. Run `alembic upgrade head` as a one-off ECS task before shifting traffic.

Terraform state must live in a separately bootstrapped encrypted remote backend with locking. Commit the provider lock file, but never commit state, variable files, plan files, APNs keys, or exported secrets.

## Low-traffic deployment considerations

The defaults prioritize a student-project budget: one small task per service, a `db.t4g.micro` database, a single Redis node, one NAT gateway, and no multi-AZ database. That is suitable for controlled beta traffic, not a high-availability claim. For launch, budget for database Multi-AZ, a second NAT gateway, Redis failover, ECS autoscaling, AWS WAF, alarms, and tested restore/runbook procedures. Cost varies by region and usage; review the AWS pricing calculator before applying.

The asset bucket remains private. ECS task-role credentials issue direct signed uploads, while approved-photo URLs use the CloudFront distribution. CloudFront is the only public read path and receives `s3:GetObject` through a source-ARN-constrained bucket policy; rejected or pending images are never returned by the API. The default distribution hostname is sufficient for initial deployment, and an ACM-backed custom asset domain can be added later without changing object keys.
