"""
S3 service providing helpers for presigned URL generation and object lifecycle.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service abstraction for S3 document operations."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.s3_bucket_name:
            raise ValueError(
                "S3_BUCKET_NAME not configured. Please set it in environment variables."
            )

        self.s3_client = boto3.client("s3", region_name=settings.aws_region)
        self.bucket_name = settings.s3_bucket_name
        self.upload_expiration = settings.s3_upload_expiration
        self.download_expiration = settings.s3_download_expiration

    @staticmethod
    def generate_s3_key(company_id: UUID, document_id: UUID, filename: str) -> str:
        """
        Create a deterministic S3 key for a document.

        Format: companies/{company_id}/documents/{document_id}/{filename}
        """
        return f"companies/{company_id}/documents/{document_id}/{filename}"

    def generate_upload_url(
        self,
        company_id: UUID,
        document_id: UUID,
        filename: str,
        mime_type: str,
    ) -> Dict[str, str]:
        """
        Generate a presigned PUT URL for uploading a document directly to S3.
        """
        s3_key = self.generate_s3_key(company_id, document_id, filename)

        try:
            upload_url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                    "ContentType": mime_type,
                },
                ExpiresIn=self.upload_expiration,
            )
        except ClientError as exc:  # pragma: no cover - boto3 handles error types
            logger.error(
                "Failed to generate S3 upload URL for company %s document %s: %s",
                company_id,
                document_id,
                exc,
                exc_info=True,
            )
            raise

        logger.info(
            "Generated S3 upload URL for company %s document %s (expires in %s seconds)",
            company_id,
            document_id,
            self.upload_expiration,
        )

        return {"upload_url": upload_url, "s3_key": s3_key}

    def generate_download_url(self, s3_key: str, filename: str) -> str:
        """
        Generate a presigned GET URL for downloading a document.
        """
        try:
            download_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                    "ResponseContentDisposition": f'attachment; filename="{filename}"',
                },
                ExpiresIn=self.download_expiration,
            )
        except ClientError as exc:  # pragma: no cover - boto3 handles error types
            logger.error(
                "Failed to generate S3 download URL for key %s: %s",
                s3_key,
                exc,
                exc_info=True,
            )
            raise

        logger.info(
            "Generated S3 download URL for key %s (expires in %s seconds)",
            s3_key,
            self.download_expiration,
        )
        return download_url

    def delete_object(self, s3_key: str) -> bool:
        """
        Delete an object from S3.

        Returns True when deletion request succeeds, False otherwise.
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        except ClientError as exc:  # pragma: no cover - boto3 handles error types
            logger.error("Failed to delete S3 object %s: %s", s3_key, exc, exc_info=True)
            return False

        logger.info("Deleted S3 object %s", s3_key)
        return True


_s3_service: Optional[S3Service] = None


def get_s3_service() -> S3Service:
    """Return a singleton instance of the S3 service."""
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service

