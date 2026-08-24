variable "name" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "app_security_group" { type = string }
variable "enable_deletion_protection" { type = bool }
