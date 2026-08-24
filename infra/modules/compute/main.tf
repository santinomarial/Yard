resource "aws_ecs_cluster" "this" {
  name = var.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.name}"
  retention_in_days = 30
}

resource "aws_secretsmanager_secret" "application" {
  name                    = "${var.name}/application"
  recovery_window_in_days = 7
  description             = "Populate JSON keys database_url, access_token_secret, verification_pepper, apns_team_id, apns_key_id, and apns_private_key."
}

resource "aws_iam_role" "execution" {
  name = "${var.name}-execution"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.application.arn]
    }]
  })
}

resource "aws_iam_role" "task" {
  name = "${var.name}-task"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "task" {
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = ["${var.asset_bucket_arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["rekognition:DetectModerationLabels", "ses:SendEmail"]
        Resource = "*"
      }
    ]
  })
}

locals {
  environment = [
    { name = "YARD_ENVIRONMENT", value = "production" },
    { name = "YARD_REDIS_URL", value = var.redis_url },
    { name = "YARD_S3_BUCKET", value = var.asset_bucket_name },
    { name = "YARD_S3_REGION", value = var.aws_region },
    { name = "YARD_ASSET_BASE_URL", value = var.asset_base_url },
    { name = "YARD_APPLE_AUDIENCE", value = var.apple_audience },
    { name = "YARD_CORS_ORIGINS", value = jsonencode(var.cors_origins) },
    { name = "YARD_SES_FROM_EMAIL", value = var.ses_from_email }
  ]
  secrets = [
    { name = "YARD_DATABASE_URL", valueFrom = "${aws_secretsmanager_secret.application.arn}:database_url::" },
    { name = "YARD_ACCESS_TOKEN_SECRET", valueFrom = "${aws_secretsmanager_secret.application.arn}:access_token_secret::" },
    { name = "YARD_VERIFICATION_PEPPER", valueFrom = "${aws_secretsmanager_secret.application.arn}:verification_pepper::" },
    { name = "YARD_APNS_TEAM_ID", valueFrom = "${aws_secretsmanager_secret.application.arn}:apns_team_id::" },
    { name = "YARD_APNS_KEY_ID", valueFrom = "${aws_secretsmanager_secret.application.arn}:apns_key_id::" },
    { name = "YARD_APNS_PRIVATE_KEY", valueFrom = "${aws_secretsmanager_secret.application.arn}:apns_private_key::" }
  ]
  log_configuration = {
    logDriver = "awslogs"
    options = {
      awslogs-group         = aws_cloudwatch_log_group.app.name
      awslogs-region        = var.aws_region
      awslogs-stream-prefix = "yard"
    }
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name             = "api", image = var.api_image, essential = true,
    portMappings     = [{ containerPort = 8000, protocol = "tcp" }],
    environment      = local.environment, secrets = local.secrets,
    logConfiguration = local.log_configuration,
    healthCheck      = { command = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/ready')\""], interval = 30, timeout = 5, retries = 3, startPeriod = 30 }
  }])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name             = "worker", image = var.worker_image, essential = true,
    environment      = local.environment, secrets = local.secrets,
    logConfiguration = local.log_configuration
  }])
}

resource "aws_ecs_task_definition" "admin" {
  family                   = "${var.name}-admin"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name             = "admin", image = var.admin_image, essential = true,
    portMappings     = [{ containerPort = 3000, protocol = "tcp" }],
    environment      = [{ name = "API_BASE_URL", value = "http://${aws_lb.this.dns_name}" }],
    logConfiguration = local.log_configuration
  }])
}

resource "aws_lb" "this" {
  name                       = substr(var.name, 0, 32)
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [var.load_balancer_sg_id]
  subnets                    = var.public_subnet_ids
  enable_deletion_protection = var.enable_deletion_protection
}

resource "aws_lb_target_group" "api" {
  name        = substr("${var.name}-api", 0, 32)
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check { path = "/ready" }
}

resource "aws_lb_target_group" "admin" {
  name        = substr("${var.name}-admin", 0, 32)
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check { path = "/" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = var.certificate_arn == "" ? 80 : 443
  protocol          = var.certificate_arn == "" ? "HTTP" : "HTTPS"
  certificate_arn   = var.certificate_arn == "" ? null : var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.admin.arn
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern {
      values = ["/api/*", "/health", "/ready", "/metrics", "/docs", "/openapi.json"]
    }
  }
}

resource "aws_ecs_service" "api" {
  name            = "${var.name}-api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_api_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "worker" {
  name            = "${var.name}-worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.desired_worker_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = false
  }
}

resource "aws_ecs_service" "admin" {
  name            = "${var.name}-admin"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.admin.arn
  desired_count   = var.desired_admin_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.admin.arn
    container_name   = "admin"
    container_port   = 3000
  }
  depends_on = [aws_lb_listener.http]
}
