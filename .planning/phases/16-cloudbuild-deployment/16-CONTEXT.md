# Phase 16: CloudBuild Deployment - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate from Terraform to CloudBuild + gcloud CLI for automated deployment of backend, frontend, and GPU services. Includes GitHub trigger setup, Secret Manager integration, and basic rollback procedures.

</domain>

<decisions>
## Implementation Decisions

### Simplicity First - Proof of Concept Approach

- Keep deployment configuration simple and straightforward
- Avoid complex orchestration patterns (blue-green, canary, etc.)
- Focus on working automation over advanced features
- Use basic rollback mechanisms (revision-based)
- Minimal approval gates - prioritize developer velocity

### Build Triggers

- Simple GitHub trigger on push to main branch
- No complex branch patterns or tag-based releases initially
- Manual deployment option via gcloud CLI for emergency fixes
- Single build configuration per service (backend, frontend, GPU)

### Secret Management

- Use Secret Manager for all sensitive configuration
- Build-time secret injection via CloudBuild
- Single environment (production) - no multi-environment complexity initially
- Secrets referenced by name in cloudbuild.yaml

### Service Orchestration

- Deploy services independently (no orchestration layer)
- Services can be deployed in any order (loose coupling)
- No dependency ordering enforcement - services handle unavailability gracefully
- Parallel builds acceptable if multiple PRs merged

### Rollback Approach

- Simple Cloud Run revision rollback via gcloud CLI
- Manual rollback trigger (no automated failure detection)
- Rollback procedure documented in runbook
- Keep last 5 revisions for rollback capability

### Claude's Discretion

- CloudBuild timeout values
- Build step naming conventions
- Log retention policies
- Exact gcloud CLI command structure

</decisions>

<specifics>
## Specific Ideas

- "This is a proof of concept - we can add sophistication later if needed"
- Prioritize getting automated deployments working over advanced deployment strategies
- Developer should be able to deploy with minimal steps

</specifics>

<deferred>
## Deferred Ideas

- Multi-environment support (staging, production) - future enhancement
- Automated rollback on failure detection - future enhancement
- Blue-green or canary deployments - future enhancement
- Complex approval workflows - future enhancement
- Tag-based release versioning - future enhancement

</deferred>

---

*Phase: 16-cloudbuild-deployment*
*Context gathered: 2026-01-25*
