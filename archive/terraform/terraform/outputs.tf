# Terraform outputs for Loan Extraction GCP Infrastructure
# Provides service URLs and connection information after deployment

# Cloud Run service URLs
output "backend_url" {
  description = "Backend Cloud Run service URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  description = "Frontend Cloud Run service URL"
  value       = google_cloud_run_v2_service.frontend.uri
}

# Cloud SQL database information
output "database_instance" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.main.name
}

output "database_connection_name" {
  description = "Cloud SQL connection name for proxy"
  value       = google_sql_database_instance.main.connection_name
}

output "database_private_ip" {
  description = "Cloud SQL private IP address"
  value       = google_sql_database_instance.main.private_ip_address
}

# Cloud Storage bucket
output "storage_bucket" {
  description = "GCS bucket for document storage"
  value       = google_storage_bucket.documents.name
}

# Cloud Tasks queue
output "cloud_tasks_queue" {
  description = "Cloud Tasks queue path"
  value       = google_cloud_tasks_queue.document_processing.id
}
