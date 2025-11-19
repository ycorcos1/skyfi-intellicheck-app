locals {
  frontend_certificate_domains = var.enable_custom_domain ? compact(concat([var.frontend_domain_name], var.frontend_additional_domain_names)) : []
  api_certificate_domain       = var.api_domain_name != "" ? var.api_domain_name : ""
}

resource "aws_acm_certificate" "frontend" {
  count = var.enable_custom_domain ? 1 : 0

  provider          = aws.us_east_1
  domain_name       = local.frontend_certificate_domains[0]
  validation_method = "DNS"

  subject_alternative_names = length(local.frontend_certificate_domains) > 1 ? slice(local.frontend_certificate_domains, 1, length(local.frontend_certificate_domains)) : []

  options {
    certificate_transparency_logging_preference = "ENABLED"
  }

  lifecycle {
    create_before_destroy = true

    precondition {
      condition     = length(local.frontend_certificate_domains) > 0
      error_message = "When enable_custom_domain is true, frontend_domain_name must be provided."
    }
  }

  tags = {
    Name = "skyfi-intellicheck-frontend-cert"
  }
}

resource "aws_acm_certificate_validation" "frontend" {
  count = var.enable_custom_domain && var.route53_zone_id != "" ? 1 : 0

  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.frontend[0].arn
  validation_record_fqdns = [for record in aws_route53_record.frontend_cert_validation : record.fqdn]
}

# ACM Certificate for API ALB
resource "aws_acm_certificate" "api" {
  count = local.api_certificate_domain != "" ? 1 : 0

  domain_name       = local.api_certificate_domain
  validation_method = "DNS"

  options {
    certificate_transparency_logging_preference = "ENABLED"
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "skyfi-intellicheck-api-cert"
  }
}

resource "aws_acm_certificate_validation" "api" {
  count = local.api_certificate_domain != "" && var.route53_zone_id != "" ? 1 : 0

  certificate_arn         = aws_acm_certificate.api[0].arn
  validation_record_fqdns = [for record in aws_route53_record.api_cert_validation : record.fqdn]
}

