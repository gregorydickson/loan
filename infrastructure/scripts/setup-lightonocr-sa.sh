#!/bin/bash
# LightOnOCR GPU Service Account Setup
# Creates dedicated service account for LightOnOCR GPU service
#
# Usage: ./setup-lightonocr-sa.sh [PROJECT_ID]
# If PROJECT_ID not provided, uses gcloud default project
#
# Note: IAM binding for run.invoker is handled in deploy.sh after service is created

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "$PROJECT_ID" ]]; then
    echo "Error: No project ID provided and no default project set"
    echo "Usage: $0 PROJECT_ID"
    exit 1
fi

SA_NAME="lightonocr-gpu"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Setting up LightOnOCR GPU service account for project: $PROJECT_ID"

# Create service account (idempotent - will skip if exists)
if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo "Service account $SA_EMAIL already exists, skipping creation"
else
    echo "Creating service account: $SA_NAME"
    gcloud iam service-accounts create "$SA_NAME" \
        --project="$PROJECT_ID" \
        --display-name="LightOnOCR GPU Service" \
        --description="Service account for LightOnOCR GPU service on Cloud Run"
fi

echo ""
echo "Service account setup complete!"
echo "Service account: $SA_EMAIL"
echo ""
echo "Next steps:"
echo "  1. Run infrastructure/lightonocr-gpu/deploy.sh to deploy the service"
echo "  2. IAM binding for backend invocation will be configured during deployment"
