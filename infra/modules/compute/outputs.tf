output "load_balancer_dns_name" { value = aws_lb.this.dns_name }
output "application_secret_arn" { value = aws_secretsmanager_secret.application.arn }
