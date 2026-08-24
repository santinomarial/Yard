output "asset_bucket_name" { value = aws_s3_bucket.assets.id }
output "asset_bucket_arn" { value = aws_s3_bucket.assets.arn }
output "asset_base_url" { value = "https://${aws_cloudfront_distribution.assets.domain_name}" }
output "asset_distribution_id" { value = aws_cloudfront_distribution.assets.id }
