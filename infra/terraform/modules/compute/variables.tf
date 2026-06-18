# Stable, provider-neutral inputs for the compute module.
# Runs the api + web container images (k8s cluster, Cloud Run, or VM).

variable "name_prefix" {
  description = "Prefix applied to all compute resource names."
  type        = string
  default     = "marketmind"
}

variable "region" {
  description = "Cloud region to run workloads in."
  type        = string
}

variable "cloud" {
  description = "Target cloud — selects the per-cloud submodule (aws | gcp | azure)."
  type        = string
  default     = "gcp"

  validation {
    condition     = contains(["aws", "gcp", "azure"], var.cloud)
    error_message = "cloud must be one of: aws, gcp, azure."
  }
}

variable "network_id" {
  description = "Network to attach workloads to (from the networking module)."
  type        = string
  default     = null
}

variable "api_image" {
  description = "Container image reference for the api service."
  type        = string
}

variable "web_image" {
  description = "Container image reference for the web service."
  type        = string
}

variable "min_instances" {
  description = "Minimum running instances (0 enables scale-to-zero)."
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum running instances."
  type        = number
  default     = 2
}

variable "env" {
  description = "Non-secret environment variables for the api container."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags / labels applied to all resources."
  type        = map(string)
  default     = {}
}
