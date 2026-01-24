# IAM Service Account and Role Bindings for Cloud Run services
# Following least-privilege principle - only grant permissions the backend needs

# Service Account for Cloud Run services
resource "google_service_account" "cloud_run_sa" {
  account_id   = "loan-cloud-run"
  display_name = "Loan Extraction Cloud Run Service Account"
}

# Role: Cloud SQL Client - Connect to Cloud SQL database
resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Role: Secret Manager Secret Accessor - Read secrets
resource "google_project_iam_member" "secretmanager_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Role: Cloud Tasks Enqueuer - Create and manage Cloud Tasks
resource "google_project_iam_member" "cloudtasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Role: Logging Log Writer - Write application logs
resource "google_project_iam_member" "logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Role: Cloud Run Invoker - Allow service account to invoke Cloud Run
# Required for Cloud Tasks OIDC authentication when calling /api/tasks/process-document
resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Local value for service account email - used by other files (e.g., storage IAM)
locals {
  cloud_run_service_account_email = google_service_account.cloud_run_sa.email
}
