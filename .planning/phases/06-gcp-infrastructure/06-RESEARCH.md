# Phase 6: GCP Infrastructure - Research

**Researched:** 2026-01-24
**Domain:** Google Cloud Platform Infrastructure as Code (Terraform)
**Confidence:** HIGH

## Summary

This research covers deploying a FastAPI backend and Next.js frontend to Google Cloud Platform using Terraform infrastructure as code. The standard approach uses Cloud Run for serverless compute, Cloud SQL PostgreSQL for the database, Cloud Storage for document storage, and Cloud Tasks for async processing.

The key architectural decision is using Cloud Run v2 with direct VPC egress to connect to Cloud SQL via private IP, avoiding the additional cost of Serverless VPC Access connectors. Terraform Google provider 7.x provides all necessary resources with the newer `google_cloud_run_v2_service` resource offering native scaling configuration without annotations.

Production-ready Dockerfiles use multi-stage builds for smaller images and faster cold starts. FastAPI uses `python:3.12-slim` with pip prefix installation, while Next.js uses standalone output mode with Alpine-based Node.js images.

**Primary recommendation:** Use Terraform with `google_cloud_run_v2_service`, Cloud SQL with private IP via VPC peering, and Secret Manager for all credentials. Never hardcode secrets in Terraform files.

## Standard Stack

The established tools and services for this domain:

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Terraform | >= 1.6.0 | Infrastructure as code | Industry standard, GCP-maintained provider |
| google provider | >= 7.0.0 | GCP Terraform provider | Latest major version with 800+ resources, ephemeral resources support |
| google-beta provider | >= 7.0.0 | Beta features | Required for preview features if needed |

### GCP Services
| Service | Configuration | Purpose | Why Standard |
|---------|---------------|---------|--------------|
| Cloud Run v2 | google_cloud_run_v2_service | Container hosting | Serverless, auto-scaling, pay-per-use |
| Cloud SQL | PostgreSQL 16 | Managed database | Automated backups, HA options, private IP |
| Cloud Storage | Standard class | Document storage | Durable, lifecycle rules, IAM integration |
| Cloud Tasks | Rate-limited queue | Async processing | Managed queue with retry logic |
| Secret Manager | Secret storage | Credentials | Integrated with Cloud Run, rotation support |
| IAM | Service accounts | Access control | Least-privilege, workload identity |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| Docker | Container images | Multi-stage builds for backend/frontend |
| gcloud CLI | GCP operations | Setup scripts, deployments |
| Artifact Registry | Container registry | Store Docker images |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Cloud Run | GKE | More control, but higher complexity and cost |
| Cloud SQL | Cloud Spanner | Global scale, but significantly higher cost |
| Cloud Tasks | Pub/Sub | More features, but more complex for simple queuing |
| VPC Connector | Direct VPC Egress | Connector has fixed cost; Direct egress is newer but free |

**Installation:**
```bash
# Install Terraform
brew install terraform  # macOS
# or download from https://www.terraform.io/downloads

# Install gcloud CLI
brew install google-cloud-sdk  # macOS
# or see https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud auth application-default login
```

## Architecture Patterns

### Recommended Project Structure
```
infrastructure/
├── terraform/
│   ├── main.tf              # Provider config, APIs, basic resources
│   ├── variables.tf         # Input variables
│   ├── outputs.tf           # Output values (URLs, connection strings)
│   ├── cloud_sql.tf         # Database configuration
│   ├── cloud_storage.tf     # GCS bucket configuration
│   ├── cloud_run.tf         # Cloud Run services (backend + frontend)
│   ├── cloud_tasks.tf       # Task queue configuration
│   ├── iam.tf               # Service accounts and roles
│   ├── vpc.tf               # VPC network for private IP
│   └── terraform.tfvars.example  # Example variable values
├── scripts/
│   ├── setup-gcp.sh         # Initial GCP project setup
│   └── deploy.sh            # Automated deployment script
├── backend/
│   └── Dockerfile           # Multi-stage FastAPI build
└── frontend/
    └── Dockerfile           # Multi-stage Next.js standalone build
```

### Pattern 1: VPC Network with Private IP for Cloud SQL
**What:** Create a VPC network with private services access for Cloud SQL to avoid public IP exposure
**When to use:** Always for production deployments
**Example:**
```hcl
# Source: Google Cloud documentation - Private IP configuration
resource "google_compute_network" "private_network" {
  name                    = "${var.project_id}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_global_address" "private_ip_address" {
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.private_network.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.private_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}
```

### Pattern 2: Cloud Run with Direct VPC Egress
**What:** Connect Cloud Run directly to VPC for Cloud SQL access without VPC Connector costs
**When to use:** When connecting to private IP Cloud SQL instances
**Example:**
```hcl
# Source: Google Cloud Run documentation
resource "google_cloud_run_v2_service" "backend" {
  name     = "loan-backend"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/loan-repo/backend:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url.secret_id
            version = "latest"
          }
        }
      }
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.private_network.id
        subnetwork = google_compute_subnetwork.cloud_run_subnet.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    service_account = google_service_account.cloud_run_sa.email
  }
}
```

### Pattern 3: Secret Manager Integration
**What:** Store sensitive credentials in Secret Manager, not in Terraform state
**When to use:** Always for database passwords, API keys, and other secrets
**Example:**
```hcl
# Source: Cloud Run secrets documentation
resource "google_secret_manager_secret" "db_password" {
  secret_id = "db-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password  # Pass via environment variable, not tfvars
}

resource "google_secret_manager_secret_iam_member" "cloud_run_access" {
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}
```

### Anti-Patterns to Avoid
- **Hardcoding secrets in .tf files:** Use Secret Manager and environment variables
- **Using public IP for Cloud SQL in production:** Always use private IP with VPC peering
- **Storing terraform.tfvars with secrets in git:** Use environment variables or Secret Manager
- **Using google_cloud_run_service (v1):** Use google_cloud_run_v2_service for better features
- **Skipping depends_on for VPC resources:** Service networking connection must complete before Cloud SQL
- **Using default service accounts:** Create dedicated service accounts with least-privilege roles

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Database connection pooling | Custom connection manager | Cloud SQL Auth Proxy or asyncpg pool | Handles reconnection, auth, connection limits |
| Secret rotation | Manual secret updates | Secret Manager with version pinning | Audit trail, rotation support, IAM integration |
| Container registry | Docker Hub | Artifact Registry | Private, GCP-integrated, vulnerability scanning |
| Load balancing | Custom nginx | Cloud Run built-in | Automatic HTTPS, global load balancing |
| SSL/TLS certificates | Let's Encrypt setup | Cloud Run managed certs | Automatic renewal, no configuration |
| Database backups | pg_dump scripts | Cloud SQL automated backups | Point-in-time recovery, managed retention |
| Log aggregation | Custom logging | Cloud Logging | Integrated with Cloud Run, alerting built-in |

**Key insight:** GCP managed services handle operational complexity that would require significant effort to replicate. Use native integrations wherever possible.

## Common Pitfalls

### Pitfall 1: Cloud SQL Connection Failures from Cloud Run
**What goes wrong:** Cloud Run service cannot connect to Cloud SQL despite correct configuration
**Why it happens:** Service networking connection not fully established before Cloud SQL creation, or missing Cloud SQL Client role on service account
**How to avoid:**
- Add explicit `depends_on = [google_service_networking_connection.private_vpc_connection]` to Cloud SQL resource
- Ensure service account has `roles/cloudsql.client` role
- For private IP, ensure VPC subnet is in same region as Cloud Run
**Warning signs:** "Connection refused" or "Network is unreachable" errors in Cloud Run logs

### Pitfall 2: Terraform State Drift with Multi-Environment Deployments
**What goes wrong:** Terraform tries to recreate existing resources when deploying from different machines
**Why it happens:** `terraform.tfvars` containing project_id is in .gitignore, causing state mismatch
**How to avoid:**
- Use remote state backend (GCS bucket) for team deployments
- Pass sensitive variables via `TF_VAR_` environment variables
- Use workspaces for environment separation
**Warning signs:** Plan shows destroy/create for existing resources

### Pitfall 3: Docker Image Size Causing Cold Start Latency
**What goes wrong:** Cloud Run cold starts take 10+ seconds
**Why it happens:** Large Docker images with full node_modules or Python packages
**How to avoid:**
- Use multi-stage builds to exclude build dependencies
- Use Alpine or slim base images
- For Next.js, use `output: 'standalone'` mode
- Pre-compile Python bytecode during build
**Warning signs:** Cold start times > 5 seconds in Cloud Run metrics

### Pitfall 4: Missing API Enablement
**What goes wrong:** Terraform apply fails with "API not enabled" errors
**Why it happens:** Required GCP APIs not enabled before resource creation
**How to avoid:**
- Enable APIs in main.tf with `google_project_service` resources
- Use `disable_dependent_services = false` and `disable_on_destroy = false`
- Add `depends_on` to resources that need the APIs
**Warning signs:** Error messages mentioning "API not enabled" or "Permission denied"

### Pitfall 5: Secret Version Mismatch
**What goes wrong:** Cloud Run uses stale secret values after secret rotation
**Why it happens:** Using `version = "latest"` with environment variable secrets (resolved at startup only)
**How to avoid:**
- For env vars: pin to specific version numbers for predictability
- For frequently rotated secrets: mount as volumes (refreshed at runtime)
- Use rolling deployments to pick up new secret versions
**Warning signs:** Application uses old credentials after secret update

### Pitfall 6: VPC Connector vs Direct VPC Egress Confusion
**What goes wrong:** Unexpected billing or connection failures
**Why it happens:** Misunderstanding the two VPC connectivity options
**How to avoid:**
- VPC Connector: Fixed monthly cost (~$7/month/connector), works with google_cloud_run_service (v1)
- Direct VPC Egress: No fixed cost, requires google_cloud_run_v2_service, uses `vpc_access.network_interfaces`
- Choose Direct VPC Egress for v2 services to avoid connector costs
**Warning signs:** Unexpected charges for VPC Access or connection timeouts

## Code Examples

Verified patterns from official sources:

### Cloud SQL PostgreSQL 16 with Private IP
```hcl
# Source: Google Cloud SQL documentation
resource "google_sql_database_instance" "main" {
  name             = "loan-db"
  database_version = "POSTGRES_16"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier              = "db-f1-micro"  # Use db-custom-2-4096 for production
    availability_type = "ZONAL"        # Use "REGIONAL" for HA in production
    disk_size         = 10
    disk_type         = "PD_SSD"

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.private_network.id
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
      }
    }

    maintenance_window {
      day  = 7  # Sunday
      hour = 3  # 3 AM
    }
  }

  deletion_protection = true  # Set to false only for testing
}

resource "google_sql_database" "loan_extraction" {
  name     = "loan_extraction"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app_user" {
  name     = "app"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}
```

### Cloud Storage Bucket with Lifecycle Rules
```hcl
# Source: Google Cloud Storage documentation
resource "google_storage_bucket" "documents" {
  name          = "${var.project_id}-loan-documents"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }
}
```

### Cloud Tasks Queue with Rate Limiting
```hcl
# Source: Terraform Registry google_cloud_tasks_queue documentation
resource "google_cloud_tasks_queue" "document_processing" {
  name     = "document-processing"
  location = var.region

  rate_limits {
    max_dispatches_per_second = 10
    max_concurrent_dispatches = 5
  }

  retry_config {
    max_attempts       = 5
    max_retry_duration = "3600s"
    max_backoff        = "3600s"
    min_backoff        = "10s"
    max_doublings      = 5
  }
}
```

### IAM Service Account with Least Privilege
```hcl
# Source: GCP IAM best practices
resource "google_service_account" "cloud_run_sa" {
  account_id   = "loan-cloud-run"
  display_name = "Loan Extraction Cloud Run Service Account"
}

# Cloud SQL Client - connect to database
resource "google_project_iam_member" "cloud_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Storage Object Admin - read/write documents
resource "google_storage_bucket_iam_member" "documents_access" {
  bucket = google_storage_bucket.documents.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Secret Manager Accessor - read secrets
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Cloud Tasks Enqueuer - create tasks
resource "google_project_iam_member" "tasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}
```

### Backend Dockerfile (FastAPI Multi-Stage)
```dockerfile
# Source: FastAPI deployment docs + Cloud Run best practices
# Stage 1: Build
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies to /install prefix
COPY pyproject.toml ./
RUN pip install --prefix=/install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -q ./src/

# Switch to non-root user
USER app

# Cloud Run provides PORT environment variable
ENV PORT=8080

# Use exec form for proper signal handling
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Frontend Dockerfile (Next.js Standalone)
```dockerfile
# Source: Next.js deployment docs + standalone output
# Stage 1: Dependencies
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --only=production

# Stage 2: Build
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set standalone output in next.config
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 3: Runtime
FROM node:20-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy standalone output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER nextjs

# Cloud Run provides PORT environment variable
ENV PORT=8080
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

### Setup Script (setup-gcp.sh)
```bash
#!/bin/bash
# Source: GCP best practices for project setup
set -euo pipefail

PROJECT_ID="${1:?Usage: setup-gcp.sh PROJECT_ID REGION}"
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

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Initialize Terraform: cd infrastructure/terraform && terraform init"
echo "2. Create terraform.tfvars with your configuration"
echo "3. Run: terraform plan"
echo "4. Run: terraform apply"
```

### Deploy Script (deploy.sh)
```bash
#!/bin/bash
# Source: Cloud Run deployment best practices
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID environment variable}"
REGION="${REGION:-us-central1}"
TAG="${TAG:-$(git rev-parse --short HEAD)}"

REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/loan-repo"

echo "Deploying with tag: $TAG"

# Build and push backend
echo "Building backend..."
docker build -t "${REGISTRY}/backend:${TAG}" -t "${REGISTRY}/backend:latest" ./backend
docker push "${REGISTRY}/backend:${TAG}"
docker push "${REGISTRY}/backend:latest"

# Build and push frontend
echo "Building frontend..."
docker build -t "${REGISTRY}/frontend:${TAG}" -t "${REGISTRY}/frontend:latest" ./frontend
docker push "${REGISTRY}/frontend:${TAG}"
docker push "${REGISTRY}/frontend:latest"

# Apply Terraform (updates Cloud Run services)
echo "Applying Terraform..."
cd infrastructure/terraform
terraform apply -auto-approve -var="image_tag=${TAG}"

# Get service URLs
BACKEND_URL=$(terraform output -raw backend_url)
FRONTEND_URL=$(terraform output -raw frontend_url)

echo ""
echo "Deployment complete!"
echo "Backend URL: $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
echo ""
echo "Health check: curl ${BACKEND_URL}/health"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google_cloud_run_service (v1) | google_cloud_run_v2_service | 2023 | Native scaling config, better VPC integration |
| VPC Connector for Cloud SQL | Direct VPC Egress | 2024 | No fixed connector cost, simpler setup |
| Knative annotations for scaling | Native scaling block | 2023 | No launch stage annotations needed |
| Container Registry (gcr.io) | Artifact Registry | 2023 | Vulnerability scanning, better IAM |
| Cloud SQL Proxy sidecar | Direct VPC connection | 2024 | Simpler architecture, no sidecar overhead |
| Terraform state in local file | Remote state in GCS | Always | Team collaboration, state locking |

**Deprecated/outdated:**
- `google_cloud_run_service` resource: Use `google_cloud_run_v2_service` for new deployments
- Container Registry (gcr.io): Migrate to Artifact Registry
- Serverless VPC Access Connector with Cloud Run v2: Use Direct VPC Egress instead
- `tiangolo/uvicorn-gunicorn-fastapi` Docker image: Use official Python image with FastAPI CLI

## Open Questions

Things that couldn't be fully resolved:

1. **Cloud Tasks HTTP Target Authentication**
   - What we know: Cloud Tasks can call Cloud Run with OIDC tokens
   - What's unclear: Exact Terraform configuration for OIDC token in task creation
   - Recommendation: Use service account with invoker role, test configuration manually first

2. **Cold Start Optimization for Docling**
   - What we know: Docling may have large dependencies affecting cold starts
   - What's unclear: Actual cold start time with production Docling container
   - Recommendation: Set `min_instance_count = 1` initially, monitor cold start metrics, adjust

3. **Database Connection Pool Sizing**
   - What we know: Cloud SQL has connection limits based on tier
   - What's unclear: Optimal pool size for Cloud Run with variable instance counts
   - Recommendation: Start with max_connections = 5 per instance, monitor and adjust

## Sources

### Primary (HIGH confidence)
- [Google Cloud Run documentation](https://docs.cloud.google.com/run/docs/configuring/services/environment-variables) - Environment variables and secrets configuration
- [Google Cloud SQL documentation](https://docs.cloud.google.com/sql/docs/postgres/configure-private-ip) - Private IP configuration
- [FastAPI deployment documentation](https://fastapi.tiangolo.com/deployment/docker/) - Docker patterns
- [Next.js output configuration](https://nextjs.org/docs/pages/api-reference/config/next-config-js/output) - Standalone mode

### Secondary (MEDIUM confidence)
- [Terraform Registry google provider](https://registry.terraform.io/providers/hashicorp/google/latest) - Resource documentation
- [HashiCorp Terraform Google provider releases](https://github.com/hashicorp/terraform-provider-google/releases) - Version 7.16.0 current
- [Google Cloud Terraform best practices](https://docs.cloud.google.com/docs/terraform/best-practices/operations) - Operations guidance

### Tertiary (LOW confidence)
- [Dev.to Terraform GCP guides](https://dev.to/terraformmonkey/gcp-cloud-sql-terraform-quick-start-guide-2mk4) - Community patterns
- [Medium Terraform tutorials](https://medium.com/terraform-using-google-cloud-platform/terraform-for-gcp-how-to-create-cloud-sql-0a558840914c) - Additional examples

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official GCP documentation and Terraform registry
- Architecture: HIGH - Verified patterns from Google Cloud documentation
- Pitfalls: MEDIUM - Mix of official docs and community experience
- Code examples: HIGH - Derived from official documentation samples

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - GCP infrastructure is relatively stable)
