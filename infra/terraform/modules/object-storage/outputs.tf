# Stable, provider-neutral outputs for the object-storage module.
# bucket_name binds the api's S3ObjectStorage adapter. Values null in the stub.

output "bucket_name" {
  description = "Name of the provisioned bucket / container."
  value       = null
}

output "bucket_url" {
  description = "Base URL of the bucket (maps to MARKETMIND_STORAGE_BASE_URL)."
  value       = null
}
