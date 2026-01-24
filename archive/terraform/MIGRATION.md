# Terraform Migration

**Archived:** 2026-01-24
**Reason:** Migration to CloudBuild for deployment automation

## What Happened

Terraform configuration archived. Resources remain in GCP - only management tooling changes:

- **Terraform managed:** Cloud SQL, Cloud Run, GCS, VPC, IAM, Secrets, Cloud Tasks
- **CloudBuild will manage:** Container builds and deployments to Cloud Run
- **gcloud CLI will manage:** One-time infrastructure changes

## State Location

State remains in GCS remote backend (configured in main.tf):

```hcl
backend "gcs" {
  prefix = "terraform/state"
}
```

**State is NOT destroyed or copied locally** because:

1. State contains sensitive outputs (connection strings, IPs, secret references)
2. State can be re-fetched anytime via `terraform state pull`
3. GCS backend has versioning enabled for recovery
4. Keeping state in GCS allows potential future Terraform operations

## Resources

See: [inventory.md](./inventory.md) for complete resource list with gcloud equivalents.

**33 total resources** across:
- Cloud Run services (backend, frontend)
- Cloud SQL PostgreSQL instance
- Cloud Storage bucket with lifecycle policies
- Cloud Tasks queue for async processing
- Secret Manager secrets (database URL, API keys)
- VPC networking for private SQL connectivity
- IAM service account and role bindings

## Why CloudBuild?

1. **Simpler deployments** - Container build + deploy in one workflow
2. **Better CI/CD integration** - Triggers on git push, automatic rollback
3. **Reduced complexity** - No Terraform state management for deployments
4. **Cost savings** - No Terraform Cloud, just pay-per-build

### What Changes

| Aspect | Before (Terraform) | After (CloudBuild) |
|--------|-------------------|-------------------|
| Container builds | External (Artifact Registry direct) | CloudBuild step |
| Cloud Run deploy | `terraform apply` | `gcloud run deploy` in CloudBuild |
| Env vars | Terraform variables | CloudBuild substitutions + Secret Manager |
| Rollback | `terraform apply` with old state | `gcloud run services update-traffic` |

### What Stays the Same

- Infrastructure resources (VPC, Cloud SQL, GCS, IAM) remain unchanged
- Secret Manager secrets continue working
- Cloud Tasks queue continues working
- Service account permissions unchanged

## Reverting (If Needed)

If you need to use Terraform again:

1. Copy archive/terraform/terraform/ to infrastructure/terraform/
2. Run `terraform init -backend-config="bucket=${TF_STATE_BUCKET}"`
3. Terraform will reconnect to existing GCS state
4. Run `terraform plan` to verify state alignment

```bash
# Example revert
cp -r archive/terraform/terraform/* infrastructure/terraform/
cd infrastructure/terraform
terraform init -backend-config="bucket=your-project-terraform-state"
terraform plan
```

## Important Notes

- **NO `terraform destroy` was run** - all resources continue to exist
- **Resources function normally** - database, services, storage all operational
- **CloudBuild deployments update resources in-place** - no resource recreation
- **State in GCS is authoritative** - don't delete the state bucket

## Timeline

| Date | Action |
|------|--------|
| 2026-01-24 | Terraform configuration archived |
| 2026-01-24+ | CloudBuild pipelines created (Phase 10, Plan 03) |
| Future | Terraform archived configs available for reference |

## Contact

If questions arise about the original Terraform setup, refer to:
- `archive/terraform/terraform/` - Original configurations
- `archive/terraform/inventory.md` - Resource mapping to gcloud
- `.planning/phases/06-gcp-infrastructure/` - Original phase documentation
