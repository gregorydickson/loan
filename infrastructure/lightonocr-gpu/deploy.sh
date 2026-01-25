#!/bin/bash
# LightOnOCR GPU Service Deployment Script
# Builds Docker image, deploys to Cloud Run with L4 GPU, and configures IAM
#
# Prerequisites:
#   - Docker installed and running
#   - gcloud CLI authenticated with project access
#   - Service account created (run setup-lightonocr-sa.sh first)
#
# Usage: ./deploy.sh [PROJECT_ID] [REGION]
# Defaults: PROJECT_ID from gcloud config, REGION=us-central1

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-${1:-$(gcloud config get-value project 2>/dev/null)}}"
REGION="${REGION:-${2:-us-central1}}"
SERVICE_NAME="lightonocr-gpu"
AR_REPO="cloud-run-source-deploy"  # Default Artifact Registry repo
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${SERVICE_NAME}:latest"

if [[ -z "$PROJECT_ID" ]]; then
    echo "Error: No project ID provided and no default project set"
    echo "Usage: PROJECT_ID=<project> ./deploy.sh"
    echo "   or: ./deploy.sh <project_id> [region]"
    exit 1
fi

echo "=== LightOnOCR GPU Service Deployment ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Image: $IMAGE"
echo ""

# Step 0: Ensure Artifact Registry repo exists
echo "Ensuring Artifact Registry repository exists..."
gcloud artifacts repositories create "$AR_REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --quiet 2>/dev/null || echo "Repository $AR_REPO already exists"

# Configure Docker for Artifact Registry
echo "Configuring Docker authentication..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Step 1: Build and push Docker image
echo ""
echo "Building Docker image (this may take 10+ minutes for model download)..."
cd "$(dirname "$0")"
docker build -t "$IMAGE" .
docker push "$IMAGE"

# Step 2: Deploy to Cloud Run with GPU
echo ""
echo "Deploying to Cloud Run with L4 GPU..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE" \
    --service-account "lightonocr-gpu@${PROJECT_ID}.iam.gserviceaccount.com" \
    --cpu 8 \
    --memory 32Gi \
    --gpu 1 \
    --gpu-type nvidia-l4 \
    --port 8000 \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --no-allow-unauthenticated \
    --min-instances 0 \
    --max-instances 3 \
    --no-cpu-throttling \
    --no-gpu-zonal-redundancy \
    --startup-probe "tcpSocket.port=8000,initialDelaySeconds=240,failureThreshold=1,timeoutSeconds=240,periodSeconds=240"

# Step 3: Grant invoker role to backend service account
echo ""
echo "Granting backend service account permission to invoke GPU service..."
BACKEND_SA="backend-service@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
    --member "serviceAccount:${BACKEND_SA}" \
    --role roles/run.invoker \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --quiet

# Step 4: Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --format "value(status.url)")

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: $SERVICE_URL"
echo ""
echo "Verify deployment:"
echo "  # Get auth token"
echo "  TOKEN=\$(gcloud auth print-identity-token)"
echo "  # Health check"
echo "  curl -sf -H \"Authorization: Bearer \$TOKEN\" ${SERVICE_URL}/health"
echo ""
echo "Add to backend .env:"
echo "  LIGHTONOCR_SERVICE_URL=$SERVICE_URL"
