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


class LocalStorageService(StorageService):
    """Local disk implementation for testing without AWS S3."""

    def __init__(self):
        import os
        from backend.app.core.config import settings
        self.storage_dir = settings.PROJECT_ROOT / "outputs" / "local_s3"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def upload(
        self,
        file_obj: BinaryIO,
        storage_key: str,
        content_type: str = "application/octet-stream",
    ) -> bool:
        try:
            import os
            # storage_key might have slashes, e.g. "audits/123/crop.jpg"
            file_path = self.storage_dir / storage_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "wb") as f:
                f.write(file_obj.read())
            return True
        except Exception as e:
            print(f"Local Storage Upload failed: {e}")
            return False

    def download(self, storage_key: str) -> bytes | None:
        try:
            file_path = self.storage_dir / storage_key
            if not file_path.exists():
                return None
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            print(f"Local Storage Download failed: {e}")
            return None

    def delete(self, storage_key: str) -> bool:
        try:
            file_path = self.storage_dir / storage_key
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            print(f"Local Storage Delete failed: {e}")
            return False

    def generate_url(self, storage_key: str, expiration: int = 3600) -> str | None:
        # In a local environment, you could serve these statically.
        # But for pipeline training, we usually just need `download`.
        return f"http://localhost:8000/static/{storage_key}"

# Global instance to be used by the application
storage = S3StorageService()
# storage = LocalStorageService()
