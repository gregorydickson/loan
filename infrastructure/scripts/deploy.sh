#!/bin/bash
# Automated deployment script
# Builds Docker images, pushes to Artifact Registry, and runs terraform apply
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID environment variable}"
REGION="${REGION:-us-central1}"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"

REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo"

echo "=========================================="
echo "Deploying Loan Extraction System"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Tag: $TAG"
echo "=========================================="

# Build and push backend
echo ""
echo "[1/4] Building backend..."
docker build -t "${REGISTRY}/backend:${TAG}" -t "${REGISTRY}/backend:latest" ./backend
echo "[2/4] Pushing backend..."
docker push "${REGISTRY}/backend:${TAG}"
docker push "${REGISTRY}/backend:latest"

# Build and push frontend
echo ""
echo "[3/4] Building frontend..."
docker build -t "${REGISTRY}/frontend:${TAG}" -t "${REGISTRY}/frontend:latest" ./frontend
echo "Pushing frontend..."
docker push "${REGISTRY}/frontend:${TAG}"
docker push "${REGISTRY}/frontend:latest"

# Apply Terraform
echo ""
echo "[4/4] Applying Terraform..."
cd infrastructure/terraform
terraform apply -auto-approve -var="image_tag=${TAG}"

# Get service URLs
BACKEND_URL=$(terraform output -raw backend_url 2>/dev/null || echo "not yet deployed")
FRONTEND_URL=$(terraform output -raw frontend_url 2>/dev/null || echo "not yet deployed")

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo "Backend URL: $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
echo ""
echo "Health check: curl ${BACKEND_URL}/health"
