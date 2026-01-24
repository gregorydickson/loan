# Cloud SQL PostgreSQL configuration for Loan Extraction application
# Uses private IP via VPC peering for secure database connectivity

# Cloud SQL Instance - PostgreSQL 16
resource "google_sql_database_instance" "main" {
  name             = "loan-db-${var.environment}"
  database_version = "POSTGRES_16"
  region           = var.region

  # Ensure VPC peering is established before creating the instance
  depends_on = [google_service_networking_connection.private_vpc_connection]

  # Set to false for demo/development; change to true for production
  deletion_protection = false

  settings {
    tier              = "db-f1-micro" # Smallest tier, sufficient for demo
    availability_type = "ZONAL"       # Use REGIONAL for HA in production
    disk_size         = 10
    disk_type         = "PD_SSD"

    # Private IP configuration - no public IP for security
    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.private_network.id
      enable_private_path_for_google_cloud_services = true
    }

    # Automated backup configuration
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00" # 3 AM UTC
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
      }
    }

    # Maintenance window on Sunday at 3 AM
    maintenance_window {
      day  = 7 # Sunday
      hour = 3
    }
  }
}

# Database within the Cloud SQL instance
resource "google_sql_database" "loan_extraction" {
  name     = "loan_extraction"
  instance = google_sql_database_instance.main.name
}

# Database user for application access
resource "google_sql_user" "app" {
  name     = "app"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

# Output the private IP for use in connection strings
output "cloud_sql_private_ip" {
  description = "Private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.main.private_ip_address
}

output "cloud_sql_connection_name" {
  description = "Connection name for Cloud SQL instance"
  value       = google_sql_database_instance.main.connection_name
}
