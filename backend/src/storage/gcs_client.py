"""Google Cloud Storage client for document storage.

Uses Application Default Credentials (ADC) for authentication:
- Local development: Set GOOGLE_APPLICATION_CREDENTIALS env var
- Cloud Run: Uses attached service account automatically
"""

from datetime import timedelta
from typing import BinaryIO, cast

from google.cloud import storage  # type: ignore[attr-defined]
from google.cloud.exceptions import NotFound


class GCSError(Exception):
    """Base exception for GCS operations."""

    pass


class GCSUploadError(GCSError):
    """Raised when upload fails."""

    pass


class GCSDownloadError(GCSError):
    """Raised when download fails."""

    pass


class GCSClient:
    """Google Cloud Storage client for document operations.

    Uses Application Default Credentials for seamless Cloud Run deployment.
    """

    def __init__(self, bucket_name: str) -> None:
        """Initialize GCS client.

        Args:
            bucket_name: Name of the GCS bucket to use
        """
        if not bucket_name:
            raise ValueError("bucket_name cannot be empty")

        # Uses Application Default Credentials (ADC)
        self.client = storage.Client()
        self.bucket_name = bucket_name
        self._bucket = None

    @property
    def bucket(self) -> storage.Bucket:
        """Lazy-load bucket to allow testing without real GCS."""
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def upload(
        self,
        data: bytes,
        path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes to GCS.

        Args:
            data: File content as bytes
            path: Destination path within bucket (e.g., "documents/uuid/file.pdf")
            content_type: MIME type of the file

        Returns:
            gs:// URI of uploaded file

        Raises:
            GCSUploadError: If upload fails
        """
        try:
            blob = self.bucket.blob(path)
            blob.upload_from_string(data, content_type=content_type)
            return f"gs://{self.bucket_name}/{path}"
        except Exception as e:
            raise GCSUploadError(f"Failed to upload to {path}: {e}") from e

    def upload_from_file(
        self,
        file_obj: BinaryIO,
        path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload from file-like object (memory efficient for large files).

        Args:
            file_obj: File-like object to upload
            path: Destination path within bucket
            content_type: MIME type of the file

        Returns:
            gs:// URI of uploaded file

        Raises:
            GCSUploadError: If upload fails
        """
        try:
            blob = self.bucket.blob(path)
            file_obj.seek(0)
            blob.upload_from_file(file_obj, content_type=content_type)
            return f"gs://{self.bucket_name}/{path}"
        except Exception as e:
            raise GCSUploadError(f"Failed to upload from file to {path}: {e}") from e

    def download(self, path: str) -> bytes:
        """Download file content as bytes.

        Args:
            path: Path within bucket to download

        Returns:
            File content as bytes

        Raises:
            GCSDownloadError: If download fails or file not found
        """
        try:
            blob = self.bucket.blob(path)
            return cast(bytes, blob.download_as_bytes())
        except NotFound as e:
            raise GCSDownloadError(f"File not found: {path}") from e
        except Exception as e:
            raise GCSDownloadError(f"Failed to download {path}: {e}") from e

    def download_to_file(self, path: str, file_obj: BinaryIO) -> None:
        """Download file to file-like object.

        Args:
            path: Path within bucket to download
            file_obj: File-like object to write to

        Raises:
            GCSDownloadError: If download fails
        """
        try:
            blob = self.bucket.blob(path)
            blob.download_to_file(file_obj)
            file_obj.seek(0)
        except NotFound as e:
            raise GCSDownloadError(f"File not found: {path}") from e
        except Exception as e:
            raise GCSDownloadError(f"Failed to download {path}: {e}") from e

    def exists(self, path: str) -> bool:
        """Check if file exists in bucket.

        Args:
            path: Path within bucket

        Returns:
            True if file exists, False otherwise
        """
        blob = self.bucket.blob(path)
        return cast(bool, blob.exists())

    def delete(self, path: str) -> None:
        """Delete a file from storage.

        Args:
            path: Path within bucket to delete

        Raises:
            GCSError: If deletion fails
        """
        try:
            blob = self.bucket.blob(path)
            blob.delete()
        except NotFound:
            pass  # Already deleted, not an error
        except Exception as e:
            raise GCSError(f"Failed to delete {path}: {e}") from e

    def get_signed_url(
        self,
        path: str,
        expiration_minutes: int = 15,
        method: str = "GET",
    ) -> str:
        """Generate a signed URL for temporary access.

        Args:
            path: Path within bucket
            expiration_minutes: How long the URL is valid (default 15 min)
            method: HTTP method (GET for download, PUT for upload)

        Returns:
            Signed URL string

        Note:
            Requires service account credentials for signing.
            On Cloud Run, uses impersonated credentials automatically.
        """
        blob = self.bucket.blob(path)
        return cast(
            str,
            blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method=method,
            ),
        )

    def parse_gcs_uri(self, uri: str) -> tuple[str, str]:
        """Parse a gs:// URI into bucket and path.

        Args:
            uri: GCS URI (e.g., "gs://bucket-name/path/to/file")

        Returns:
            Tuple of (bucket_name, path)

        Raises:
            ValueError: If URI format is invalid
        """
        if not uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI format: {uri}")

        parts = uri[5:].split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid GCS URI format: {uri}")

        return parts[0], parts[1]
