# CloudWatch Log Group for ECS API Service
resource "aws_cloudwatch_log_group" "ecs_api" {
  name              = "/aws/ecs/skyfi-intellicheck-api-${var.environment}"
  retention_in_days = 30

  # Tags applied via provider default_tags to avoid TagResource permission requirement
  # Can be added back after permissions are granted
}

# CloudWatch Dashboard for SkyFi IntelliCheck Observability

resource "aws_cloudwatch_dashboard" "intellicheck" {
  dashboard_name = "skyfi-intellicheck-dashboard-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Row 1: SQS Queue Metrics
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", {
              "stat"   = "Average"
              "period" = 300
              "label"  = "Queue Depth"
            }],
            ["AWS/SQS", "ApproximateNumberOfMessagesNotVisible", {
              "stat"   = "Average"
              "period" = 300
              "label"  = "In Flight"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "SQS Queue Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.verification_dlq.name, {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "DLQ Messages"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Dead Letter Queue"
          period  = 300
        }
      },
      # Row 2: Analysis Success vs Failure
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["SkyFi/IntelliCheck", "AnalysisSuccess", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "Success"
            }],
            ["SkyFi/IntelliCheck", "AnalysisFailure", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "Failure"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Analysis Success vs Failure"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["SkyFi/IntelliCheck", "AnalysisDuration", {
              "stat"   = "Average"
              "period" = 300
              "label"  = "Avg Duration"
            }],
            ["SkyFi/IntelliCheck", "AnalysisDuration", {
              "stat"   = "Maximum"
              "period" = 300
              "label"  = "Max Duration"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Analysis Duration (seconds)"
          period  = 300
        }
      },
      # Row 3: API Metrics
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["SkyFi/IntelliCheck", "APIRequestCount", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "Total Requests"
            }],
            ["SkyFi/IntelliCheck", "APIErrorCount", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "Errors"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "API Request Count"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["SkyFi/IntelliCheck", "APIRequestDuration", {
              "stat"   = "Average"
              "period" = 300
              "label"  = "Avg Latency"
            }],
            ["SkyFi/IntelliCheck", "APIRequestDuration", {
              "stat"   = "p95"
              "period" = 300
              "label"  = "P95 Latency"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "API Response Latency (ms)"
          period  = 300
        }
      },
      # Row 4: Integration Health (split into two widgets due to CloudWatch limit of 2 metrics per array)
      {
        type   = "metric"
        x      = 0
        y      = 18
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["SkyFi/IntelliCheck", "IntegrationCheck", "Integration", "whois", "Status", "success", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "WHOIS Success"
            }],
            ["SkyFi/IntelliCheck", "IntegrationCheck", "Integration", "whois", "Status", "failure", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "WHOIS Failure"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "WHOIS Integration Health"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 18
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["SkyFi/IntelliCheck", "IntegrationCheck", "Integration", "dns", "Status", "success", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "DNS Success"
            }],
            ["SkyFi/IntelliCheck", "IntegrationCheck", "Integration", "dns", "Status", "failure", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "DNS Failure"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "DNS Integration Health"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 24
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["SkyFi/IntelliCheck", "IntegrationCheck", "Integration", "mx_validation", "Status", "success", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "MX Success"
            }],
            ["SkyFi/IntelliCheck", "IntegrationCheck", "Integration", "mx_validation", "Status", "failure", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "MX Failure"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "MX Integration Health"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 24
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["SkyFi/IntelliCheck", "IntegrationCheck", "Integration", "website_scrape", "Status", "success", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "Website Success"
            }],
            ["SkyFi/IntelliCheck", "IntegrationCheck", "Integration", "website_scrape", "Status", "failure", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "Website Failure"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Website Integration Health"
          period  = 300
        }
      },
      # Row 6: Worker Execution Duration
      {
        type   = "metric"
        x      = 0
        y      = 30
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["SkyFi/IntelliCheck", "WorkerExecutionDuration", {
              "stat"   = "Average"
              "period" = 300
              "label"  = "Avg Execution Time"
            }],
            ["SkyFi/IntelliCheck", "WorkerExecutionDuration", {
              "stat"   = "Maximum"
              "period" = 300
              "label"  = "Max Execution Time"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Worker Execution Duration (seconds)"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 24
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["SkyFi/IntelliCheck", "CompanyCreated", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "Companies Created"
            }],
            ["SkyFi/IntelliCheck", "ReanalysisEnqueued", {
              "stat"   = "Sum"
              "period" = 300
              "label"  = "Reanalyses Enqueued"
            }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Business Metrics"
          period  = 300
        }
      }
    ]
  })
}

# CloudWatch Alarm for High Queue Depth
resource "aws_cloudwatch_metric_alarm" "high_queue_depth" {
  alarm_name          = "skyfi-intellicheck-high-queue-depth-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "100"
  alarm_description   = "Alert when SQS queue depth exceeds 100 messages"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.verification.name
  }

  tags = {
    Name = "skyfi-intellicheck-high-queue-depth-alarm"
  }
}

# CloudWatch Alarm for High Failure Rate
resource "aws_cloudwatch_metric_alarm" "high_analysis_failure_rate" {
  alarm_name          = "skyfi-intellicheck-high-failure-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "AnalysisFailure"
  namespace           = "SkyFi/IntelliCheck"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when analysis failures exceed 10 in 10 minutes"
  treat_missing_data  = "notBreaching"

  tags = {
    Name = "skyfi-intellicheck-high-failure-rate-alarm"
  }
}

# CloudWatch Alarm for DLQ Messages
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "skyfi-intellicheck-dlq-messages-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when messages appear in DLQ"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.verification_dlq.name
  }

  tags = {
    Name = "skyfi-intellicheck-dlq-alarm"
  }
}

