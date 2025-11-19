output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "nat_gateway_ids" {
  description = "IDs of NAT Gateways"
  value       = var.enable_nat_gateway ? aws_nat_gateway.main[*].id : []
}

output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "IDs of private route tables"
  value       = aws_route_table.private[*].id
}

# RDS Outputs
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.intellicheck.address
}

output "rds_port" {
  description = "RDS PostgreSQL port"
  value       = aws_db_instance.intellicheck.port
}

output "db_secret_arn" {
  description = "ARN of database credentials secret"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

# S3 Outputs
output "documents_bucket_name" {
  description = "S3 bucket name for documents"
  value       = aws_s3_bucket.documents.id
}

output "documents_bucket_arn" {
  description = "S3 bucket ARN for documents"
  value       = aws_s3_bucket.documents.arn
}

# SQS Outputs
output "verification_queue_url" {
  description = "URL of the verification SQS queue"
  value       = aws_sqs_queue.verification.url
}

output "verification_queue_arn" {
  description = "ARN of the verification SQS queue"
  value       = aws_sqs_queue.verification.arn
}

output "verification_dlq_url" {
  description = "URL of the verification DLQ"
  value       = aws_sqs_queue.verification_dlq.url
}

# Lambda Outputs
output "lambda_worker_arn" {
  description = "ARN of Lambda worker function"
  value       = aws_lambda_function.worker.arn
}

output "lambda_worker_name" {
  description = "Name of Lambda worker function"
  value       = aws_lambda_function.worker.function_name
}

output "lambda_worker_version" {
  description = "Latest published version of Lambda worker"
  value       = aws_lambda_function.worker.version
}

output "lambda_worker_last_modified" {
  description = "Last modified timestamp of Lambda worker"
  value       = aws_lambda_function.worker.last_modified
}

# ECS Outputs
output "ecs_cluster_name" {
  description = "Name of ECS cluster"
  value       = aws_ecs_cluster.intellicheck.name
}

output "ecs_cluster_arn" {
  description = "ARN of ECS cluster"
  value       = aws_ecs_cluster.intellicheck.arn
}

output "ecs_task_execution_role_arn" {
  description = "ARN of ECS task execution role"
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN of ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

output "ecr_repository_url" {
  description = "URL of the ECR repository for backend API"
  value       = aws_ecr_repository.backend_api.repository_url
}

output "ecr_repository_arn" {
  description = "ARN of the ECR repository for backend API"
  value       = aws_ecr_repository.backend_api.arn
}

output "ecr_registry_id" {
  description = "Registry ID for the ECR repository"
  value       = aws_ecr_repository.backend_api.registry_id
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.backend_api.name
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend static assets"
  value       = aws_s3_bucket.frontend.id
}

output "frontend_bucket_arn" {
  description = "S3 bucket ARN for frontend static assets"
  value       = aws_s3_bucket.frontend.arn
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution serving the frontend"
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_distribution_domain_name" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution"
  value       = aws_cloudfront_distribution.frontend.arn
}

output "frontend_url" {
  description = "URL used to access the frontend application"
  value       = var.enable_custom_domain && length(local.frontend_certificate_domains) > 0 ? "https://${local.frontend_certificate_domains[0]}" : format("https://%s", aws_cloudfront_distribution.frontend.domain_name)
}

output "acm_certificate_arn_frontend" {
  description = "ARN of the ACM certificate used for the frontend (if custom domain is enabled)"
  value       = var.enable_custom_domain ? aws_acm_certificate.frontend[0].arn : ""
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.api.dns_name
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.api.arn
}

output "alb_zone_id" {
  description = "Route53 zone ID of the Application Load Balancer"
  value       = aws_lb.api.zone_id
}

output "alb_target_group_arn" {
  description = "ARN of the ECS target group behind the ALB"
  value       = aws_lb_target_group.ecs.arn
}

output "api_url" {
  description = "Base URL for the backend API (uses CloudFront HTTPS if available, otherwise ALB)"
  value       = (var.certificate_arn != "" || local.api_certificate_domain != "") ? (
    local.api_certificate_domain != "" ? "https://${local.api_certificate_domain}" : "https://${aws_lb.api.dns_name}"
  ) : "https://${aws_cloudfront_distribution.api.domain_name}"
}

output "api_cloudfront_domain" {
  description = "CloudFront domain name for the API (HTTPS enabled)"
  value       = aws_cloudfront_distribution.api.domain_name
}

output "api_cloudfront_distribution_id" {
  description = "CloudFront distribution ID for the API"
  value       = aws_cloudfront_distribution.api.id
}

output "api_certificate_arn" {
  description = "ARN of the ACM certificate used for the API ALB (if api_domain_name is provided)"
  value       = local.api_certificate_domain != "" ? aws_acm_certificate.api[0].arn : ""
}

# Cognito Outputs
output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.intellicheck.id
}

output "cognito_app_client_id" {
  description = "App Client ID for Cognito authentication"
  value       = aws_cognito_user_pool_client.intellicheck.id
}

output "cognito_issuer" {
  description = "Issuer URL for the Cognito User Pool"
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.intellicheck.id}"
}

