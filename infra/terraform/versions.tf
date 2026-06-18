# Root Terraform settings for MarketMind AI IaC.
#
# State backend = HCP Terraform free tier (provider-neutral). It avoids the
# bootstrap chicken-and-egg of needing an S3/GCS bucket before Terraform can
# provision anything. Configure per-workspace; left commented here so the
# skeleton plans offline.
#
#   cloud {
#     organization = "marketmind"
#     workspaces {
#       name = "marketmind-dev"
#     }
#   }
#
# Provider requirements are declared per-module (modules/*/versions.tf) and per
# environment so each cloud's providers are pulled in only where used.

terraform {
  required_version = ">= 1.9.0, < 2.0.0"
}
