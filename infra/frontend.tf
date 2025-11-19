locals {
  frontend_backend_api_origin = var.api_url != "" ? var.api_url : (
    var.certificate_arn != "" || local.api_certificate_domain != "" ?
    format("%s://%s", "https", local.api_certificate_domain != "" ? local.api_certificate_domain : aws_lb.api.dns_name) :
    format("%s://%s", "https", aws_cloudfront_distribution.api.domain_name)
  )

  frontend_csp_connect_sources = concat(
    ["'self'", "https://cognito-idp.${var.aws_region}.amazonaws.com"],
    local.frontend_backend_api_origin != "" ? [local.frontend_backend_api_origin] : []
  )
}

resource "aws_s3_bucket" "frontend" {
  bucket = "skyfi-intellicheck-frontend-${var.environment}"

  tags = {
    Name = "skyfi-intellicheck-frontend"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "skyfi-intellicheck-frontend-oac"
  description                       = "Origin access control for frontend S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_cache_policy" "frontend_html" {
  name        = "skyfi-intellicheck-html-${var.environment}"
  comment     = "Cache policy for HTML files"
  min_ttl     = 0
  default_ttl = 300
  max_ttl     = 3600

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }

    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
  }
}

resource "aws_cloudfront_cache_policy" "frontend_static" {
  name        = "skyfi-intellicheck-static-${var.environment}"
  comment     = "Cache policy for static assets"
  min_ttl     = 0
  default_ttl = 86400
  max_ttl     = 31536000

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }

    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
  }
}

resource "aws_cloudfront_response_headers_policy" "frontend_security" {
  name    = "skyfi-intellicheck-security-${var.environment}"
  comment = "Security headers for frontend distribution"

  security_headers_config {
    content_security_policy {
      content_security_policy = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src ${join(" ", local.frontend_csp_connect_sources)};"
      override                = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }

    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }

    xss_protection {
      mode_block = true
      protection = true
      override   = true
    }
  }
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "SkyFi IntelliCheck frontend distribution"
  default_root_object = var.frontend_default_root_object
  price_class         = var.cloudfront_price_class
  aliases             = var.enable_custom_domain ? local.frontend_certificate_domains : []

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "frontend-s3-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  default_cache_behavior {
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_html.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "/_next/static/*"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.js"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.css"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.png"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.jpg"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.jpeg"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.gif"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.ico"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.svg"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.webp"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.woff"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.woff2"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.ttf"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  ordered_cache_behavior {
    path_pattern           = "*.eot"
    target_origin_id       = "frontend-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id            = aws_cloudfront_cache_policy.frontend_static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_security.id
  }

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.enable_custom_domain ? false : true
    acm_certificate_arn            = var.enable_custom_domain ? aws_acm_certificate.frontend[0].arn : null
    ssl_support_method             = var.enable_custom_domain ? "sni-only" : null
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = {
    Name = "skyfi-intellicheck-frontend"
  }

  depends_on = [
    aws_s3_bucket_public_access_block.frontend
  ]
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "AllowCloudFrontService",
        Effect = "Allow",
        Principal = {
          Service = "cloudfront.amazonaws.com"
        },
        Action = [
          "s3:GetObject"
        ],
        Resource = "${aws_s3_bucket.frontend.arn}/*",
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
          }
        }
      }
    ]
  })

  depends_on = [aws_cloudfront_distribution.frontend]
}

