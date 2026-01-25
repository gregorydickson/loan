#!/bin/bash
# setup-github-triggers.sh - Create GitHub triggers for CloudBuild
#
# Creates GitHub triggers for automatic builds on push to main branch.
# Each service has its own trigger with --included-files scoping so only
# relevant changes trigger builds.
#
# Prerequisites:
#   - GitHub repository connected to Cloud Build via Developer Connect
#     (One-time setup in Cloud Console: Cloud Build > Repositories > Connect Repository)
#   - Connection name known (created during Console setup, e.g., "github-connection")
#   - cloudbuild-deployer service account exists (run setup-service-account.sh)
#   - CloudBuild YAML files exist in infrastructure/cloudbuild/
#
# Usage:
#   ./setup-github-triggers.sh PROJECT_ID CONNECTION_NAME
#
# Examples:
#   ./setup-github-triggers.sh my-gcp-project github-connection
#   REGION=us-west1 REPO_NAME=loan-app ./setup-github-triggers.sh my-project my-connection
#
# Environment Variables:
#   REGION - Cloud Build region (default: us-central1)
#   REPO_NAME - GitHub repository name (default: loan)

set -euo pipefail

PROJECT_ID="${1:?Usage: setup-github-triggers.sh PROJECT_ID CONNECTION_NAME}"
CONNECTION_NAME="${2:?Usage: setup-github-triggers.sh PROJECT_ID CONNECTION_NAME}"
REGION="${REGION:-us-central1}"
REPO_NAME="${REPO_NAME:-loan}"

echo "=============================================="
echo "GitHub Trigger Setup"
echo "=============================================="
echo "Project:    $PROJECT_ID"
echo "Connection: $CONNECTION_NAME"
echo "Region:     $REGION"
echo "Repo:       $REPO_NAME"
echo ""

# Service account for CloudBuild triggers
SA_EMAIL="cloudbuild-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

# Repository path for triggers
REPO_PATH="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION_NAME}/repositories/${REPO_NAME}"

echo "Creating backend-deploy trigger..."
echo "----------------------------------------------"

# Check if trigger already exists
if gcloud builds triggers describe backend-deploy --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "Trigger 'backend-deploy' already exists, skipping..."
else
    gcloud builds triggers create github \
        --name="backend-deploy" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --repository="$REPO_PATH" \
        --branch-pattern="^main$" \
        --build-config="infrastructure/cloudbuild/backend-cloudbuild.yaml" \
        --service-account="projects/${PROJECT_ID}/serviceAccounts/${SA_EMAIL}" \
        --included-files="backend/**,infrastructure/cloudbuild/backend-cloudbuild.yaml"
    echo "Created trigger: backend-deploy"
fi
echo ""

echo "Creating frontend-deploy trigger..."
echo "----------------------------------------------"

# Check if trigger already exists
if gcloud builds triggers describe frontend-deploy --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "Trigger 'frontend-deploy' already exists, skipping..."
else
    gcloud builds triggers create github \
        --name="frontend-deploy" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --repository="$REPO_PATH" \
        --branch-pattern="^main$" \
        --build-config="infrastructure/cloudbuild/frontend-cloudbuild.yaml" \
        --service-account="projects/${PROJECT_ID}/serviceAccounts/${SA_EMAIL}" \
        --included-files="frontend/**,infrastructure/cloudbuild/frontend-cloudbuild.yaml" \
        --substitutions="_BACKEND_URL=https://loan-backend-prod-PLACEHOLDER.run.app"
    echo "Created trigger: frontend-deploy"
    echo ""
    echo "NOTE: Update _BACKEND_URL substitution after backend is deployed:"
    echo "  gcloud builds triggers update frontend-deploy --region=$REGION --update-substitutions=_BACKEND_URL=<actual-url>"
fi
echo ""

echo "Creating gpu-deploy trigger..."
echo "----------------------------------------------"

# Check if trigger already exists
if gcloud builds triggers describe gpu-deploy --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "Trigger 'gpu-deploy' already exists, skipping..."
else
    gcloud builds triggers create github \
        --name="gpu-deploy" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --repository="$REPO_PATH" \
        --branch-pattern="^main$" \
        --build-config="infrastructure/cloudbuild/gpu-cloudbuild.yaml" \
        --service-account="projects/${PROJECT_ID}/serviceAccounts/${SA_EMAIL}" \
        --included-files="infrastructure/lightonocr-gpu/**,infrastructure/cloudbuild/gpu-cloudbuild.yaml"
    echo "Created trigger: gpu-deploy"
fi
echo ""

echo "=============================================="
echo "Trigger Setup Complete"
echo "=============================================="
echo ""
echo "Created triggers:"
gcloud builds triggers list \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --filter="name:(backend-deploy OR frontend-deploy OR gpu-deploy)" \
    --format="table(name,createTime,triggerTemplate.branchName)"
echo ""
echo "Next steps:"
echo "  1. Verify triggers in Console: https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
echo "  2. After backend deployment, update frontend trigger's _BACKEND_URL"
echo "  3. Push to main branch to test triggers"
echo "  4. Monitor builds: https://console.cloud.google.com/cloud-build/builds?project=$PROJECT_ID"
