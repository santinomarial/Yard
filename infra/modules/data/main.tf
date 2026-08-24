resource "aws_security_group" "data" {
  name_prefix = "${var.name}-data-"
  description = "PostgreSQL and Redis ingress from Yard tasks"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.app_security_group]
  }

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.app_security_group]
  }

  lifecycle { create_before_destroy = true }
}

resource "aws_db_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.private_subnet_ids
}

resource "aws_db_instance" "postgres" {
  identifier                   = var.name
  engine                       = "postgres"
  engine_version               = "16.4"
  instance_class               = "db.t4g.micro"
  allocated_storage            = 20
  max_allocated_storage        = 100
  storage_type                 = "gp3"
  storage_encrypted            = true
  db_name                      = "yard"
  username                     = "yard"
  manage_master_user_password  = true
  db_subnet_group_name         = aws_db_subnet_group.this.name
  vpc_security_group_ids       = [aws_security_group.data.id]
  backup_retention_period      = 7
  deletion_protection          = var.enable_deletion_protection
  skip_final_snapshot          = !var.enable_deletion_protection
  final_snapshot_identifier    = "${var.name}-final"
  performance_insights_enabled = true
  multi_az                     = false
  publicly_accessible          = false
}

resource "aws_elasticache_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.private_subnet_ids
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = var.name
  description                = "Yard cache, rate limits, and job coordination"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = "cache.t4g.micro"
  port                       = 6379
  num_cache_clusters         = 1
  automatic_failover_enabled = false
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = [aws_security_group.data.id]
  snapshot_retention_limit   = 1
}
