"""Unit tests for CloudTasksClient."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest


class TestCloudTasksClient:
    """Tests for CloudTasksClient task creation."""

    @pytest.fixture
    def mock_gcp_client(self):
        """Mock only the google.cloud.tasks_v2.CloudTasksClient class.

        This allows real Task and CreateTaskRequest objects to be created
        so we can inspect their properties.
        """
        with patch(
            "src.ingestion.cloud_tasks_client.tasks_v2.CloudTasksClient"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.queue_path.return_value = (
                "projects/test-project/locations/us-central1/queues/test-queue"
            )

            # Mock the task creation response
            mock_task = MagicMock()
            mock_task.name = (
                "projects/test-project/locations/us-central1/queues/test-queue/tasks/123"
            )
            mock_client.create_task.return_value = mock_task

            yield mock_client

    def test_init_creates_client_with_queue_path(self, mock_gcp_client):
        """Test CloudTasksClient initializes with correct queue path."""
        from src.ingestion.cloud_tasks_client import CloudTasksClient

        client = CloudTasksClient(
            project_id="test-project",
            location="us-central1",
            queue_id="test-queue",
            service_url="https://backend.example.com",
            service_account_email="sa@test-project.iam.gserviceaccount.com",
        )

        mock_gcp_client.queue_path.assert_called_once_with(
            "test-project", "us-central1", "test-queue"
        )
        assert client.service_url == "https://backend.example.com"
        assert client.service_account_email == "sa@test-project.iam.gserviceaccount.com"

    def test_init_strips_trailing_slash_from_service_url(self, mock_gcp_client):
        """Test service URL has trailing slash removed."""
        from src.ingestion.cloud_tasks_client import CloudTasksClient

        client = CloudTasksClient(
            project_id="test-project",
            location="us-central1",
            queue_id="test-queue",
            service_url="https://backend.example.com/",
            service_account_email="sa@test-project.iam.gserviceaccount.com",
        )

        assert client.service_url == "https://backend.example.com"

    def test_create_document_processing_task_calls_create_task(self, mock_gcp_client):
        """Test task creation calls create_task with correct request."""
        from src.ingestion.cloud_tasks_client import CloudTasksClient

        client = CloudTasksClient(
            project_id="test-project",
            location="us-central1",
            queue_id="test-queue",
            service_url="https://backend.example.com",
            service_account_email="sa@test-project.iam.gserviceaccount.com",
        )

        document_id = UUID("12345678-1234-5678-1234-567812345678")
        client.create_document_processing_task(
            document_id=document_id,
            filename="test.pdf",
        )

        # Verify create_task was called
        mock_gcp_client.create_task.assert_called_once()

        # Extract the CreateTaskRequest from the call
        call_args = mock_gcp_client.create_task.call_args
        request = call_args[0][0]  # First positional argument

        # Verify parent queue path
        assert (
            request.parent
            == "projects/test-project/locations/us-central1/queues/test-queue"
        )

        # Verify task HTTP request properties
        task = request.task
        http_request = task.http_request

        # URL should include the handler endpoint
        assert http_request.url == "https://backend.example.com/api/tasks/process-document"

        # Verify Content-Type header
        assert http_request.headers["Content-Type"] == "application/json"

        # Verify payload
        payload = json.loads(http_request.body.decode())
        assert payload["document_id"] == str(document_id)
        assert payload["filename"] == "test.pdf"

    def test_create_task_configures_oidc_token(self, mock_gcp_client):
        """Test task creation configures OIDC token for Cloud Run auth."""
        from src.ingestion.cloud_tasks_client import CloudTasksClient

        client = CloudTasksClient(
            project_id="test-project",
            location="us-central1",
            queue_id="test-queue",
            service_url="https://backend.example.com",
            service_account_email="sa@test-project.iam.gserviceaccount.com",
        )

        document_id = UUID("12345678-1234-5678-1234-567812345678")
        client.create_document_processing_task(
            document_id=document_id,
            filename="test.pdf",
        )

        call_args = mock_gcp_client.create_task.call_args
        request = call_args[0][0]
        oidc_token = request.task.http_request.oidc_token

        # Verify OIDC token configuration
        assert oidc_token.service_account_email == "sa@test-project.iam.gserviceaccount.com"
        assert oidc_token.audience == "https://backend.example.com"

    def test_create_task_returns_task_object(self, mock_gcp_client):
        """Test that create_document_processing_task returns the created task."""
        from src.ingestion.cloud_tasks_client import CloudTasksClient

        client = CloudTasksClient(
            project_id="test-project",
            location="us-central1",
            queue_id="test-queue",
            service_url="https://backend.example.com",
            service_account_email="sa@test-project.iam.gserviceaccount.com",
        )

        document_id = UUID("12345678-1234-5678-1234-567812345678")
        result = client.create_document_processing_task(
            document_id=document_id,
            filename="test.pdf",
        )

        assert result.name == (
            "projects/test-project/locations/us-central1/queues/test-queue/tasks/123"
        )

    def test_queue_path_stored_correctly(self, mock_gcp_client):
        """Test that queue_path is stored and accessible."""
        from src.ingestion.cloud_tasks_client import CloudTasksClient

        client = CloudTasksClient(
            project_id="test-project",
            location="us-central1",
            queue_id="test-queue",
            service_url="https://backend.example.com",
            service_account_email="sa@test-project.iam.gserviceaccount.com",
        )

        assert client.queue_path == (
            "projects/test-project/locations/us-central1/queues/test-queue"
        )

    def test_create_task_uses_post_method(self, mock_gcp_client):
        """Test that task uses HTTP POST method."""
        from google.cloud import tasks_v2

        from src.ingestion.cloud_tasks_client import CloudTasksClient

        client = CloudTasksClient(
            project_id="test-project",
            location="us-central1",
            queue_id="test-queue",
            service_url="https://backend.example.com",
            service_account_email="sa@test-project.iam.gserviceaccount.com",
        )

        document_id = UUID("12345678-1234-5678-1234-567812345678")
        client.create_document_processing_task(
            document_id=document_id,
            filename="test.pdf",
        )

        call_args = mock_gcp_client.create_task.call_args
        request = call_args[0][0]

        # Verify HTTP method is POST
        assert request.task.http_request.http_method == tasks_v2.HttpMethod.POST

    def test_create_task_sets_dispatch_deadline(self, mock_gcp_client):
        """Test that task has 10-minute dispatch deadline for Docling processing."""
        from src.ingestion.cloud_tasks_client import CloudTasksClient

        client = CloudTasksClient(
            project_id="test-project",
            location="us-central1",
            queue_id="test-queue",
            service_url="https://backend.example.com",
            service_account_email="sa@test-project.iam.gserviceaccount.com",
        )

        document_id = UUID("12345678-1234-5678-1234-567812345678")
        client.create_document_processing_task(
            document_id=document_id,
            filename="test.pdf",
        )

        call_args = mock_gcp_client.create_task.call_args
        request = call_args[0][0]

        # Verify dispatch deadline is 600 seconds (10 minutes)
        assert request.task.dispatch_deadline.seconds == 600
