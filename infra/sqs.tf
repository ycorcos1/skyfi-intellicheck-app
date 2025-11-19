# Dead Letter Queue
resource "aws_sqs_queue" "verification_dlq" {
  name                      = "skyfi-intellicheck-verification-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Name = "skyfi-intellicheck-verification-dlq"
  }
}

# Main verification queue
resource "aws_sqs_queue" "verification" {
  name                       = "skyfi-intellicheck-verification-queue-${var.environment}"
  visibility_timeout_seconds = 900     # 15 minutes
  message_retention_seconds  = 1209600 # 14 days
  receive_wait_time_seconds  = 20      # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.verification_dlq.arn
    maxReceiveCount     = 3
  })

  # Enable encryption at rest
  sqs_managed_sse_enabled = true

  tags = {
    Name = "skyfi-intellicheck-verification-queue"
  }
}




