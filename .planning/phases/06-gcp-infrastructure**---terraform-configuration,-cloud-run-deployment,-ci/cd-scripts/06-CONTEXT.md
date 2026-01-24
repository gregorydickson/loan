# Phase 6: GCP Infrastructure - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Deploy the complete loan document extraction system to Google Cloud Platform using infrastructure as code. This transforms the local development setup (Phases 1-5) into a production-ready cloud deployment with Cloud Run services, Cloud SQL database, and Cloud Storage.

This phase focuses on infrastructure deployment and automation - NOT adding new application features or modifying existing functionality.

</domain>

<decisions>
## Implementation Decisions

### Resource organization
- Single GCP project for all resources (Cloud Run, Cloud SQL, GCS, etc.)
- Primary region: us-central1 (Iowa) - GCP's default region, lowest cost
- Naming convention: `{service}-{env}` format (e.g., loan-backend-prod, loan-db-prod)
- Service grouping comes before environment in resource names

### Deployment workflow
- Monolithic Terraform configuration - single main.tf with all resources
- Remote state stored in GCS backend (versioned, supports locking)
- Cloud Build triggers for automated deployments (cloudbuild.yaml)
- GCP-native CI/CD using service accounts (no external credential management)

### Environment strategy
- Production only - single prod environment (test locally before deploying)
- Environment-specific configuration via Cloud Run environment variables
- Cloud SQL (PostgreSQL) for managed database - automated backups, integrated
- Configuration at runtime (env vars), not build time (tfvars)

### Secrets & configuration
- Secrets passed as Cloud Run environment variables (simpler approach)
- Database connection via direct connection string with password
- Passwords and API keys managed as environment variables in Terraform

### Claude's Discretion
- Gemini API key injection method (balance security vs simplicity given env var approach)
- Cloud Run service sizing (CPU, memory, concurrency settings)
- Cloud SQL instance tier and configuration
- GCS bucket lifecycle policies
- Build trigger configuration details
- Network/VPC configuration (if needed)

</decisions>

<specifics>
## Specific Ideas

No specific requirements - open to standard GCP deployment patterns that align with the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope (infrastructure deployment only).

</deferred>

---

*Phase: 06-gcp-infrastructure*
*Context gathered: 2026-01-24*
