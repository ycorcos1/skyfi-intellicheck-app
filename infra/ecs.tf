# ECS Cluster
resource "aws_ecs_cluster" "intellicheck" {
  name = "skyfi-intellicheck-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "skyfi-intellicheck-cluster"
  }
}

# Task execution role
resource "aws_iam_role" "ecs_task_execution" {
  name = "skyfi-intellicheck-ecs-task-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "skyfi-intellicheck-ecs-task-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_ecr" {
  name = "skyfi-intellicheck-ecr-pull-policy-${var.environment}"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = aws_ecr_repository.backend_api.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "skyfi-intellicheck-secrets-policy-${var.environment}"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.db_credentials.arn
      }
    ]
  })
}

# Task role (for application permissions)
resource "aws_iam_role" "ecs_task" {
  name = "skyfi-intellicheck-ecs-task-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "skyfi-intellicheck-ecs-task-role"
  }
}

# Task role policy
resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "skyfi-intellicheck-ecs-task-policy-${var.environment}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl"
        ]
        Resource = aws_sqs_queue.verification.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.documents.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.db_credentials.arn
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "SkyFi/IntelliCheck"
          }
        }
      }
    ]
  })
}

# API task definition
resource "aws_ecs_task_definition" "api" {
  family                   = "skyfi-intellicheck-api-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.api_container_cpu)
  memory                   = tostring(var.api_container_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.backend_api.repository_url}:latest"
      essential = true
      portMappings = [{
        containerPort = 8000
        hostPort      = 8000
        protocol      = "tcp"
      }]
      environment = [
        {
          name  = "API_VERSION"
          value = "1.0.0"
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "COGNITO_REGION"
          value = var.aws_region
        },
        {
          name  = "COGNITO_USER_POOL_ID"
          value = aws_cognito_user_pool.intellicheck.id
        },
        {
          name  = "COGNITO_APP_CLIENT_ID"
          value = aws_cognito_user_pool_client.intellicheck.id
        },
        {
          name  = "COGNITO_ISSUER"
          value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.intellicheck.id}"
        },
        {
          name  = "SQS_QUEUE_URL"
          value = aws_sqs_queue.verification.url
        },
        {
          name  = "S3_BUCKET_NAME"
          value = aws_s3_bucket.documents.id
        }
      ]
      secrets = [
        {
          name      = "DB_URL"
          valueFrom = "${aws_secretsmanager_secret.db_credentials.arn}:db_url::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_api.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }
      linuxParameters = {
        initProcessEnabled = true
      }
    }
  ])

  tags = {
    Name = "skyfi-intellicheck-api-task"
  }
}

# API service
resource "aws_ecs_service" "api" {
  name                   = "skyfi-intellicheck-api-service-${var.environment}"
  cluster                = aws_ecs_cluster.intellicheck.id
  task_definition        = aws_ecs_task_definition.api.arn
  desired_count          = var.api_desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  health_check_grace_period_seconds = 120

  load_balancer {
    target_group_arn = aws_lb_target_group.ecs.arn
    container_name   = "api"
    container_port   = 8000
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [desired_count, task_definition]
  }

  depends_on = [
    aws_lb_target_group.ecs
  ]

  tags = {
    Name = "skyfi-intellicheck-api-service"
  }
}

# Application Auto Scaling target for ECS service desired count
resource "aws_appautoscaling_target" "ecs_api" {
  max_capacity       = var.api_max_count
  min_capacity       = var.api_min_count
  resource_id        = "service/${aws_ecs_cluster.intellicheck.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_api_cpu" {
  name               = "skyfi-intcheck-ecs-cpu-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_api.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 60
    scale_out_cooldown = 60
  }
}

resource "aws_appautoscaling_policy" "ecs_api_memory" {
  name               = "skyfi-intcheck-ecs-mem-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_api.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 80
    scale_in_cooldown  = 60
    scale_out_cooldown = 60
  }
}




