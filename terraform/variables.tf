variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (production, staging)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Short name used to prefix all resources"
  type        = string
  default     = "anote-ai"
}

variable "backend_image_tag" {
  description = "Docker image tag to deploy for the backend (set by CI to the git SHA)"
  type        = string
  default     = "latest"
}

variable "backend_container_port" {
  type    = number
  default = 5000
}

variable "backend_desired_count" {
  type    = number
  default = 2
}

variable "backend_cpu" {
  type    = number
  default = 512
}

variable "backend_memory" {
  type    = number
  default = 1024
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_name" {
  type    = string
  default = "anote"
}

variable "db_username" {
  type    = string
  default = "anote_admin"
}

variable "db_password" {
  description = "Master password for RDS. Pass via TF_VAR_db_password or a tfvars file excluded from git."
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "Flask JWT signing secret."
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "openai_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "stripe_secret_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "domain_name" {
  description = "Optional custom domain for the CloudFront distribution (requires an ACM cert in us-east-1). Leave empty to use the default CloudFront domain."
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN in us-east-1 for the CloudFront distribution. Required if domain_name is set."
  type        = string
  default     = ""
}
