# Provider requirements for the compute module.
# Provider-agnostic skeleton. Concrete providers are required inside the
# per-cloud submodules (aws/ gcp/ azure/), not at this interface level.

terraform {
  required_version = ">= 1.9.0, < 2.0.0"
}
