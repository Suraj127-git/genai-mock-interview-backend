"""
S3 service for handling file uploads.
"""
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class S3Service:
    """Service class for S3 operations."""

    def __init__(self):
        """Initialize S3 client."""
        client_config = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.AWS_REGION,
        }

        # Add endpoint_url if provided (for Railway Object Storage)
        if settings.AWS_ENDPOINT_URL:
            # Clean up endpoint URL - remove $ prefix if present
            endpoint_url = settings.AWS_ENDPOINT_URL.lstrip("$")
            client_config["endpoint_url"] = endpoint_url

        self.s3_client = boto3.client("s3", **client_config)
        self.bucket_name = settings.S3_BUCKET_NAME

    def generate_s3_key(self, user_id: int, extension: str) -> str:
        """
        Generate a unique S3 key for upload.

        Args:
            user_id: User ID
            extension: File extension

        Returns:
            S3 object key
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"uploads/{user_id}/{timestamp}_{unique_id}.{extension}"

    def generate_presigned_url(
        self, key: str, content_type: str, expiration: int = None
    ) -> str:
        """
        Generate a presigned URL for S3 upload.

        Args:
            key: S3 object key
            content_type: MIME type of the file
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL for upload

        Raises:
            ClientError: If presigned URL generation fails
        """
        if expiration is None:
            expiration = settings.S3_PRESIGNED_URL_EXPIRATION

        try:
            url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def get_file_url(self, key: str) -> str:
        """
        Get the public URL for an S3 object.

        Args:
            key: S3 object key

        Returns:
            Public URL of the object
        """
        return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    async def get_file_size(self, key: str) -> int:
        """
        Get the size of an S3 object.

        Args:
            key: S3 object key

        Returns:
            File size in bytes

        Raises:
            ClientError: If object doesn't exist
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return response["ContentLength"]
        except ClientError as e:
            logger.error(f"Failed to get file size for {key}: {e}")
            raise

    def download_file(self, key: str, local_path: str) -> None:
        """
        Download a file from S3.

        Args:
            key: S3 object key
            local_path: Local file path to save to

        Raises:
            ClientError: If download fails
        """
        try:
            self.s3_client.download_file(self.bucket_name, key, local_path)
        except ClientError as e:
            logger.error(f"Failed to download file {key}: {e}")
            raise
