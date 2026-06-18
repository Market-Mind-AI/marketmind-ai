# object-storage module — STUB (provider-agnostic interface, no real resources).
#
# Stores uploaded product images. The cloud counterpart of the local
# LocalFilesystemObjectStorage adapter (the api's S3ObjectStorage adapter binds
# to the bucket exposed here). Selected per cloud:
#
#   aws    -> aws_s3_bucket
#   gcp    -> google_storage_bucket
#   azure  -> azurerm_storage_container
#
# Resources are commented out so this skeleton plans offline.
#
# Example (AWS):
#   resource "aws_s3_bucket" "this" {
#     bucket        = "${var.name_prefix}-uploads"
#     force_destroy = var.force_destroy
#     tags          = var.tags
#   }
