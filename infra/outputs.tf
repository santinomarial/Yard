output "load_balancer_dns_name" {
  value       = module.compute.load_balancer_dns_name
  description = "DNS name for the API/admin application load balancer."
}

output "asset_bucket_name" {
  value       = module.storage.asset_bucket_name
  description = "Private listing-image bucket."
}

output "asset_base_url" {
  value       = module.storage.asset_base_url
  description = "HTTPS CloudFront base URL for approved listing photos."
}

output "asset_distribution_id" {
  value       = module.storage.asset_distribution_id
  description = "CloudFront distribution to invalidate after an exceptional asset replacement."
}

output "application_secret_arn" {
  value       = module.compute.application_secret_arn
  description = "Populate this Secrets Manager secret before starting tasks."
}

output "database_secret_arn" {
  value       = module.data.database_secret_arn
  description = "RDS-managed master credential secret."
  sensitive   = true
}
