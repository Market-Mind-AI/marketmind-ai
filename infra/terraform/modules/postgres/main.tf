# postgres module — STUB (provider-agnostic interface, no real resources).
#
# Managed Postgres 16 with the pgvector extension — backs both the analysis
# repository and the vector store (comparable-product retrieval). The concrete
# implementation is selected per cloud:
#
#   aws    -> aws_db_instance (RDS)
#   gcp    -> google_sql_database_instance (Cloud SQL)
#   azure  -> azurerm_postgresql_flexible_server
#
# pgvector is enabled via the extension on first connect (CREATE EXTENSION
# vector) — managed-Postgres flavours expose it in their allowed-extensions list.
# Resources are commented out so this skeleton plans offline.
#
# Example (GCP Cloud SQL):
#   resource "google_sql_database_instance" "this" {
#     name             = "${var.name_prefix}-pg"
#     database_version = "POSTGRES_${var.postgres_version}"
#     region           = var.region
#     settings { tier = "db-custom-1-3840" }
#   }
