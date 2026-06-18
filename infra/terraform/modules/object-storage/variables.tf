# Stable, provider-neutral inputs for the object-storage module.
# Stores uploaded product images (S3 | GCS | Azure Blob) — the cloud equivalent
# of the local LocalFilesystemObjectStorage adapter.

variable "name_prefix" {
  description = "Prefix applied to the bucket / container name."
  type        = string
  default     = "marketmind"
}

variable "region" {
  description = "Cloud region / location for the bucket."
  type        = string
}

variable "versioning" {
  description = "Enable object versioning."
  type        = bool
  default     = false
}

variable "force_destroy" {
  description = "Allow deleting a non-empty bucket on terraform destroy (dev only)."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags / labels applied to all resources."
  type        = map(string)
  default     = {}
}
