# Stable, provider-neutral outputs for the postgres module.
# database_url feeds MARKETMIND_DATABASE_URL on the api container.
# Values are null in the stub.

output "host" {
  description = "Database host / private IP."
  value       = null
}

output "port" {
  description = "Database port."
  value       = 5432
}

output "database_url" {
  description = "SQLAlchemy async DSN for the api (postgresql+asyncpg://...). Password injected via the secrets module."
  value       = null
  sensitive   = true
}
