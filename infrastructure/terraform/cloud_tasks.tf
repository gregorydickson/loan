# Cloud Tasks configuration for Loan Extraction application
# Async document processing queue with rate limiting and retry config

# Document processing queue
resource "google_cloud_tasks_queue" "document_processing" {
  name     = "document-processing"
  location = var.region

  # Rate limiting configuration
  # Controls how quickly tasks are dispatched
  rate_limits {
    max_dispatches_per_second = 10
    max_concurrent_dispatches = 5
  }

  # Retry configuration for failed tasks
  # Exponential backoff with maximum limits
  retry_config {
    max_attempts       = 5
    max_retry_duration = "3600s" # 1 hour total retry window
    max_backoff        = "3600s" # 1 hour maximum backoff
    min_backoff        = "10s"   # 10 second minimum backoff
    max_doublings      = 5       # Exponential backoff doublings
  }

  depends_on = [google_project_service.cloudtasks]
}

# Output the queue name for task creation
output "document_processing_queue_name" {
  description = "Name of the document processing Cloud Tasks queue"
  value       = google_cloud_tasks_queue.document_processing.name
}

output "document_processing_queue_id" {
  description = "Full resource ID of the document processing queue"
  value       = google_cloud_tasks_queue.document_processing.id
}
