# Provider requirements for the networking module.
# Provider-agnostic skeleton: the concrete provider (aws/google/azurerm) is
# wired in by the consuming environment, so none is required here yet.

terraform {
  required_version = ">= 1.9.0, < 2.0.0"
}
