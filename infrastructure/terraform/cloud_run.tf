# Cloud Run service configuration for Loan Extraction application
# Backend and frontend services with VPC egress for Cloud SQL connectivity

# Backend Cloud Run service
resource "google_cloud_run_v2_service" "backend" {
  name     = "loan-backend-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run_sa.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/loan-repo/backend:${var.image_tag}"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi" # Docling tableformer models need 2GB+ for PDF processing
        }
        cpu_idle = true # Scale to zero when not processing requests
      }

      # Database URL from Secret Manager
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      # Gemini API key from Secret Manager
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      # GCS bucket name for document storage
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.documents.name
      }

      # Cloud Tasks queue path for async processing
      env {
        name  = "CLOUD_TASKS_QUEUE"
        value = google_cloud_tasks_queue.document_processing.id
      }

      ports {
        container_port = 8080
      }

      # Startup probe for health check
      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
      }
    }

    # Direct VPC egress for Cloud SQL access via private IP
    # No VPC connector cost - uses network_interfaces instead
    vpc_access {
      network_interfaces {
        network    = google_compute_network.private_network.id
        subnetwork = google_compute_subnetwork.cloud_run_subnet.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 0  # Scale to zero
      max_instance_count = 10 # Handle spikes
    }
  }

  depends_on = [
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.gemini_api_key,
    google_project_service.run,
  ]
}

# Frontend Cloud Run service
resource "google_cloud_run_v2_service" "frontend" {
  name     = "loan-frontend-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/loan-repo/frontend:${var.image_tag}"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi" # Frontend is lighter than backend
        }
        cpu_idle = true # Scale to zero
      }

      # Backend API URL for frontend to call
      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = google_cloud_run_v2_service.backend.uri
      }

      ports {
        container_port = 8080
      }
    }

    scaling {
      min_instance_count = 0 # Scale to zero
      max_instance_count = 5 # Typically less load than backend
    }
  }

  depends_on = [
    google_cloud_run_v2_service.backend,
    google_project_service.run,
  ]
}

# IAM binding for public access to backend service
# Allows unauthenticated requests (API is public)
resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  name     = google_cloud_run_v2_service.backend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# IAM binding for public access to frontend service
# Allows unauthenticated requests (web app is public)
resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  name     = google_cloud_run_v2_service.frontend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
