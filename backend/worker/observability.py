"""
Observability utilities for the Lambda worker.
Provides metrics and enhanced logging integration.
"""
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from worker.correlation import get_correlation_id

logger = logging.getLogger(__name__)


class WorkerMetrics:
    """
    Metrics client for Lambda worker operations.
    Wraps CloudWatch metrics with worker-specific convenience methods.
    """
    
    def __init__(self, namespace: str = "SkyFi/IntelliCheck", region: Optional[str] = None):
        """
        Initialize worker metrics client.
        
        Args:
            namespace: CloudWatch namespace
            region: AWS region
        """
        self.namespace = namespace
        self.region = region or "us-east-1"
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        except Exception as e:
            logger.warning(f"Failed to initialize CloudWatch client: {e}. Metrics will be disabled.")
            self.cloudwatch = None
    
    def _put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: Optional[Dict[str, str]] = None
    ) -> bool:
        """Internal method to publish a metric."""
        if self.cloudwatch is None:
            return False
        
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow()
        }
        
        if dimensions:
            metric_data['Dimensions'] = [
                {'Name': k, 'Value': v} for k, v in dimensions.items()
            ]
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to publish metric {metric_name}: {e}")
            return False
    
    def record_analysis_success(
        self,
        company_id: str,
        duration_seconds: float,
        correlation_id: Optional[str] = None
    ):
        """Record a successful analysis completion."""
        dimensions = {"Status": "success"}
        if correlation_id:
            dimensions["CorrelationId"] = correlation_id
        
        self._put_metric("AnalysisSuccess", 1, "Count", dimensions)
        self._put_metric("AnalysisDuration", duration_seconds, "Seconds", dimensions)
    
    def record_analysis_failure(
        self,
        company_id: str,
        error_type: str,
        correlation_id: Optional[str] = None
    ):
        """Record a failed analysis."""
        dimensions = {
            "Status": "failure",
            "ErrorType": error_type
        }
        if correlation_id:
            dimensions["CorrelationId"] = correlation_id
        
        self._put_metric("AnalysisFailure", 1, "Count", dimensions)
    
    def record_analysis_incomplete(
        self,
        company_id: str,
        failed_checks_count: int,
        correlation_id: Optional[str] = None
    ):
        """Record an incomplete analysis (partial failure)."""
        dimensions = {"Status": "incomplete"}
        if correlation_id:
            dimensions["CorrelationId"] = correlation_id
        
        self._put_metric("AnalysisIncomplete", 1, "Count", dimensions)
        self._put_metric("FailedChecksCount", failed_checks_count, "Count", dimensions)
    
    def record_integration_success(
        self,
        integration_type: str,
        correlation_id: Optional[str] = None
    ):
        """Record a successful integration check."""
        dimensions = {
            "Integration": integration_type,
            "Status": "success"
        }
        if correlation_id:
            dimensions["CorrelationId"] = correlation_id
        
        self._put_metric("IntegrationCheck", 1, "Count", dimensions)
    
    def record_integration_failure(
        self,
        integration_type: str,
        error_type: str,
        correlation_id: Optional[str] = None
    ):
        """Record a failed integration check."""
        dimensions = {
            "Integration": integration_type,
            "Status": "failure",
            "ErrorType": error_type
        }
        if correlation_id:
            dimensions["CorrelationId"] = correlation_id
        
        self._put_metric("IntegrationCheck", 1, "Count", dimensions)
    
    def record_worker_execution_duration(
        self,
        duration_seconds: float,
        correlation_id: Optional[str] = None
    ):
        """Record total worker execution duration."""
        dimensions = {}
        if correlation_id:
            dimensions["CorrelationId"] = correlation_id
        
        self._put_metric("WorkerExecutionDuration", duration_seconds, "Seconds", dimensions)
    
    def record_retry_count(
        self,
        retry_count: int,
        correlation_id: Optional[str] = None
    ):
        """Record number of retries for an analysis."""
        dimensions = {}
        if correlation_id:
            dimensions["CorrelationId"] = correlation_id
        
        self._put_metric("AnalysisRetryCount", retry_count, "Count", dimensions)


class WorkerLogger:
    """
    Enhanced logger wrapper for worker operations.
    Automatically includes correlation ID in log messages.
    """
    
    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize worker logger.
        
        Args:
            correlation_id: Optional correlation ID (will be retrieved from context if not provided)
        """
        self.correlation_id = correlation_id or get_correlation_id()
        self.logger = logging.getLogger(__name__)
    
    def _get_extra(self, **kwargs) -> Dict[str, Any]:
        """Build extra fields for logging."""
        extra = kwargs.copy()
        if self.correlation_id:
            extra["correlation_id"] = self.correlation_id
        return extra
    
    def info(self, message: str, **kwargs):
        """Log info message with correlation ID."""
        self.logger.info(message, extra=self._get_extra(**kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message with correlation ID."""
        # Extract exc_info if present (to avoid conflict with extra dict)
        exc_info = kwargs.pop('exc_info', None)
        extra = self._get_extra(**kwargs)
        if exc_info is not None:
            self.logger.error(message, extra=extra, exc_info=exc_info)
        else:
            self.logger.error(message, extra=extra)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with correlation ID."""
        self.logger.warning(message, extra=self._get_extra(**kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log debug message with correlation ID."""
        self.logger.debug(message, extra=self._get_extra(**kwargs))

