# Stable, provider-neutral inputs for the postgres module.
# Managed Postgres + pgvector (rds | cloud_sql | azurerm_postgresql).

variable "name_prefix" {
  description = "Prefix applied to all database resource names."
  type        = string
  default     = "marketmind"
}

variable "region" {
  description = "Cloud region to provision the database in."
  type        = string
}

variable "network_id" {
  description = "Network for private connectivity (from the networking module)."
  type        = string
  default     = null
}

variable "postgres_version" {
  description = "Major Postgres version (pgvector-compatible)."
  type        = string
  default     = "16"
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "marketmind"
}

variable "db_user" {
  description = "Master database username."
  type        = string
  default     = "marketmind"
}

variable "instance_size" {
  description = "Provider-neutral instance size hint (e.g. small / medium)."
  type        = string
  default     = "small"
}

variable "enable_pgvector" {
  description = "Create the pgvector extension for embedding storage."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags / labels applied to all resources."
  type        = map(string)
  default     = {}
}
