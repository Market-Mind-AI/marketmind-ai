# Provider requirements for the object-storage module.
# Provider-agnostic skeleton. Concrete provider (aws/google/azurerm) is wired
# in by the consuming environment.

terraform {
  required_version = ">= 1.9.0, < 2.0.0"
}
