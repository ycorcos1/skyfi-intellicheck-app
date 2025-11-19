variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "vpc_name" {
  description = "Name of the VPC"
  type        = string
  default     = "skyfi-intellicheck-vpc"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones to use"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.20.0.0/24", "10.20.1.0/24", "10.20.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.20.10.0/24", "10.20.11.0/24", "10.20.12.0/24"]
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use a single NAT gateway for all private subnets (cost optimization)"
  type        = bool
  default     = false
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.small"
}

variable "frontend_urls" {
  description = "Frontend URLs for S3 CORS configuration"
  type        = list(string)
  default     = ["http://localhost:3000"]
}

variable "openai_api_key" {
  description = "OpenAI API key for LLM analysis (sensitive, optional for dev)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "api_container_cpu" {
  description = "CPU units allocated to the API Fargate task (valid values: 256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 512
}

variable "api_container_memory" {
  description = "Memory (MiB) allocated to the API Fargate task"
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Desired number of API tasks running in the ECS service"
  type        = number
  default     = 2
}

variable "api_min_count" {
  description = "Minimum number of API tasks for auto-scaling"
  type        = number
  default     = 2
}

variable "api_max_count" {
  description = "Maximum number of API tasks for auto-scaling"
  type        = number
  default     = 10
}

variable "enable_alb_access_logs" {
  description = "Enable Application Load Balancer access logging to S3"
  type        = bool
  default     = false
}

variable "alb_access_logs_bucket" {
  description = "S3 bucket name for ALB access logs (required if enable_alb_access_logs is true)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ARN of ACM certificate for HTTPS listener (optional - will be auto-created if api_domain_name is provided)"
  type        = string
  default     = ""
}

variable "api_domain_name" {
  description = "Domain name for the API ALB (e.g., api.example.com). If provided, an ACM certificate will be created automatically."
  type        = string
  default     = ""
}

variable "enable_custom_domain" {
  description = "Enable custom domain and ACM certificate for CloudFront"
  type        = bool
  default     = false
}

variable "frontend_domain_name" {
  description = "Primary custom domain name for the frontend (e.g., app.example.com)"
  type        = string
  default     = ""
}

variable "frontend_additional_domain_names" {
  description = "Additional domain names for the frontend (e.g., www.app.example.com)"
  type        = list(string)
  default     = []
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID for custom domain management (optional)"
  type        = string
  default     = ""
}

variable "cloudfront_price_class" {
  description = "CloudFront price class (PriceClass_All, PriceClass_200, PriceClass_100)"
  type        = string
  default     = "PriceClass_100"
}

variable "frontend_default_root_object" {
  description = "Default root object served by CloudFront"
  type        = string
  default     = "index.html"
}

variable "api_url" {
  description = "Base URL of the backend API (used for CSP configuration)"
  type        = string
  default     = ""
}

