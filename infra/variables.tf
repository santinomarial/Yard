variable "aws_region" {
  description = "AWS region for all Yard resources."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Short deployment environment name."
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "Optional existing Route 53 domain used for the public load balancer certificate."
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN. When absent, the load balancer exposes HTTP for bootstrap only."
  type        = string
  default     = ""
}

variable "api_image" {
  description = "Immutable API image reference, preferably pinned by digest."
  type        = string
}

variable "worker_image" {
  description = "Immutable worker image reference, preferably pinned by digest."
  type        = string
}

variable "admin_image" {
  description = "Immutable admin web image reference, preferably pinned by digest."
  type        = string
}

variable "apple_audience" {
  description = "Sign in with Apple service/bundle identifier."
  type        = string
  default     = "com.santinomarial.yard"
}

variable "ses_from_email" {
  description = "SES-verified sender used for Harvard email verification."
  type        = string
}

variable "cors_origins" {
  description = "Exact production origins allowed by the API."
  type        = list(string)
  default     = []

  validation {
    condition     = length(var.cors_origins) > 0 && alltrue([for origin in var.cors_origins : startswith(origin, "https://")])
    error_message = "Production CORS origins must contain at least one exact HTTPS origin."
  }
}

variable "desired_api_count" {
  type    = number
  default = 1
}

variable "desired_worker_count" {
  type    = number
  default = 1
}

variable "desired_admin_count" {
  type    = number
  default = 1
}

variable "enable_deletion_protection" {
  description = "Protect the production database and load balancer from accidental deletion."
  type        = bool
  default     = true
}
