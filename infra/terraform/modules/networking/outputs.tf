# Stable, provider-neutral outputs for the networking module.
# Consumed by the compute + postgres modules. Values are null in the stub.

output "network_id" {
  description = "ID of the provisioned VPC / network."
  value       = null
}

output "subnet_ids" {
  description = "IDs of the provisioned subnets."
  value       = []
}
