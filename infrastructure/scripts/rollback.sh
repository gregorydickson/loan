#!/bin/bash
# rollback.sh - Cloud Run rollback helper
#
# Rolls back a Cloud Run service to a previous revision by shifting 100% traffic.
# If no revision is specified, lists recent revisions for selection.
#
# Usage:
#   ./rollback.sh SERVICE [REVISION]
#
# Examples:
#   ./rollback.sh loan-backend-prod                              # List revisions and prompt
#   ./rollback.sh loan-backend-prod loan-backend-prod-00042-abc  # Rollback to specific revision
#   REGION=us-west1 ./rollback.sh loan-frontend-prod             # Override region
#
# Environment Variables:
#   REGION - Cloud Run region (default: us-central1)
#   PROJECT_ID - GCP project (optional, uses gcloud default if not set)

set -euo pipefail

SERVICE="${1:?Usage: rollback.sh SERVICE [REVISION]}"
REGION="${REGION:-us-central1}"
REVISION="${2:-}"
PROJECT_FLAG=""

# Use PROJECT_ID if set
if [[ -n "${PROJECT_ID:-}" ]]; then
    PROJECT_FLAG="--project=${PROJECT_ID}"
fi

echo "=============================================="
echo "Cloud Run Rollback Helper"
echo "=============================================="
echo "Service: $SERVICE"
echo "Region:  $REGION"
echo ""

# If no revision specified, list recent revisions
if [[ -z "$REVISION" ]]; then
    echo "Recent revisions for $SERVICE:"
    echo ""
    gcloud run revisions list \
        --service="$SERVICE" \
        --region="$REGION" \
        $PROJECT_FLAG \
        --limit=5 \
        --format="table(name,active,created)" \
        --sort-by="~created"
    echo ""

    # Prompt for revision
    read -p "Enter revision name to rollback to: " REVISION

    if [[ -z "$REVISION" ]]; then
        echo "Error: No revision specified"
        exit 1
    fi
fi

# Confirm rollback
echo ""
echo "Rolling back $SERVICE to revision: $REVISION"
read -p "Continue? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Rollback cancelled"
    exit 0
fi

# Perform rollback
echo ""
echo "Shifting 100% traffic to $REVISION..."
gcloud run services update-traffic "$SERVICE" \
    --region="$REGION" \
    $PROJECT_FLAG \
    --to-revisions="${REVISION}=100"

# Verify rollback
echo ""
echo "Verifying traffic configuration..."
TRAFFIC=$(gcloud run services describe "$SERVICE" \
    --region="$REGION" \
    $PROJECT_FLAG \
    --format="value(status.traffic)")
echo "Current traffic: $TRAFFIC"

echo ""
echo "=============================================="
echo "Rollback complete!"
echo "=============================================="
echo ""
echo "To restore to latest revision after fix:"
echo "  gcloud run services update-traffic $SERVICE --region=$REGION --to-revisions=LATEST=100"
