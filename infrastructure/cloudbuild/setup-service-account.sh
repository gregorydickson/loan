#!/bin/bash
# CloudBuild Service Account Setup
# Creates dedicated service account with least-privilege permissions for Cloud Run deployments
#
# Usage: ./setup-service-account.sh [PROJECT_ID]
# If PROJECT_ID not provided, uses gcloud default project

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "$PROJECT_ID" ]]; then
    echo "Error: No project ID provided and no default project set"
    echo "Usage: $0 PROJECT_ID"
    exit 1
fi

SA_NAME="cloudbuild-deployer"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Setting up CloudBuild service account for project: $PROJECT_ID"

# Create service account (idempotent - will skip if exists)
if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo "Service account $SA_EMAIL already exists, skipping creation"
else
    echo "Creating service account: $SA_NAME"
    gcloud iam service-accounts create "$SA_NAME" \
        --project="$PROJECT_ID" \
        --display-name="CloudBuild Deployer Service Account" \
        --description="Service account for CloudBuild deployments to Cloud Run"
fi

# Required IAM roles for Cloud Run deployment
ROLES=(
    "roles/run.developer"              # Deploy Cloud Run services
    "roles/iam.serviceAccountUser"     # Act as runtime service account
    "roles/artifactregistry.writer"    # Push container images
    "roles/secretmanager.secretAccessor" # Read secrets during build
    "roles/logging.logWriter"          # Write build logs
)

echo "Granting IAM roles to $SA_EMAIL"
for role in "${ROLES[@]}"; do
    echo "  Granting: $role"
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$role" \
        --condition=None \
        --quiet
done

echo ""
echo "CloudBuild service account setup complete!"
echo "Service account: $SA_EMAIL"
echo ""
echo "Roles granted:"
for role in "${ROLES[@]}"; do
    echo "  - $role"
done
echo ""
echo "Next steps:"
echo "  1. Configure CloudBuild triggers to use this service account"
echo "  2. Create cloudbuild.yaml files for each service"
