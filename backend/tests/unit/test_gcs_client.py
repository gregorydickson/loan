"""Unit tests for GCS client.

Uses mocking to test without actual GCS access.
Integration tests will verify real GCS operations.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.storage.gcs_client import (
    GCSClient,
    GCSDownloadError,
    GCSUploadError,
)


class TestGCSClientInit:
    """Tests for GCSClient initialization."""

    def test_empty_bucket_name_raises_error(self):
        """Test that empty bucket name raises ValueError."""
        with pytest.raises(ValueError, match="bucket_name cannot be empty"):
            GCSClient("")

    @patch("src.storage.gcs_client.storage.Client")
    def test_creates_storage_client(self, mock_client_class: MagicMock):
        """Test that GCSClient creates a storage Client."""
        client = GCSClient("test-bucket")
        mock_client_class.assert_called_once()
        assert client.bucket_name == "test-bucket"


class TestGCSClientUpload:
    """Tests for GCSClient.upload method."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_upload_returns_gs_uri(self, mock_client_class: MagicMock):
        """Test that upload returns correct gs:// URI."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        client = GCSClient("my-bucket")
        uri = client.upload(b"test data", "documents/test.pdf", "application/pdf")

        assert uri == "gs://my-bucket/documents/test.pdf"
        mock_blob.upload_from_string.assert_called_once_with(
            b"test data", content_type="application/pdf"
        )

    @patch("src.storage.gcs_client.storage.Client")
    def test_upload_failure_raises_error(self, mock_client_class: MagicMock):
        """Test that upload failure raises GCSUploadError."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        mock_blob = MagicMock()
        mock_blob.upload_from_string.side_effect = Exception("Network error")
        mock_bucket.blob.return_value = mock_blob

        client = GCSClient("my-bucket")
        with pytest.raises(GCSUploadError, match="Failed to upload"):
            client.upload(b"test", "path.pdf")


class TestGCSClientDownload:
    """Tests for GCSClient.download method."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_download_returns_bytes(self, mock_client_class: MagicMock):
        """Test that download returns file content."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        mock_blob = MagicMock()
        mock_blob.download_as_bytes.return_value = b"file content"
        mock_bucket.blob.return_value = mock_blob

        client = GCSClient("my-bucket")
        data = client.download("documents/test.pdf")

        assert data == b"file content"

    @patch("src.storage.gcs_client.storage.Client")
    def test_download_not_found_raises_error(self, mock_client_class: MagicMock):
        """Test that downloading non-existent file raises error."""
        from google.cloud.exceptions import NotFound

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        mock_blob = MagicMock()
        mock_blob.download_as_bytes.side_effect = NotFound("Not found")
        mock_bucket.blob.return_value = mock_blob

        client = GCSClient("my-bucket")
        with pytest.raises(GCSDownloadError, match="File not found"):
            client.download("nonexistent.pdf")


class TestGCSClientExists:
    """Tests for GCSClient.exists method."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_exists_returns_true(self, mock_client_class: MagicMock):
        """Test exists returns True for existing file."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob

        client = GCSClient("my-bucket")
        assert client.exists("documents/test.pdf") is True

    @patch("src.storage.gcs_client.storage.Client")
    def test_exists_returns_false(self, mock_client_class: MagicMock):
        """Test exists returns False for non-existent file."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob

        client = GCSClient("my-bucket")
        assert client.exists("nonexistent.pdf") is False


class TestGCSClientDelete:
    """Tests for GCSClient.delete method."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_delete_succeeds(self, mock_client_class: MagicMock):
        """Test successful deletion."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        client = GCSClient("my-bucket")
        client.delete("documents/test.pdf")

        mock_blob.delete.assert_called_once()

    @patch("src.storage.gcs_client.storage.Client")
    def test_delete_not_found_succeeds(self, mock_client_class: MagicMock):
        """Test that deleting non-existent file doesn't raise error."""
        from google.cloud.exceptions import NotFound

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        mock_blob = MagicMock()
        mock_blob.delete.side_effect = NotFound("Not found")
        mock_bucket.blob.return_value = mock_blob

        client = GCSClient("my-bucket")
        # Should not raise
        client.delete("nonexistent.pdf")


class TestGCSClientSignedUrl:
    """Tests for GCSClient.get_signed_url method."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_get_signed_url_returns_url(self, mock_client_class: MagicMock):
        """Test that get_signed_url returns a URL."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_bucket = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        mock_blob = MagicMock()
        mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/signed-url"
        mock_bucket.blob.return_value = mock_blob

        client = GCSClient("my-bucket")
        url = client.get_signed_url("documents/test.pdf", expiration_minutes=30)

        assert "https://" in url
        mock_blob.generate_signed_url.assert_called_once()


class TestGCSClientParseUri:
    """Tests for GCSClient.parse_gcs_uri method."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_parse_valid_uri(self, mock_client_class: MagicMock):
        """Test parsing valid gs:// URI."""
        client = GCSClient("test-bucket")
        bucket, path = client.parse_gcs_uri("gs://my-bucket/path/to/file.pdf")
        assert bucket == "my-bucket"
        assert path == "path/to/file.pdf"

    @patch("src.storage.gcs_client.storage.Client")
    def test_parse_invalid_uri_raises_error(self, mock_client_class: MagicMock):
        """Test that invalid URI raises ValueError."""
        client = GCSClient("test-bucket")

        with pytest.raises(ValueError, match="Invalid GCS URI"):
            client.parse_gcs_uri("https://storage.googleapis.com/file")

        with pytest.raises(ValueError, match="Invalid GCS URI"):
            client.parse_gcs_uri("gs://bucket-only")
