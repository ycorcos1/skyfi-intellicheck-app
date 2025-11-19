resource "aws_lb" "api" {
  name                       = "skyfi-intcheck-alb-${var.environment}"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = aws_subnet.public[*].id
  idle_timeout               = 60
  enable_deletion_protection = var.environment == "prod"
  drop_invalid_header_fields = true

  dynamic "access_logs" {
    for_each = var.enable_alb_access_logs ? [1] : []
    content {
      bucket  = var.alb_access_logs_bucket
      enabled = true
    }
  }

  tags = {
    Name        = "skyfi-intcheck-alb"
    Environment = var.environment
    Service     = "backend-api"
  }
}

resource "aws_lb_target_group" "ecs" {
  name        = "skyfi-intcheck-tg-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    enabled             = true
    path                = "/health"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    matcher             = "200"
    protocol            = "HTTP"
  }

  tags = {
    Name        = "skyfi-intcheck-tg"
    Environment = var.environment
    Service     = "backend-api"
  }
}

resource "aws_lb_listener" "http" {
  count             = (var.certificate_arn == "" && local.api_certificate_domain == "") ? 1 : 0
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ecs.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  count             = (var.certificate_arn != "" || local.api_certificate_domain != "") ? 1 : 0
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  count             = (var.certificate_arn != "" || local.api_certificate_domain != "") ? 1 : 0
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn != "" ? var.certificate_arn : (local.api_certificate_domain != "" ? aws_acm_certificate.api[0].arn : "")

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ecs.arn
  }
}

