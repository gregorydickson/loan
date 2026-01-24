# Phase 10: v2.0 Setup & Preparation - Research

**Researched:** 2026-01-24
**Domain:** GCP Infrastructure Setup, GPU Quota, Terraform Migration, CloudBuild Configuration
**Confidence:** HIGH

## Summary

Phase 10 focuses on preparatory infrastructure work required before v2.0 development can proceed. This phase covers four distinct domains: (1) GPU quota for Cloud Run L4 GPUs to support LightOnOCR in Phase 13, (2) Terraform state archival before migration to CloudBuild, (3) CloudBuild service account setup with appropriate IAM permissions, and (4) local validation of vLLM with the LightOnOCR model.

Research confirms that Cloud Run GPU support is now GA with automatic 3 L4 GPU quota granted to new projects. The LightOnOCR-2-1B model is officially supported in vLLM v0.11.1+, enabling local validation. CloudBuild service account configuration follows established patterns with well-documented IAM roles. Terraform archival requires careful state management to avoid orphaning resources.

**Primary recommendation:** Request GPU quota early (first action), archive Terraform state with versioned GCS backup before touching any CloudBuild configuration, and validate vLLM+LightOnOCR locally before committing to GPU service architecture.

## Standard Stack

The established tools for this infrastructure preparation phase:

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| gcloud CLI | latest | GCP resource management, quota requests | Official GCP CLI, all operations scriptable |
| vLLM | 0.11.2+ | LightOnOCR model serving | Official OCR model support since v0.11.1 |
| gsutil | latest | GCS operations for Terraform state backup | Official GCS CLI for state archival |
| terraform | 1.6.0+ | State export and archival | Required for state management |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| Python | 3.12 | vLLM local environment | Model validation |
| uv | latest | Python package management | Fast vLLM installation |
| Docker | latest | Optional vLLM containerized testing | Isolated environment validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| vLLM local | Docker vLLM | Docker adds isolation but requires GPU passthrough setup |
| gcloud CLI | Console UI | Console is visual but not scriptable/reproducible |
| Manual quota request | Support ticket | Support ticket slower but may help for complex requests |

**Installation:**
```bash
# vLLM for local validation
uv venv --python 3.12 --seed
source .venv/bin/activate
uv pip install vllm==0.11.2

# gcloud CLI (if not installed)
# https://cloud.google.com/sdk/docs/install
```

## Architecture Patterns

### Recommended Project Structure
```
/archive/terraform/           # Archived Terraform state and configs
    terraform/                # Full copy of infrastructure/terraform/
        *.tf                  # All Terraform files
        terraform.tfstate     # Exported state (from GCS)
    MIGRATION.md              # Documentation of migration date and process
    inventory.md              # Resource inventory mapping to gcloud equivalents

infrastructure/
    terraform/                # Existing (preserved until CloudBuild proven)
    cloudbuild/               # New CloudBuild configs (Phase 16)
```

### Pattern 1: GPU Quota Request
**What:** Request L4 GPU quota before starting GPU-dependent work
**When to use:** First action in Phase 10
**Process:**
```bash
# Source: https://docs.cloud.google.com/run/docs/configuring/services/gpu

# Check current quota
gcloud compute regions describe us-central1 --project=PROJECT_ID \
    --format="table(quotas.filter(metric:NVIDIA_L4_GPUS))"

# For Cloud Run GPU quota (no zonal redundancy - faster approval)
# Request via console: IAM & Admin > Quotas
# Filter: "NvidiaL4GpuAllocNoZonalRedundancyPerProjectRegion"
# Target region: us-central1
# Request: 1-3 GPUs (3 is auto-granted for new projects)
```

**Key insight:** As of GA release, new projects deploying L4 GPUs get automatic 3 GPU quota without request. Only request increase if needed beyond 3.

### Pattern 2: Terraform State Archival
**What:** Export and archive Terraform state before CloudBuild migration
**When to use:** Before any CloudBuild deployment work
**Example:**
```bash
# Source: https://spacelift.io/blog/terraform-state

# 1. Pull state from GCS backend
cd infrastructure/terraform
terraform init -backend-config="bucket=${TF_STATE_BUCKET}"
terraform state pull > terraform.tfstate.backup

# 2. Create inventory of managed resources
terraform state list > resource_inventory.txt

# 3. Create archive directory
mkdir -p /archive/terraform/terraform
cp *.tf /archive/terraform/terraform/
cp terraform.tfstate.backup /archive/terraform/terraform/terraform.tfstate
cp resource_inventory.txt /archive/terraform/

# 4. Document migration
cat > /archive/terraform/MIGRATION.md << 'EOF'
# Terraform Migration

**Archived:** $(date)
**GCS State Bucket:** ${TF_STATE_BUCKET}
**State Path:** terraform/state

## Resources Managed

See: resource_inventory.txt

## Migration Notes

- State archived before CloudBuild migration
- Resources remain in GCP (not destroyed)
- CloudBuild will manage deployments, gcloud CLI for infrastructure
- Terraform files preserved for reference
EOF
```

### Pattern 3: CloudBuild Service Account Setup
**What:** Create dedicated service account with least-privilege permissions
**When to use:** Before any CloudBuild triggers are created
**Example:**
```bash
# Source: https://docs.cloud.google.com/build/docs/cloud-build-service-account

PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Create dedicated CloudBuild service account
gcloud iam service-accounts create cloudbuild-deployer \
    --display-name="CloudBuild Deployer Service Account" \
    --description="Service account for CloudBuild deployments"

SA_EMAIL="cloudbuild-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant required roles for Cloud Run deployment
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"

# Grant Artifact Registry access for pushing images
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/artifactregistry.writer"

# Grant Secret Manager access for deployment secrets
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

# Grant logging for build output
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/logging.logWriter"
```

### Pattern 4: vLLM Local Validation
**What:** Validate LightOnOCR model loads correctly with vLLM
**When to use:** After GPU quota approved, before committing to GPU service architecture
**Example:**
```bash
# Source: https://huggingface.co/lightonai/LightOnOCR-2-1B

# Setup environment
uv venv --python 3.12 --seed
source .venv/bin/activate
uv pip install vllm==0.11.2

# Serve the model (requires GPU with ~8-16GB VRAM for 1B model)
vllm serve lightonai/LightOnOCR-2-1B \
    --limit-mm-per-prompt '{"image": 1}' \
    --mm-processor-cache-gb 0 \
    --no-enable-prefix-caching

# Test with curl (in separate terminal)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lightonai/LightOnOCR-2-1B",
    "messages": [{"role": "user", "content": [
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ]}]
  }'
```

### Anti-Patterns to Avoid
- **Destroying Terraform state before CloudBuild proven:** Keep Terraform intact until CloudBuild deployments work
- **Requesting too much GPU quota:** Start with auto-granted 3, only request more if needed
- **Skipping local vLLM validation:** Don't assume GPU service will work without local testing
- **Using legacy Cloud Build service account:** Create dedicated SA with least-privilege

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GPU quota monitoring | Custom scripts | GCP Console Quotas page | Built-in, accurate, supports alerts |
| Terraform state backup | Manual file copy | `terraform state pull` + GCS versioning | Ensures consistency, handles remote state |
| Service account management | Direct API calls | gcloud CLI | Handles auth, validation, IAM propagation |
| vLLM model serving | Custom inference code | vLLM serve command | Production-grade, OpenAI-compatible API |

**Key insight:** This phase is entirely about using existing GCP and vLLM tooling correctly, not building new solutions.

## Common Pitfalls

### Pitfall 1: GPU Quota Request Timing
**What goes wrong:** GPU quota approval takes time, blocking Phase 13 development
**Why it happens:** Quota requests can take 24-48 hours for review (though auto-grant often immediate)
**How to avoid:** Request GPU quota as FIRST action in Phase 10, not after other tasks
**Warning signs:** No confirmation email within 24 hours

### Pitfall 2: Terraform State Orphaning
**What goes wrong:** Resources become unmanaged after migration, leading to drift
**Why it happens:** Deleting Terraform state without documenting what it managed
**How to avoid:**
1. Run `terraform state list` before archival
2. Keep state backup in versioned GCS
3. Map each resource to gcloud equivalent command
4. Never run `terraform destroy` during migration
**Warning signs:** Resources in GCP that don't match expectations

### Pitfall 3: CloudBuild Service Account Missing Permissions
**What goes wrong:** CloudBuild triggers fail with permission denied errors
**Why it happens:** Forgetting required IAM roles (especially actAs for service accounts)
**How to avoid:** Grant all roles listed in Pattern 3 before creating triggers
**Warning signs:** "Permission denied" in CloudBuild logs, especially for Secret Manager

### Pitfall 4: vLLM Version Mismatch
**What goes wrong:** LightOnOCR model fails to load
**Why it happens:** Using vLLM version older than 0.11.1 (when LightOnOCR support was added)
**How to avoid:** Explicitly pin vLLM>=0.11.2 in requirements
**Warning signs:** "Model not supported" or "Unknown model architecture" errors

### Pitfall 5: Insufficient VRAM for Local Testing
**What goes wrong:** vLLM crashes or OOM during model loading
**Why it happens:** LightOnOCR-2-1B is ~1B params but requires adequate VRAM
**How to avoid:** Ensure local GPU has at least 8GB VRAM (L4 has 24GB, plenty for cloud)
**Warning signs:** CUDA out of memory errors during model initialization

## Code Examples

Verified patterns from official sources:

### Check Current GPU Quota
```bash
# Source: https://docs.cloud.google.com/run/docs/configuring/services/gpu

# Check Cloud Run GPU quota for a region
gcloud run regions describe us-central1 \
    --format="table(name,quotas)"

# Or check Compute Engine quotas
gcloud compute project-info describe --project=PROJECT_ID \
    --format="table(quotas.filter(metric:NVIDIA))"
```

### Export Terraform State
```bash
# Source: https://spacelift.io/blog/terraform-state

# Initialize with backend (required before state operations)
terraform init -backend-config="bucket=my-tf-state-bucket"

# Pull current state to local file
terraform state pull > terraform.tfstate.local

# List all managed resources
terraform state list

# Show specific resource details
terraform state show google_cloud_run_v2_service.backend
```

### CloudBuild Service Account Roles
```bash
# Source: https://docs.cloud.google.com/build/docs/iam-roles-permissions

# Minimum roles for Cloud Run deployment
# - roles/run.developer: Deploy services
# - roles/iam.serviceAccountUser: Act as runtime service account
# - roles/artifactregistry.writer: Push container images
# - roles/secretmanager.secretAccessor: Read secrets during build
# - roles/logging.logWriter: Write build logs

# Additional roles for GPU service deployment
# - roles/compute.viewer: View GPU quota information
```

### vLLM LightOnOCR Serving
```bash
# Source: https://huggingface.co/lightonai/LightOnOCR-2-1B

# Install vLLM with GPU support
uv pip install vllm==0.11.2

# Serve LightOnOCR-2-1B model
vllm serve lightonai/LightOnOCR-2-1B \
    --limit-mm-per-prompt '{"image": 1}' \
    --mm-processor-cache-gb 0 \
    --no-enable-prefix-caching \
    --port 8000

# Key flags:
# --limit-mm-per-prompt '{"image": 1}': One image per request (OCR use case)
# --mm-processor-cache-gb 0: Disable multimodal cache (saves memory)
# --no-enable-prefix-caching: Disable prefix caching (not useful for OCR)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GPU quota pre-approval | Auto-grant 3 L4 GPUs | Cloud Run GPU GA (2025) | No quota request needed for basic usage |
| Terraform for all | Terraform for infra, CloudBuild for deployments | Industry trend 2024-2025 | Simpler CI/CD, less state management |
| Custom OCR pipelines | End-to-end VLM OCR (LightOnOCR) | LightOnOCR release Oct 2025 | Single model call, no pipeline complexity |
| Legacy CloudBuild SA | User-specified service accounts | 2024+ best practice | Least-privilege, better security |

**Deprecated/outdated:**
- `PROJECT_NUMBER@cloudbuild.gserviceaccount.com` legacy SA: Still works but not recommended for new setups
- LightOnOCR-1B-1025: Superseded by LightOnOCR-2-1B with RLVR training
- Terraform for Cloud Run deployments: CloudBuild preferred for container deployments

## Open Questions

Things that couldn't be fully resolved:

1. **Exact GPU Quota Approval Time**
   - What we know: Auto-grant of 3 GPUs for new projects, 24-48 hours for increases
   - What's unclear: Whether this project has existing quota or needs request
   - Recommendation: Check current quota immediately, request if needed

2. **LightOnOCR-2-1B VRAM Requirements**
   - What we know: 1B params, BF16 tensor type, benchmarked on H100 (80GB)
   - What's unclear: Minimum VRAM for L4 (24GB) deployment
   - Recommendation: Test locally first; 1B model should fit in 24GB easily

3. **Terraform Remote State Lock**
   - What we know: GCS backend supports state locking
   - What's unclear: Whether lock needs release before archival
   - Recommendation: Check lock status, release if needed before state pull

## Sources

### Primary (HIGH confidence)
- [Cloud Run GPU Documentation](https://docs.cloud.google.com/run/docs/configuring/services/gpu) - GPU specs, quota, pricing
- [CloudBuild Service Account Documentation](https://docs.cloud.google.com/build/docs/cloud-build-service-account) - SA setup, IAM roles
- [LightOnOCR-2-1B Hugging Face](https://huggingface.co/lightonai/LightOnOCR-2-1B) - Model specs, vLLM commands
- [LightOnOCR Blog Post](https://huggingface.co/blog/lightonai/lightonocr-2) - Performance benchmarks, deployment guide

### Secondary (MEDIUM confidence)
- [Terraform State Migration Guide](https://spacelift.io/blog/terraform-migrate-state) - State archival best practices
- [CloudBuild GitHub Triggers](https://cloud.google.com/build/docs/automating-builds/create-manage-triggers) - Trigger setup process
- [vLLM Supported Models](https://docs.vllm.ai/en/latest/models/supported_models/) - LightOnOCR vLLM support confirmation

### Tertiary (LOW confidence)
- GCP community discussions on quota approval times - variable experiences reported

## Metadata

**Confidence breakdown:**
- GPU Quota process: HIGH - Official GCP documentation, GA release notes
- CloudBuild setup: HIGH - Official documentation with code examples
- vLLM/LightOnOCR: HIGH - Official model card and blog post with exact commands
- Terraform archival: MEDIUM - Community best practices, no official "migration away" guide

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - stable infrastructure patterns)

## Phase 10 Requirements Mapping

| Requirement | Research Finding | Confidence |
|-------------|------------------|------------|
| LOCR-09: GPU quota for L4 | Auto-grant 3 GPUs, request if more needed | HIGH |
| CBLD-04: Terraform state archived | `terraform state pull` + GCS versioning | MEDIUM |
| CBLD-08: CloudBuild SA permissions | 5 IAM roles identified | HIGH |
| CBLD-12: Terraform to /archive/terraform/ | Directory structure defined | HIGH |
| vLLM validation (success criteria #4) | vLLM 0.11.2 + specific serve flags | HIGH |
