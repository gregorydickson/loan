#!/bin/bash
# GCP project initialization script
# Enables required APIs, creates Artifact Registry, and prepares Terraform state bucket
set -euo pipefail

PROJECT_ID="${1:?Usage: setup-gcp.sh PROJECT_ID [REGION]}"
REGION="${2:-us-central1}"

echo "Setting up GCP project: $PROJECT_ID in region: $REGION"

# Set project
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    cloudtasks.googleapis.com \
    servicenetworking.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    compute.googleapis.com

# Create Artifact Registry repository
echo "Creating Artifact Registry repository..."
gcloud artifacts repositories create loan-repo \
    --repository-format=docker \
    --location="$REGION" \
    --description="Loan extraction Docker images" \
    2>/dev/null || echo "Repository already exists"

# Configure Docker authentication
echo "Configuring Docker authentication..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Create Terraform state bucket
STATE_BUCKET="${PROJECT_ID}-terraform-state"
echo "Creating Terraform state bucket: $STATE_BUCKET"
gsutil mb -l "$REGION" "gs://${STATE_BUCKET}" 2>/dev/null || echo "Bucket already exists"
gsutil versioning set on "gs://${STATE_BUCKET}"

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. cd infrastructure/terraform && terraform init"
echo "2. Set TF_VAR_project_id, TF_VAR_db_password, TF_VAR_gemini_api_key environment variables"
echo "3. Run: terraform plan"
echo "4. Run: terraform apply"
