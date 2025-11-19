# Lambda execution role
resource "aws_iam_role" "lambda_worker" {
  name = "skyfi-intellicheck-lambda-worker-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "skyfi-intellicheck-lambda-worker-role"
  }
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_vpc_execution" {
  role       = aws_iam_role.lambda_worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Custom policy for Lambda
resource "aws_iam_role_policy" "lambda_worker_policy" {
  name = "skyfi-intellicheck-lambda-worker-policy-${var.environment}"
  role = aws_iam_role.lambda_worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.verification.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.verification_dlq.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
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
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
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

# Lambda function
resource "aws_lambda_function" "worker" {
  filename      = "${path.module}/lambda_stub.zip" # Initial deployment only, replaced by deploy script
  function_name = "skyfi-intellicheck-worker-${var.environment}"
  role          = aws_iam_role.lambda_worker.arn
  handler       = "index.lambda_handler" # Points to index.py which imports from worker.handler
  runtime       = "python3.11"
  timeout       = 900  # 15 minutes
  memory_size   = 1024 # Increased for external API calls

  # Source code hash - will be updated by deployment script
  source_code_hash = filebase64sha256("${path.module}/lambda_stub.zip")

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.verification_dlq.arn
  }

  environment {
    variables = {
      DB_SECRET_ARN  = aws_secretsmanager_secret.db_credentials.arn
      S3_BUCKET_NAME = aws_s3_bucket.documents.id
      SQS_QUEUE_URL  = aws_sqs_queue.verification.url
      ENVIRONMENT    = var.environment

      # Timeout configurations
      WHOIS_TIMEOUT = "30"
      DNS_TIMEOUT   = "30"
      HTTP_TIMEOUT  = "30"
      MX_TIMEOUT    = "30"
      MAX_RETRIES   = "3"

      # Logging
      LOG_LEVEL = var.environment == "prod" ? "INFO" : "DEBUG"
      # AWS_REGION is reserved and automatically set by Lambda

      # Rate limiting (requests per second)
      OPENAI_RATE_LIMIT = "3"
      WHOIS_RATE_LIMIT  = "1"
      DNS_RATE_LIMIT    = "5"
      HTTP_RATE_LIMIT   = "10"

      # Algorithm version
      ALGORITHM_VERSION = "1.0.0"

      # OpenAI API Key (from variable, optional)
      OPENAI_API_KEY = var.openai_api_key
    }
  }

  # Ignore changes to source_code_hash after initial deployment
  # This allows manual deployments without Terraform drift
  lifecycle {
    ignore_changes = [
      source_code_hash
    ]
  }

  tags = {
    Name        = "skyfi-intellicheck-worker"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda_worker" {
  name              = "/aws/lambda/${aws_lambda_function.worker.function_name}"
  retention_in_days = 30

  tags = {
    Name = "skyfi-intellicheck-lambda-worker-logs"
  }
}

# SQS trigger for Lambda
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.verification.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 1
  enabled          = true
}




