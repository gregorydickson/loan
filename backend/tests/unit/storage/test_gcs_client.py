"""Unit tests for GCS client."""

from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from google.cloud.exceptions import NotFound

from src.storage.gcs_client import (
    GCSClient,
    GCSDownloadError,
    GCSError,
    GCSUploadError,
)


class TestGCSClientInitialization:
    """Test GCS client initialization."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_initialization_with_valid_bucket_name(self, mock_storage_client):
        """Test successful initialization with valid bucket name."""
        client = GCSClient(bucket_name="test-bucket")

        assert client.bucket_name == "test-bucket"
        mock_storage_client.assert_called_once()

    @patch("src.storage.gcs_client.storage.Client")
    def test_initialization_with_empty_bucket_name_raises_error(
        self, mock_storage_client
    ):
        """Test that empty bucket name raises ValueError."""
        with pytest.raises(ValueError, match="bucket_name cannot be empty"):
            GCSClient(bucket_name="")

    @patch("src.storage.gcs_client.storage.Client")
    def test_bucket_property_lazy_loads(self, mock_storage_client):
        """Test that bucket property is lazy-loaded."""
        mock_client_instance = Mock()
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")

        # Bucket should not be loaded yet
        assert client._bucket is None

        # Access bucket property
        _ = client.bucket

        # Now bucket should be loaded
        mock_client_instance.bucket.assert_called_once_with("test-bucket")
        assert client._bucket is not None


class TestGCSClientUpload:
    """Test upload operations."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_upload_success(self, mock_storage_client):
        """Test successful upload of bytes."""
        # Setup mocks
        mock_blob = Mock()
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        data = b"test file content"
        path = "documents/test.pdf"

        result = client.upload(data, path, content_type="application/pdf")

        assert result == "gs://test-bucket/documents/test.pdf"
        mock_bucket.blob.assert_called_once_with(path)
        mock_blob.upload_from_string.assert_called_once_with(
            data, content_type="application/pdf"
        )

    @patch("src.storage.gcs_client.storage.Client")
    def test_upload_with_default_content_type(self, mock_storage_client):
        """Test upload with default content type."""
        mock_blob = Mock()
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        data = b"test content"

        result = client.upload(data, "test.bin")

        mock_blob.upload_from_string.assert_called_once_with(
            data, content_type="application/octet-stream"
        )

    @patch("src.storage.gcs_client.storage.Client")
    def test_upload_failure_raises_gcs_upload_error(self, mock_storage_client):
        """Test that upload failure raises GCSUploadError."""
        mock_blob = Mock()
        mock_blob.upload_from_string.side_effect = Exception("Network error")
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")

        with pytest.raises(GCSUploadError, match="Failed to upload to test.pdf"):
            client.upload(b"data", "test.pdf")

    @patch("src.storage.gcs_client.storage.Client")
    def test_upload_from_file_success(self, mock_storage_client):
        """Test successful upload from file object."""
        mock_blob = Mock()
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        file_obj = BytesIO(b"file content")
        path = "uploads/file.txt"

        result = client.upload_from_file(file_obj, path, content_type="text/plain")

        assert result == "gs://test-bucket/uploads/file.txt"
        mock_blob.upload_from_file.assert_called_once_with(
            file_obj, content_type="text/plain"
        )
        # Verify seek was called to reset file position
        assert file_obj.tell() == 0

    @patch("src.storage.gcs_client.storage.Client")
    def test_upload_from_file_failure_raises_error(self, mock_storage_client):
        """Test that upload_from_file failure raises GCSUploadError."""
        mock_blob = Mock()
        mock_blob.upload_from_file.side_effect = Exception("Disk error")
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        file_obj = BytesIO(b"data")

        with pytest.raises(
            GCSUploadError, match="Failed to upload from file to test.pdf"
        ):
            client.upload_from_file(file_obj, "test.pdf")


class TestGCSClientDownload:
    """Test download operations."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_download_success(self, mock_storage_client):
        """Test successful download of file."""
        mock_blob = Mock()
        expected_content = b"downloaded content"
        mock_blob.download_as_bytes.return_value = expected_content
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        result = client.download("documents/file.pdf")

        assert result == expected_content
        mock_bucket.blob.assert_called_once_with("documents/file.pdf")
        mock_blob.download_as_bytes.assert_called_once()

    @patch("src.storage.gcs_client.storage.Client")
    def test_download_not_found_raises_error(self, mock_storage_client):
        """Test that downloading non-existent file raises GCSDownloadError."""
        mock_blob = Mock()
        mock_blob.download_as_bytes.side_effect = NotFound("File not found")
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")

        with pytest.raises(GCSDownloadError, match="File not found: missing.pdf"):
            client.download("missing.pdf")

    @patch("src.storage.gcs_client.storage.Client")
    def test_download_generic_error_raises_gcs_download_error(self, mock_storage_client):
        """Test that generic download errors raise GCSDownloadError."""
        mock_blob = Mock()
        mock_blob.download_as_bytes.side_effect = Exception("Permission denied")
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")

        with pytest.raises(GCSDownloadError, match="Failed to download test.pdf"):
            client.download("test.pdf")

    @patch("src.storage.gcs_client.storage.Client")
    def test_download_to_file_success(self, mock_storage_client):
        """Test successful download to file object."""
        mock_blob = Mock()
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        file_obj = BytesIO()

        client.download_to_file("documents/file.pdf", file_obj)

        mock_blob.download_to_file.assert_called_once_with(file_obj)
        # Verify file position was reset
        assert file_obj.tell() == 0

    @patch("src.storage.gcs_client.storage.Client")
    def test_download_to_file_not_found_raises_error(self, mock_storage_client):
        """Test download_to_file with non-existent file raises error."""
        mock_blob = Mock()
        mock_blob.download_to_file.side_effect = NotFound("Not found")
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        file_obj = BytesIO()

        with pytest.raises(GCSDownloadError, match="File not found: missing.pdf"):
            client.download_to_file("missing.pdf", file_obj)

    @patch("src.storage.gcs_client.storage.Client")
    def test_download_to_file_generic_error(self, mock_storage_client):
        """Test download_to_file with generic error raises GCSDownloadError."""
        mock_blob = Mock()
        mock_blob.download_to_file.side_effect = Exception("Timeout")
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        file_obj = BytesIO()

        with pytest.raises(GCSDownloadError, match="Failed to download test.pdf"):
            client.download_to_file("test.pdf", file_obj)


class TestGCSClientDelete:
    """Test delete operations."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_delete_success(self, mock_storage_client):
        """Test successful deletion of file."""
        mock_blob = Mock()
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        client.delete("documents/old.pdf")

        mock_blob.delete.assert_called_once()

    @patch("src.storage.gcs_client.storage.Client")
    def test_delete_not_found_does_not_raise_error(self, mock_storage_client):
        """Test that deleting non-existent file does not raise error."""
        mock_blob = Mock()
        mock_blob.delete.side_effect = NotFound("Already deleted")
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")

        # Should not raise error
        client.delete("nonexistent.pdf")

    @patch("src.storage.gcs_client.storage.Client")
    def test_delete_generic_error_raises_gcs_error(self, mock_storage_client):
        """Test that generic delete errors raise GCSError."""
        mock_blob = Mock()
        mock_blob.delete.side_effect = Exception("Permission denied")
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")

        with pytest.raises(GCSError, match="Failed to delete test.pdf"):
            client.delete("test.pdf")


class TestGCSClientExists:
    """Test file existence checking."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_exists_returns_true_for_existing_file(self, mock_storage_client):
        """Test exists returns True for existing files."""
        mock_blob = Mock()
        mock_blob.exists.return_value = True
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        result = client.exists("documents/file.pdf")

        assert result is True
        mock_blob.exists.assert_called_once()

    @patch("src.storage.gcs_client.storage.Client")
    def test_exists_returns_false_for_nonexistent_file(self, mock_storage_client):
        """Test exists returns False for non-existent files."""
        mock_blob = Mock()
        mock_blob.exists.return_value = False
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        result = client.exists("missing.pdf")

        assert result is False


class TestGCSClientSignedURL:
    """Test signed URL generation."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_get_signed_url_default_params(self, mock_storage_client):
        """Test signed URL generation with default parameters."""
        mock_blob = Mock()
        expected_url = "https://storage.googleapis.com/signed-url"
        mock_blob.generate_signed_url.return_value = expected_url
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        result = client.get_signed_url("documents/file.pdf")

        assert result == expected_url
        # Verify call with default 15 minutes and GET method
        call_args = mock_blob.generate_signed_url.call_args
        assert call_args[1]["version"] == "v4"
        assert call_args[1]["method"] == "GET"

    @patch("src.storage.gcs_client.storage.Client")
    def test_get_signed_url_custom_params(self, mock_storage_client):
        """Test signed URL generation with custom parameters."""
        mock_blob = Mock()
        expected_url = "https://storage.googleapis.com/upload-signed-url"
        mock_blob.generate_signed_url.return_value = expected_url
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        client = GCSClient(bucket_name="test-bucket")
        result = client.get_signed_url(
            "uploads/file.pdf", expiration_minutes=30, method="PUT"
        )

        assert result == expected_url
        call_args = mock_blob.generate_signed_url.call_args
        assert call_args[1]["method"] == "PUT"


class TestGCSClientParseURI:
    """Test GCS URI parsing."""

    @patch("src.storage.gcs_client.storage.Client")
    def test_parse_gcs_uri_valid(self, mock_storage_client):
        """Test parsing valid gs:// URI."""
        client = GCSClient(bucket_name="test-bucket")
        bucket, path = client.parse_gcs_uri("gs://my-bucket/path/to/file.pdf")

        assert bucket == "my-bucket"
        assert path == "path/to/file.pdf"

    @patch("src.storage.gcs_client.storage.Client")
    def test_parse_gcs_uri_with_subdirectories(self, mock_storage_client):
        """Test parsing URI with multiple subdirectories."""
        client = GCSClient(bucket_name="test-bucket")
        bucket, path = client.parse_gcs_uri("gs://bucket/a/b/c/file.txt")

        assert bucket == "bucket"
        assert path == "a/b/c/file.txt"

    @patch("src.storage.gcs_client.storage.Client")
    def test_parse_gcs_uri_invalid_scheme(self, mock_storage_client):
        """Test parsing URI with invalid scheme raises ValueError."""
        client = GCSClient(bucket_name="test-bucket")

        with pytest.raises(ValueError, match="Invalid GCS URI format"):
            client.parse_gcs_uri("s3://bucket/file.pdf")

    @patch("src.storage.gcs_client.storage.Client")
    def test_parse_gcs_uri_missing_path(self, mock_storage_client):
        """Test parsing URI without path raises ValueError."""
        client = GCSClient(bucket_name="test-bucket")

        with pytest.raises(ValueError, match="Invalid GCS URI format"):
            client.parse_gcs_uri("gs://bucket-only")

    @patch("src.storage.gcs_client.storage.Client")
    def test_parse_gcs_uri_empty_string(self, mock_storage_client):
        """Test parsing empty string raises ValueError."""
        client = GCSClient(bucket_name="test-bucket")

        with pytest.raises(ValueError, match="Invalid GCS URI format"):
            client.parse_gcs_uri("")


class TestGCSClientExceptions:
    """Test custom exception classes."""

    def test_gcs_error_is_exception(self):
        """Test GCSError inherits from Exception."""
        error = GCSError("Test error")
        assert isinstance(error, Exception)

    def test_gcs_upload_error_is_gcs_error(self):
        """Test GCSUploadError inherits from GCSError."""
        error = GCSUploadError("Upload failed")
        assert isinstance(error, GCSError)
        assert isinstance(error, Exception)

    def test_gcs_download_error_is_gcs_error(self):
        """Test GCSDownloadError inherits from GCSError."""
        error = GCSDownloadError("Download failed")
        assert isinstance(error, GCSError)
        assert isinstance(error, Exception)
