#!/bin/bash
# provision-infra.sh - One-time gcloud CLI infrastructure provisioning
#
# Creates foundational GCP infrastructure for the loan extraction application:
# - VPC network with Cloud Run subnet
# - VPC peering for Cloud SQL private connectivity
# - Cloud SQL PostgreSQL instance
# - Cloud Tasks queue for document processing
#
# All commands are idempotent - safe to re-run.
#
# Usage:
#   ./provision-infra.sh PROJECT_ID [REGION]
#
# Example:
#   ./provision-infra.sh my-gcp-project us-central1

set -euo pipefail

PROJECT_ID="${1:?Usage: provision-infra.sh PROJECT_ID [REGION]}"
REGION="${2:-us-central1}"

echo "=============================================="
echo "Provisioning infrastructure for: $PROJECT_ID"
echo "Region: $REGION"
echo "=============================================="
echo ""

# Set project for all commands
gcloud config set project "$PROJECT_ID"

# ============================================
# Step 1: Enable required APIs
# ============================================
echo "[1/7] Enabling required APIs..."
gcloud services enable \
    compute.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    cloudtasks.googleapis.com \
    servicenetworking.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    --project="$PROJECT_ID"
echo "      APIs enabled"

# ============================================
# Step 2: Create VPC network
# ============================================
echo "[2/7] Creating VPC network..."
if gcloud compute networks describe "${PROJECT_ID}-vpc" --project="$PROJECT_ID" &>/dev/null; then
    echo "      VPC ${PROJECT_ID}-vpc already exists"
else
    gcloud compute networks create "${PROJECT_ID}-vpc" \
        --project="$PROJECT_ID" \
        --subnet-mode=custom
    echo "      VPC ${PROJECT_ID}-vpc created"
fi

# ============================================
# Step 3: Create Cloud Run subnet
# ============================================
echo "[3/7] Creating Cloud Run subnet..."
if gcloud compute networks subnets describe cloud-run-subnet --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "      Subnet cloud-run-subnet already exists"
else
    gcloud compute networks subnets create cloud-run-subnet \
        --project="$PROJECT_ID" \
        --network="${PROJECT_ID}-vpc" \
        --region="$REGION" \
        --range=10.0.0.0/24 \
        --enable-private-ip-google-access
    echo "      Subnet cloud-run-subnet created"
fi

# ============================================
# Step 4: Allocate private IP range for VPC peering
# ============================================
echo "[4/7] Allocating private IP range for VPC peering..."
if gcloud compute addresses describe private-ip-address --global --project="$PROJECT_ID" &>/dev/null; then
    echo "      IP range private-ip-address already allocated"
else
    gcloud compute addresses create private-ip-address \
        --project="$PROJECT_ID" \
        --global \
        --purpose=VPC_PEERING \
        --addresses=10.1.0.0 \
        --prefix-length=16 \
        --network="${PROJECT_ID}-vpc"
    echo "      IP range private-ip-address allocated"
fi

# ============================================
# Step 5: Create VPC peering for Cloud SQL
# ============================================
echo "[5/7] Creating VPC peering for Cloud SQL..."
# Check if peering already exists
if gcloud services vpc-peerings list --network="${PROJECT_ID}-vpc" --project="$PROJECT_ID" 2>/dev/null | grep -q "servicenetworking.googleapis.com"; then
    echo "      VPC peering already exists"
else
    gcloud services vpc-peerings connect \
        --service=servicenetworking.googleapis.com \
        --ranges=private-ip-address \
        --network="${PROJECT_ID}-vpc" \
        --project="$PROJECT_ID"
    echo "      VPC peering created (may take 1-2 minutes to complete)"
fi

# ============================================
# Step 6: Create Cloud SQL instance
# ============================================
echo "[6/7] Creating Cloud SQL instance..."
if gcloud sql instances describe loan-db-prod --project="$PROJECT_ID" &>/dev/null; then
    echo "      Cloud SQL instance loan-db-prod already exists"
else
    echo "      Creating Cloud SQL instance (this may take 5-10 minutes)..."
    gcloud sql instances create loan-db-prod \
        --project="$PROJECT_ID" \
        --database-version=POSTGRES_16 \
        --tier=db-f1-micro \
        --region="$REGION" \
        --network="projects/${PROJECT_ID}/global/networks/${PROJECT_ID}-vpc" \
        --no-assign-ip \
        --storage-type=SSD \
        --storage-size=10GB \
        --availability-type=ZONAL \
        --no-deletion-protection
    echo "      Cloud SQL instance loan-db-prod created"
fi

# Create database
echo "      Creating database loan_extraction..."
if gcloud sql databases describe loan_extraction --instance=loan-db-prod --project="$PROJECT_ID" &>/dev/null; then
    echo "      Database loan_extraction already exists"
else
    gcloud sql databases create loan_extraction \
        --instance=loan-db-prod \
        --project="$PROJECT_ID"
    echo "      Database loan_extraction created"
fi

# ============================================
# Step 7: Create Cloud Tasks queue
# ============================================
echo "[7/7] Creating Cloud Tasks queue..."
if gcloud tasks queues describe document-processing --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "      Queue document-processing already exists"
else
    gcloud tasks queues create document-processing \
        --location="$REGION" \
        --project="$PROJECT_ID" \
        --max-dispatches-per-second=10 \
        --max-concurrent-dispatches=5 \
        --max-attempts=5 \
        --min-backoff=10s \
        --max-backoff=3600s
    echo "      Queue document-processing created"
fi

echo ""
echo "=============================================="
echo "Infrastructure provisioning complete!"
echo "=============================================="
echo ""
echo "Summary of resources:"
echo "  - VPC: ${PROJECT_ID}-vpc"
echo "  - Subnet: cloud-run-subnet (10.0.0.0/24)"
echo "  - VPC Peering: private-ip-address (10.1.0.0/16)"
echo "  - Cloud SQL: loan-db-prod (PostgreSQL 16)"
echo "  - Database: loan_extraction"
echo "  - Cloud Tasks: document-processing"
echo ""
echo "Next steps:"
echo "  1. Create database user: gcloud sql users create USER --instance=loan-db-prod --password=PASSWORD"
echo "  2. Store connection string in Secret Manager"
echo "  3. Run setup-service-account.sh to create CloudBuild SA"
echo "  4. Set up GitHub connection in Cloud Console"
echo "  5. Create CloudBuild triggers for deployments"
