# Terraform configuration for Loan Extraction GCP Infrastructure
# Provider configuration and API enablement

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.0.0"
    }
  }

  # GCS backend for remote state - bucket name from variable
  # Initialize with: terraform init -backend-config="bucket=${TF_STATE_BUCKET}"
  backend "gcs" {
    prefix = "terraform/state"
  }
}

# Google Cloud Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required GCP APIs
# Using disable_dependent_services = false and disable_on_destroy = false
# to avoid accidentally disabling APIs that other resources depend on

resource "google_project_service" "compute" {
  service                    = "compute.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_project_service" "run" {
  service                    = "run.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_project_service" "sqladmin" {
  service                    = "sqladmin.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_project_service" "secretmanager" {
  service                    = "secretmanager.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_project_service" "cloudtasks" {
  service                    = "cloudtasks.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_project_service" "servicenetworking" {
  service                    = "servicenetworking.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_project_service" "artifactregistry" {
  service                    = "artifactregistry.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy         = false
}
