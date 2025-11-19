# CloudFront distribution for API to provide HTTPS without requiring a domain
# This solves the mixed content issue when frontend (HTTPS) calls API (HTTP)

resource "aws_cloudfront_response_headers_policy" "api_cors" {
  name    = "skyfi-intellicheck-api-cors-${var.environment}"
  comment = "CORS headers for API distribution - allows all origins to match backend CORS config"

  cors_config {
    # Set to false when using wildcard origins per CORS spec
    # Authentication is via Authorization header, not cookies, so credentials not needed
    access_control_allow_credentials = false
    access_control_allow_headers {
      items = [
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
        "X-Correlation-ID",
      ]
    }
    access_control_allow_methods {
      items = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    }
    # Allow all origins - matches backend FastAPI CORS config which allows "*"
    # This avoids circular dependency with frontend distribution
    access_control_allow_origins {
      items = ["*"]
    }
    access_control_expose_headers {
      items = [
        "Content-Type",
        "X-Correlation-ID",
        "Content-Length",
        "Date",
        "Server",
      ]
    }
    access_control_max_age_sec = 3600
    origin_override            = true
  }
}

resource "aws_cloudfront_origin_request_policy" "api_all" {
  name    = "skyfi-intellicheck-api-all-${var.environment}"
  comment = "Forward all viewer headers, cookies, and query strings for API"

  cookies_config {
    cookie_behavior = "all"
  }

  headers_config {
    header_behavior = "allViewerAndWhitelistCloudFront"
    headers {
      items = ["CloudFront-Forwarded-Proto"]
    }
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

resource "aws_cloudfront_distribution" "api" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "SkyFi IntelliCheck API distribution (HTTPS termination for ALB)"
  price_class     = var.cloudfront_price_class

  origin {
    domain_name = aws_lb.api.dns_name
    origin_id   = "api-alb-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }

    custom_header {
      name  = "X-Forwarded-Proto"
      value = "https"
    }
  }

  default_cache_behavior {
    target_origin_id       = "api-alb-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    # Use CloudFront managed cache policy and custom origin request policy
    cache_policy_id            = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # Managed-CachingDisabled
    origin_request_policy_id   = aws_cloudfront_origin_request_policy.api_all.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.api_cors.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version      = "TLSv1.2_2021"
  }

  tags = {
    Name = "skyfi-intellicheck-api"
  }
}

