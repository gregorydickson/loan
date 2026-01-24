# Cloud Storage configuration for Loan Extraction application
# Document storage bucket with lifecycle policies and uniform access

# Documents storage bucket
resource "google_storage_bucket" "documents" {
  name          = "${var.project_id}-loan-documents"
  location      = var.region
  force_destroy = false

  # Uniform bucket-level access (no per-object ACLs)
  uniform_bucket_level_access = true

  # Block all public access
  public_access_prevention = "enforced"

  # Enable versioning for document recovery
  versioning {
    enabled = true
  }

  # Lifecycle rule: Move to NEARLINE after 90 days
  # Reduces cost for infrequently accessed documents
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  # Lifecycle rule: Move to COLDLINE after 365 days
  # Further reduces cost for rarely accessed documents
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  # Lifecycle rule: Delete old versions, keep last 5
  # Prevents unlimited version accumulation
  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }
}

# IAM binding for Cloud Run service account to access documents bucket
resource "google_storage_bucket_iam_member" "documents_access" {
  bucket = google_storage_bucket.documents.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Output the bucket name for configuration
output "documents_bucket_name" {
  description = "Name of the document storage bucket"
  value       = google_storage_bucket.documents.name
}

output "documents_bucket_url" {
  description = "URL of the document storage bucket"
  value       = google_storage_bucket.documents.url
}
