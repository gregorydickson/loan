# Terraform Resource Inventory

Resources managed by Terraform before CloudBuild migration.
**Archived:** 2026-01-24

## GCP APIs Enabled

| Resource Type | Name | Purpose | gcloud Equivalent |
|---------------|------|---------|-------------------|
| google_project_service | compute | Compute Engine API | `gcloud services enable compute.googleapis.com` |
| google_project_service | run | Cloud Run API | `gcloud services enable run.googleapis.com` |
| google_project_service | sqladmin | Cloud SQL Admin API | `gcloud services enable sqladmin.googleapis.com` |
| google_project_service | secretmanager | Secret Manager API | `gcloud services enable secretmanager.googleapis.com` |
| google_project_service | cloudtasks | Cloud Tasks API | `gcloud services enable cloudtasks.googleapis.com` |
| google_project_service | servicenetworking | Service Networking API | `gcloud services enable servicenetworking.googleapis.com` |
| google_project_service | artifactregistry | Artifact Registry API | `gcloud services enable artifactregistry.googleapis.com` |

## Cloud Run Services

| Resource Type | Name | Purpose | gcloud Equivalent |
|---------------|------|---------|-------------------|
| google_cloud_run_v2_service | backend | Backend API (FastAPI + Docling) | `gcloud run services describe loan-backend-prod --region us-central1` |
| google_cloud_run_v2_service | frontend | Frontend UI (Next.js) | `gcloud run services describe loan-frontend-prod --region us-central1` |
| google_cloud_run_v2_service_iam_member | backend_public | Public access to backend | `gcloud run services get-iam-policy loan-backend-prod` |
| google_cloud_run_v2_service_iam_member | frontend_public | Public access to frontend | `gcloud run services get-iam-policy loan-frontend-prod` |

## Cloud SQL Database

| Resource Type | Name | Purpose | gcloud Equivalent |
|---------------|------|---------|-------------------|
| google_sql_database_instance | main | PostgreSQL 16 instance | `gcloud sql instances describe loan-db-prod` |
| google_sql_database | loan_extraction | Application database | `gcloud sql databases describe loan_extraction --instance loan-db-prod` |
| google_sql_user | app | Database user | `gcloud sql users list --instance loan-db-prod` |

## Cloud Storage

| Resource Type | Name | Purpose | gcloud Equivalent |
|---------------|------|---------|-------------------|
| google_storage_bucket | documents | Document storage with lifecycle | `gcloud storage buckets describe gs://{project-id}-loan-documents` |
| google_storage_bucket_iam_member | documents_access | SA access to bucket | `gcloud storage buckets get-iam-policy gs://{project-id}-loan-documents` |

## Cloud Tasks

| Resource Type | Name | Purpose | gcloud Equivalent |
|---------------|------|---------|-------------------|
| google_cloud_tasks_queue | document_processing | Async processing queue | `gcloud tasks queues describe document-processing --location us-central1` |

## Secret Manager

| Resource Type | Name | Purpose | gcloud Equivalent |
|---------------|------|---------|-------------------|
| google_secret_manager_secret | database_url | Database connection string | `gcloud secrets describe database-url` |
| google_secret_manager_secret_version | database_url | Current DB URL value | `gcloud secrets versions access latest --secret database-url` |
| google_secret_manager_secret | gemini_api_key | Gemini API key | `gcloud secrets describe gemini-api-key` |
| google_secret_manager_secret_version | gemini_api_key | Current API key value | `gcloud secrets versions access latest --secret gemini-api-key` |
| google_secret_manager_secret_iam_member | database_url_access | SA access to DB secret | `gcloud secrets get-iam-policy database-url` |
| google_secret_manager_secret_iam_member | gemini_api_key_access | SA access to API key | `gcloud secrets get-iam-policy gemini-api-key` |

## VPC Networking

| Resource Type | Name | Purpose | gcloud Equivalent |
|---------------|------|---------|-------------------|
| google_compute_network | private_network | VPC for Cloud SQL connectivity | `gcloud compute networks describe {project-id}-vpc` |
| google_compute_subnetwork | cloud_run_subnet | Subnet for Cloud Run (10.0.0.0/24) | `gcloud compute networks subnets describe cloud-run-subnet --region us-central1` |
| google_compute_global_address | private_ip_address | Private IP range for VPC peering | `gcloud compute addresses describe private-ip-address --global` |
| google_service_networking_connection | private_vpc_connection | VPC peering for Cloud SQL | `gcloud services vpc-peerings list --network {project-id}-vpc` |

## IAM

| Resource Type | Name | Purpose | gcloud Equivalent |
|---------------|------|---------|-------------------|
| google_service_account | cloud_run_sa | Cloud Run service account | `gcloud iam service-accounts describe loan-cloud-run@{project}.iam.gserviceaccount.com` |
| google_project_iam_member | cloudsql_client | Cloud SQL Client role | `gcloud projects get-iam-policy {project} --filter="bindings.role:roles/cloudsql.client"` |
| google_project_iam_member | secretmanager_accessor | Secret Accessor role | `gcloud projects get-iam-policy {project} --filter="bindings.role:roles/secretmanager.secretAccessor"` |
| google_project_iam_member | cloudtasks_enqueuer | Cloud Tasks Enqueuer role | `gcloud projects get-iam-policy {project} --filter="bindings.role:roles/cloudtasks.enqueuer"` |
| google_project_iam_member | logging_writer | Logging Writer role | `gcloud projects get-iam-policy {project} --filter="bindings.role:roles/logging.logWriter"` |
| google_project_iam_member | run_invoker | Cloud Run Invoker role | `gcloud projects get-iam-policy {project} --filter="bindings.role:roles/run.invoker"` |

## Summary

| Category | Resource Count |
|----------|----------------|
| API Enablement | 7 |
| Cloud Run | 4 |
| Cloud SQL | 3 |
| Cloud Storage | 2 |
| Cloud Tasks | 1 |
| Secret Manager | 6 |
| VPC Networking | 4 |
| IAM | 6 |
| **Total** | **33** |
