output "database_secret_arn" {
  value     = aws_db_instance.postgres.master_user_secret[0].secret_arn
  sensitive = true
}

output "redis_url" {
  value = "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"
}
