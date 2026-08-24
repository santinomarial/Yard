locals {
  name = "yard-${var.environment}"
}

module "network" {
  source = "./modules/network"

  name                       = local.name
  enable_deletion_protection = var.enable_deletion_protection
}

module "data" {
  source = "./modules/data"

  name                       = local.name
  vpc_id                     = module.network.vpc_id
  private_subnet_ids         = module.network.private_subnet_ids
  app_security_group         = module.network.app_security_group_id
  enable_deletion_protection = var.enable_deletion_protection
}

module "storage" {
  source = "./modules/storage"

  name           = local.name
  ses_from_email = var.ses_from_email
  cors_origins   = var.cors_origins
}

module "compute" {
  source = "./modules/compute"

  name                       = local.name
  aws_region                 = var.aws_region
  vpc_id                     = module.network.vpc_id
  public_subnet_ids          = module.network.public_subnet_ids
  private_subnet_ids         = module.network.private_subnet_ids
  load_balancer_sg_id        = module.network.load_balancer_security_group_id
  app_security_group_id      = module.network.app_security_group_id
  certificate_arn            = var.certificate_arn
  api_image                  = var.api_image
  worker_image               = var.worker_image
  admin_image                = var.admin_image
  desired_api_count          = var.desired_api_count
  desired_worker_count       = var.desired_worker_count
  desired_admin_count        = var.desired_admin_count
  database_secret_arn        = module.data.database_secret_arn
  redis_url                  = module.data.redis_url
  asset_bucket_name          = module.storage.asset_bucket_name
  asset_bucket_arn           = module.storage.asset_bucket_arn
  asset_base_url             = module.storage.asset_base_url
  apple_audience             = var.apple_audience
  cors_origins               = var.cors_origins
  ses_from_email             = var.ses_from_email
  enable_deletion_protection = var.enable_deletion_protection
}
