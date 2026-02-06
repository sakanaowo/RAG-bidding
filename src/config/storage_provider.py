"""
Storage Provider Abstraction Layer

Provides unified interface for file storage operations across:
- Local filesystem (dev environment)
- Google Cloud Storage (production environment)

Auto-switches based on USE_GCS_STORAGE environment variable.
"""

import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from .models import settings

logger = logging.getLogger(__name__)


@runtime_checkable
class StorageProvider(Protocol):
    """Protocol for storage operations."""
    
    def upload(self, path: str, content: bytes, content_type: Optional[str] = None) -> str:
        """Upload content to storage. Returns the storage path/URL."""
        ...
    
    def download(self, path: str) -> bytes:
        """Download content from storage."""
        ...
    
    def delete(self, path: str) -> bool:
        """Delete file from storage. Returns True if successful."""
        ...
    
    def exists(self, path: str) -> bool:
        """Check if file exists in storage."""
        ...
    
    def get_url(self, path: str) -> str:
        """Get public or signed URL for the file."""
        ...


class LocalStorageProvider:
    """
    Local filesystem storage provider for development.
    
    Stores files in a configurable base directory.
    """
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorageProvider initialized with base_path: {self.base_path}")
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve relative path to absolute path within base directory."""
        return self.base_path / path
    
    def upload(self, path: str, content: bytes, content_type: Optional[str] = None) -> str:
        """Upload content to local filesystem."""
        file_path = self._resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_bytes(content)
        logger.info(f"Uploaded to local storage: {file_path}")
        
        return str(file_path)
    
    def download(self, path: str) -> bytes:
        """Download content from local filesystem."""
        file_path = self._resolve_path(path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return file_path.read_bytes()
    
    def delete(self, path: str) -> bool:
        """Delete file from local filesystem."""
        file_path = self._resolve_path(path)
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted from local storage: {file_path}")
            return True
        
        return False
    
    def exists(self, path: str) -> bool:
        """Check if file exists in local filesystem."""
        return self._resolve_path(path).exists()
    
    def get_url(self, path: str) -> str:
        """Get file:// URL for local file."""
        file_path = self._resolve_path(path)
        return f"file://{file_path.absolute()}"


class GCSStorageProvider:
    """
    Google Cloud Storage provider for production.
    
    Requires:
        - GCS_BUCKET environment variable
        - Google Cloud credentials (via GOOGLE_APPLICATION_CREDENTIALS or default)
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.gcs_bucket
        
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET environment variable not set")
        
        self._client = None
        self._bucket = None
        logger.info(f"GCSStorageProvider initialized for bucket: {self.bucket_name}")
    
    @property
    def client(self):
        """Lazy-load GCS client."""
        if self._client is None:
            try:
                from google.cloud import storage
                self._client = storage.Client(project=settings.google_cloud_project)
            except ImportError:
                raise ImportError(
                    "google-cloud-storage package required. "
                    "Install with: pip install google-cloud-storage"
                )
        return self._client
    
    @property
    def bucket(self):
        """Lazy-load GCS bucket."""
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket
    
    def upload(self, path: str, content: bytes, content_type: Optional[str] = None) -> str:
        """Upload content to GCS bucket."""
        blob = self.bucket.blob(path)
        
        if content_type:
            blob.content_type = content_type
        
        blob.upload_from_string(content)
        logger.info(f"Uploaded to GCS: gs://{self.bucket_name}/{path}")
        
        return f"gs://{self.bucket_name}/{path}"
    
    def download(self, path: str) -> bytes:
        """Download content from GCS bucket."""
        blob = self.bucket.blob(path)
        
        if not blob.exists():
            raise FileNotFoundError(f"File not found in GCS: gs://{self.bucket_name}/{path}")
        
        return blob.download_as_bytes()
    
    def delete(self, path: str) -> bool:
        """Delete file from GCS bucket."""
        blob = self.bucket.blob(path)
        
        if blob.exists():
            blob.delete()
            logger.info(f"Deleted from GCS: gs://{self.bucket_name}/{path}")
            return True
        
        return False
    
    def exists(self, path: str) -> bool:
        """Check if file exists in GCS bucket."""
        blob = self.bucket.blob(path)
        return blob.exists()
    
    def get_url(self, path: str, expiration: int = 3600) -> str:
        """
        Get signed URL for GCS file.
        
        Args:
            path: File path in bucket
            expiration: URL expiration time in seconds (default 1 hour)
        
        Returns:
            Signed URL for temporary access
        """
        from datetime import timedelta
        
        blob = self.bucket.blob(path)
        url = blob.generate_signed_url(expiration=timedelta(seconds=expiration))
        
        return url
    
    def get_public_url(self, path: str) -> str:
        """Get public URL (requires bucket to be public)."""
        return f"https://storage.googleapis.com/{self.bucket_name}/{path}"


# Singleton instance
_storage_provider: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    """
    Get storage provider instance based on environment configuration.
    
    Auto-switches:
        - USE_GCS_STORAGE=true  -> GCSStorageProvider
        - USE_GCS_STORAGE=false -> LocalStorageProvider
    
    Returns:
        StorageProvider instance
    """
    global _storage_provider
    
    if _storage_provider is None:
        if settings.use_gcs_storage:
            logger.info(f"🌐 Using GCS storage (bucket: {settings.gcs_bucket})")
            _storage_provider = GCSStorageProvider()
        else:
            logger.info("💻 Using local file storage")
            _storage_provider = LocalStorageProvider()
    
    return _storage_provider


def reset_storage_provider():
    """Reset singleton for testing purposes."""
    global _storage_provider
    _storage_provider = None
