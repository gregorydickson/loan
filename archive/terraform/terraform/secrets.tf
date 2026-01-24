# Secret Manager configuration for Loan Extraction application
# Secrets are stored in Secret Manager, not in Terraform state

# Database URL secret - constructed from Cloud SQL outputs
resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

# Database URL secret version - asyncpg connection string
resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql+asyncpg://app:${var.db_password}@${google_sql_database_instance.main.private_ip_address}:5432/loan_extraction"

  depends_on = [
    google_sql_database_instance.main,
    google_sql_database.loan_extraction,
    google_sql_user.app
  ]
}

# Gemini API key secret
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

# Gemini API key secret version
resource "google_secret_manager_secret_version" "gemini_api_key" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key
}

# IAM binding for Cloud Run service account to access database URL secret
resource "google_secret_manager_secret_iam_member" "database_url_access" {
  secret_id = google_secret_manager_secret.database_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# IAM binding for Cloud Run service account to access Gemini API key secret
resource "google_secret_manager_secret_iam_member" "gemini_api_key_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Output secret resource names for Cloud Run configuration
output "database_url_secret_id" {
  description = "Secret ID for database URL in Secret Manager"
  value       = google_secret_manager_secret.database_url.secret_id
}

output "gemini_api_key_secret_id" {
  description = "Secret ID for Gemini API key in Secret Manager"
  value       = google_secret_manager_secret.gemini_api_key.secret_id
}
