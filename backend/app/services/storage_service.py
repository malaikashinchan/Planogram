"""
Object Storage Abstraction and S3 Implementation.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from backend.app.core.config import settings


class StorageService(ABC):
    """Abstract interface for object storage."""

    @abstractmethod
    def upload(
        self,
        file_obj: BinaryIO,
        storage_key: str,
        content_type: str = "application/octet-stream",
    ) -> bool:
        """Upload a file to storage. Returns True if successful."""
        pass

    @abstractmethod
    def download(self, storage_key: str) -> bytes | None:
        """Download a file from storage. Returns bytes or None if not found."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete a file from storage. Returns True if successful."""
        pass

    @abstractmethod
    def generate_url(self, storage_key: str, expiration: int = 3600) -> str | None:
        """Generate a pre-signed URL for temporary access."""
        pass


class S3StorageService(StorageService):
    """AWS S3 implementation."""

    def __init__(self):
        self.bucket = settings.AWS_S3_BUCKET
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME,
        )

    def upload(
        self,
        file_obj: BinaryIO,
        storage_key: str,
        content_type: str = "application/octet-stream",
    ) -> bool:
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket,
                storage_key,
                ExtraArgs={"ContentType": content_type},
            )
            return True
        except ClientError as e:
            print(f"S3 Upload failed: {e}")
            return False

    def download(self, storage_key: str) -> bytes | None:
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=storage_key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            print(f"S3 Download failed: {e}")
            return None

    def delete(self, storage_key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=storage_key)
            return True
        except ClientError as e:
            print(f"S3 Delete failed: {e}")
            return False

    def generate_url(self, storage_key: str, expiration: int = 3600) -> str | None:
        try:
            response = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": storage_key},
                ExpiresIn=expiration,
            )
            return response
        except ClientError as e:
            print(f"S3 URL generation failed: {e}")
            return None


# Global instance to be used by the application
storage = S3StorageService()
