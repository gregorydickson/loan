"""Cloud Tasks client for async document processing.

Creates HTTP target tasks with OIDC authentication for Cloud Run.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from google.cloud import tasks_v2
from google.protobuf import duration_pb2

logger = logging.getLogger(__name__)


class CloudTasksClient:
    """Client for creating Cloud Tasks to process documents.

    Creates HTTP POST tasks targeting /api/tasks/process-document
    with OIDC authentication for secure Cloud Run invocation.
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        queue_id: str,
        service_url: str,
        service_account_email: str,
    ) -> None:
        """Initialize Cloud Tasks client.

        Args:
            project_id: GCP project ID
            location: GCP region (e.g., us-central1)
            queue_id: Cloud Tasks queue name
            service_url: Cloud Run service URL for callbacks
            service_account_email: Service account for OIDC token
        """
        self.client = tasks_v2.CloudTasksClient()
        self.queue_path = self.client.queue_path(project_id, location, queue_id)
        self.service_url = service_url.rstrip("/")  # Remove trailing slash
        self.service_account_email = service_account_email

        logger.info(
            "CloudTasksClient initialized: queue=%s, target=%s",
            self.queue_path,
            self.service_url,
        )

    def create_document_processing_task(
        self,
        document_id: UUID,
        filename: str,
    ) -> tasks_v2.Task:
        """Create a task to process a document.

        Args:
            document_id: Document UUID to process
            filename: Original filename (for logging)

        Returns:
            Created Cloud Task
        """
        payload = json.dumps({
            "document_id": str(document_id),
            "filename": filename,
        }).encode()

        # Construct target URL
        target_url = f"{self.service_url}/api/tasks/process-document"

        # Task with OIDC authentication for Cloud Run
        task = tasks_v2.Task(
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=target_url,
                headers={"Content-Type": "application/json"},
                body=payload,
                oidc_token=tasks_v2.OidcToken(
                    service_account_email=self.service_account_email,
                    audience=self.service_url,
                ),
            ),
            # 10-minute timeout per attempt
            dispatch_deadline=duration_pb2.Duration(seconds=600),
        )

        created_task = self.client.create_task(
            tasks_v2.CreateTaskRequest(
                parent=self.queue_path,
                task=task,
            )
        )

        logger.info(
            "Created task for document %s: %s",
            document_id,
            created_task.name,
        )

        return created_task
