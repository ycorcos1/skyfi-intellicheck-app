"""
CloudWatch metrics client for tracking system metrics.
"""
import boto3
import os
from datetime import datetime
from typing import Dict, Optional, List
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class MetricsClient:
    """
    Client for publishing custom metrics to CloudWatch.
    
    All metrics are published under the namespace "SkyFi/IntelliCheck".
    """
    
    def __init__(self, namespace: str = "SkyFi/IntelliCheck", region: Optional[str] = None):
        """
        Initialize CloudWatch metrics client.
        
        Args:
            namespace: CloudWatch namespace for metrics
            region: AWS region (defaults to environment or us-east-1)
        """
        self.namespace = namespace
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        except Exception as e:
            logger.warning(f"Failed to initialize CloudWatch client: {e}. Metrics will be disabled.")
            self.cloudwatch = None
    
    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Publish a single metric to CloudWatch.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement (Count, Seconds, Milliseconds, Bytes, etc.)
            dimensions: Optional dimensions for filtering/grouping
            timestamp: Optional timestamp (defaults to now)
        
        Returns:
            True if successful, False otherwise
        """
        if self.cloudwatch is None:
            return False
        
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': timestamp or datetime.utcnow()
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
    
    def put_metrics_batch(
        self,
        metrics: List[Dict[str, any]]
    ) -> bool:
        """
        Publish multiple metrics in a single call (more efficient).
        
        Args:
            metrics: List of metric dictionaries, each with:
                - metric_name: str
                - value: float
                - unit: str (optional, defaults to "Count")
                - dimensions: Dict[str, str] (optional)
                - timestamp: datetime (optional)
        
        Returns:
            True if successful, False otherwise
        """
        if self.cloudwatch is None:
            return False
        
        if not metrics:
            return True
        
        metric_data_list = []
        for metric in metrics:
            metric_entry = {
                'MetricName': metric['metric_name'],
                'Value': metric['value'],
                'Unit': metric.get('unit', 'Count'),
                'Timestamp': metric.get('timestamp', datetime.utcnow())
            }
            
            if 'dimensions' in metric and metric['dimensions']:
                metric_entry['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in metric['dimensions'].items()
                ]
            
            metric_data_list.append(metric_entry)
        
        try:
            # CloudWatch allows up to 20 metrics per call
            for i in range(0, len(metric_data_list), 20):
                batch = metric_data_list[i:i + 20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            return True
        except ClientError as e:
            logger.error(f"Failed to publish metrics batch: {e}")
            return False
    
    # Convenience methods for common metrics
    
    def record_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        correlation_id: Optional[str] = None
    ):
        """Record an API request metric."""
        dimensions = {
            "Endpoint": endpoint,
            "Method": method,
            "StatusClass": f"{status_code // 100}xx"
        }
        
        # Record request count
        self.put_metric("APIRequestCount", 1, "Count", dimensions)
        
        # Record latency
        self.put_metric("APIRequestDuration", duration_ms, "Milliseconds", dimensions)
        
        # Record error if 4xx or 5xx
        if status_code >= 400:
            error_dimensions = dimensions.copy()
            error_dimensions["StatusCode"] = str(status_code)
            self.put_metric("APIErrorCount", 1, "Count", error_dimensions)
    
    def record_analysis_success(
        self,
        company_id: str,
        duration_seconds: float,
        correlation_id: Optional[str] = None
    ):
        """Record a successful analysis."""
        dimensions = {"Status": "success"}
        if correlation_id:
            dimensions["CorrelationId"] = correlation_id
        
        self.put_metric("AnalysisSuccess", 1, "Count", dimensions)
        self.put_metric("AnalysisDuration", duration_seconds, "Seconds", dimensions)
    
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
        
        self.put_metric("AnalysisFailure", 1, "Count", dimensions)
    
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
        
        self.put_metric("IntegrationCheck", 1, "Count", dimensions)
    
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
        
        self.put_metric("IntegrationCheck", 1, "Count", dimensions)
    
    def record_partial_failure(
        self,
        company_id: str,
        failed_checks_count: int,
        correlation_id: Optional[str] = None
    ):
        """Record a partial analysis failure (incomplete)."""
        dimensions = {"Status": "incomplete"}
        if correlation_id:
            dimensions["CorrelationId"] = correlation_id
        
        self.put_metric("AnalysisIncomplete", 1, "Count", dimensions)
        self.put_metric("FailedChecksCount", failed_checks_count, "Count", dimensions)


# Singleton instance
_metrics_client: Optional[MetricsClient] = None


def get_metrics_client() -> MetricsClient:
    """Get or create metrics client singleton."""
    global _metrics_client
    if _metrics_client is None:
        _metrics_client = MetricsClient()
    return _metrics_client

