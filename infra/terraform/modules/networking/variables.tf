# Stable, provider-neutral inputs for the networking module.
# vpc / subnets / firewall — implemented per cloud behind this interface.

variable "name_prefix" {
  description = "Prefix applied to all networking resource names."
  type        = string
  default     = "marketmind"
}

variable "region" {
  description = "Cloud region to provision networking in."
  type        = string
}

variable "cidr_block" {
  description = "Primary CIDR block for the VPC / network."
  type        = string
  default     = "10.0.0.0/16"
}

variable "tags" {
  description = "Tags / labels applied to all resources."
  type        = map(string)
  default     = {}
}
