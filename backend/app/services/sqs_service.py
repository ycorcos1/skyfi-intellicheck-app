"""
SQS Service for enqueueing company verification jobs.
"""
import json
import logging
import uuid
from typing import Optional, List
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SQSService:
    """Service for interacting with SQS verification queue."""
    
    def __init__(self):
        settings = get_settings()
        if not settings.sqs_queue_url:
            raise ValueError("SQS_QUEUE_URL not configured. Please set it in environment variables.")
        self.sqs_client = boto3.client('sqs', region_name=settings.aws_region)
        self.queue_url = settings.sqs_queue_url
    
    def enqueue_analysis(
        self,
        company_id: str,
        retry_mode: str = "full",
        failed_checks: Optional[List[str]] = None,
        correlation_id: Optional[str] = None
    ) -> dict:
        """
        Enqueue a company analysis job.
        
        Args:
            company_id: UUID of company to analyze
            retry_mode: "full" or "failed_only"
            failed_checks: List of failed checks to retry (if retry_mode="failed_only")
            correlation_id: Optional correlation ID for tracking
        
        Returns:
            SQS SendMessage response
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        message_body = {
            "company_id": str(company_id),
            "retry_mode": retry_mode,
            "failed_checks": failed_checks or [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        message_attributes = {
            "CorrelationId": {
                "DataType": "String",
                "StringValue": correlation_id
            }
        }
        
        try:
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
                MessageAttributes=message_attributes
            )
            
            logger.info(
                f"Enqueued analysis for company {company_id} "
                f"(MessageId: {response['MessageId']}, CorrelationId: {correlation_id})"
            )
            
            return response
            
        except ClientError as e:
            logger.error(
                f"Failed to enqueue analysis for company {company_id}: {e}",
                exc_info=True
            )
            raise
    
    def enqueue_reanalysis(
        self,
        company_id: str,
        retry_failed_only: bool = False,
        failed_checks: Optional[List[str]] = None
    ) -> dict:
        """Enqueue a re-analysis job."""
        retry_mode = "failed_only" if retry_failed_only else "full"
        return self.enqueue_analysis(
            company_id=company_id,
            retry_mode=retry_mode,
            failed_checks=failed_checks
        )


# Singleton instance
_sqs_service: Optional[SQSService] = None


def get_sqs_service() -> SQSService:
    """Get or create SQS service singleton."""
    global _sqs_service
    if _sqs_service is None:
        _sqs_service = SQSService()
    return _sqs_service

