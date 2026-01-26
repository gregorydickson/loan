#!/bin/bash
# LightOnOCR Service Prerequisites Checker
# Validates environment before deploying GPU OCR service
#
# Usage: ./check-ocr-prerequisites.sh [PROJECT_ID]

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
REGION="us-central1"

if [[ -z "$PROJECT_ID" ]]; then
    echo "❌ Error: No project ID provided and no default project set"
    echo "Usage: $0 PROJECT_ID"
    exit 1
fi

echo "=================================================="
echo "LightOnOCR Prerequisites Check"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ISSUES=0

# Check 1: GCP Authentication
echo "1. Checking GCP authentication..."
ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
if [[ -n "$ACCOUNT" ]]; then
    echo -e "${GREEN}✓${NC} Authenticated as: $ACCOUNT"
else
    echo -e "${RED}✗${NC} Not authenticated. Run: gcloud auth login"
    ((ISSUES++))
fi
echo ""

# Check 2: Project Access
echo "2. Checking project access..."
if gcloud projects describe "$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}✓${NC} Can access project: $PROJECT_ID"
else
    echo -e "${RED}✗${NC} Cannot access project: $PROJECT_ID"
    echo "  Contact project owner for access"
    ((ISSUES++))
fi
echo ""

# Check 3: Required APIs
echo "3. Checking required APIs..."
REQUIRED_APIS=(
    "run.googleapis.com"
    "artifactregistry.googleapis.com"
    "cloudbuild.googleapis.com"
    "compute.googleapis.com"
)

for API in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --project="$PROJECT_ID" --filter="name:${API}" --format="value(name)" 2>/dev/null | grep -q "$API"; then
        echo -e "${GREEN}✓${NC} $API enabled"
    else
        echo -e "${RED}✗${NC} $API not enabled"
        echo "  Run: gcloud services enable $API --project=$PROJECT_ID"
        ((ISSUES++))
    fi
done
echo ""

# Check 4: GPU Quota
echo "4. Checking L4 GPU quota..."
if GPU_QUOTA=$(gcloud compute regions describe us-central1 --project="$PROJECT_ID" --format="json" 2>/dev/null | grep -A 2 "NVIDIA_L4_GPUS" || echo ""); then
    if [[ -n "$GPU_QUOTA" ]]; then
        LIMIT=$(echo "$GPU_QUOTA" | grep -o '"limit": [0-9]*' | grep -o '[0-9]*' || echo "0")
        if [[ "$LIMIT" -gt 0 ]]; then
            echo -e "${GREEN}✓${NC} L4 GPU quota available: $LIMIT"
        else
            echo -e "${RED}✗${NC} L4 GPU quota is 0"
            echo "  Request quota at: https://console.cloud.google.com/iam-admin/quotas?project=$PROJECT_ID"
            ((ISSUES++))
        fi
    else
        echo -e "${YELLOW}⚠${NC} Could not check GPU quota (may require compute.regions.get permission)"
    fi
else
    echo -e "${YELLOW}⚠${NC} Could not check GPU quota"
fi
echo ""

# Check 5: Artifact Registry Repository
echo "5. Checking Artifact Registry repository..."
if gcloud artifacts repositories describe loan-repo --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}✓${NC} Repository 'loan-repo' exists"
else
    echo -e "${RED}✗${NC} Repository 'loan-repo' not found"
    echo "  Run: gcloud artifacts repositories create loan-repo --repository-format=docker --location=$REGION --project=$PROJECT_ID"
    ((ISSUES++))
fi
echo ""

# Check 6: Service Accounts
echo "6. Checking service accounts..."

# LightOnOCR GPU service account
if gcloud iam service-accounts describe "lightonocr-gpu@${PROJECT_ID}.iam.gserviceaccount.com" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}✓${NC} Service account 'lightonocr-gpu' exists"
else
    echo -e "${RED}✗${NC} Service account 'lightonocr-gpu' not found"
    echo "  Run: infrastructure/scripts/setup-lightonocr-sa.sh $PROJECT_ID"
    ((ISSUES++))
fi

# Backend service account
if gcloud iam service-accounts describe "loan-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}✓${NC} Service account 'loan-cloud-run' exists"
else
    echo -e "${YELLOW}⚠${NC} Service account 'loan-cloud-run' not found"
    echo "  This will be needed for backend deployment"
fi
echo ""

# Check 7: Existing LightOnOCR Service
echo "7. Checking if LightOnOCR service exists..."
if SERVICE_URL=$(gcloud run services describe lightonocr-gpu --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)" 2>/dev/null); then
    echo -e "${GREEN}✓${NC} LightOnOCR service already deployed"
    echo "  URL: $SERVICE_URL"

    # Check IAM binding
    if gcloud run services get-iam-policy lightonocr-gpu --region="$REGION" --project="$PROJECT_ID" --filter="bindings.members:serviceAccount:loan-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com" --flatten="bindings[].members" 2>/dev/null | grep -q "loan-cloud-run"; then
        echo -e "${GREEN}✓${NC} IAM binding configured for backend"
    else
        echo -e "${YELLOW}⚠${NC} IAM binding missing for backend service account"
        echo "  Run: gcloud run services add-iam-policy-binding lightonocr-gpu --member='serviceAccount:loan-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com' --role=roles/run.invoker --region=$REGION --project=$PROJECT_ID"
    fi
else
    echo -e "${YELLOW}⚠${NC} LightOnOCR service not deployed yet"
    echo "  This is expected if you haven't deployed yet"
fi
echo ""

# Check 8: Backend Service Configuration
echo "8. Checking backend service configuration..."
if BACKEND_URL=$(gcloud run services describe loan-backend-prod --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)" 2>/dev/null); then
    echo -e "${GREEN}✓${NC} Backend service deployed"
    echo "  URL: $BACKEND_URL"

    # Check if LIGHTONOCR_SERVICE_URL is configured
    if gcloud run services describe loan-backend-prod --region="$REGION" --project="$PROJECT_ID" --format="yaml(spec.template.spec.containers[0].env)" 2>/dev/null | grep -q "LIGHTONOCR_SERVICE_URL"; then
        OCR_URL=$(gcloud run services describe loan-backend-prod --region="$REGION" --project="$PROJECT_ID" --format="yaml(spec.template.spec.containers[0].env)" 2>/dev/null | grep -A 1 "LIGHTONOCR_SERVICE_URL" | grep "value:" | awk '{print $2}')
        echo -e "${GREEN}✓${NC} LIGHTONOCR_SERVICE_URL configured: $OCR_URL"
    else
        echo -e "${YELLOW}⚠${NC} LIGHTONOCR_SERVICE_URL not configured"
        echo "  Backend will fall back to Docling OCR only"
    fi
else
    echo -e "${YELLOW}⚠${NC} Backend service not deployed yet"
fi
echo ""

# Summary
echo "=================================================="
if [[ $ISSUES -eq 0 ]]; then
    echo -e "${GREEN}✓ All critical prerequisites met!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Deploy LightOnOCR GPU service:"
    echo "     cd infrastructure/lightonocr-gpu"
    echo "     PROJECT_ID=$PROJECT_ID ./deploy.sh"
    echo ""
    echo "  2. Or use CloudBuild:"
    echo "     gcloud builds submit --config=infrastructure/cloudbuild/gpu-cloudbuild.yaml --project=$PROJECT_ID --substitutions=SHORT_SHA=\$(git rev-parse --short HEAD) ."
else
    echo -e "${RED}✗ Found $ISSUES issue(s) that need to be resolved${NC}"
    echo ""
    echo "Please address the issues above before deploying."
fi
echo "=================================================="
