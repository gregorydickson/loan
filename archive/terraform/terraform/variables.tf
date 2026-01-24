# Terraform variables for Loan Extraction GCP Infrastructure

variable "project_id" {
  description = "GCP project ID where resources will be created"
  type        = string
}

variable "region" {
  description = "GCP region for resource deployment"
  type        = string
  default     = "us-central1"
}

variable "db_password" {
  description = "Database password for Cloud SQL PostgreSQL instance"
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Google Gemini API key for LLM extraction"
  type        = string
  sensitive   = true
}

variable "image_tag" {
  description = "Docker image tag for Cloud Run deployments"
  type        = string
  default     = "latest"
}

variable "environment" {
  description = "Environment name for resource naming (e.g., prod, staging)"
  type        = string
  default     = "prod"
}
