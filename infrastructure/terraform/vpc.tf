# VPC Network configuration for private Cloud SQL connectivity
# Enables Cloud Run to connect to Cloud SQL via private IP

# VPC Network
resource "google_compute_network" "private_network" {
  name                    = "${var.project_id}-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.compute]
}

# Subnet for Cloud Run services
resource "google_compute_subnetwork" "cloud_run_subnet" {
  name                     = "cloud-run-subnet"
  region                   = var.region
  ip_cidr_range            = "10.0.0.0/24"
  network                  = google_compute_network.private_network.id
  private_ip_google_access = true
}

# Private IP allocation for Cloud SQL VPC peering
resource "google_compute_global_address" "private_ip_address" {
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.private_network.id
}

# Private VPC connection for Cloud SQL
# This enables Cloud SQL to use private IP within the VPC
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.private_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]

  depends_on = [google_project_service.servicenetworking]
}
