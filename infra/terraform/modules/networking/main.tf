# networking module — STUB (provider-agnostic interface, no real resources).
#
# Provisions the VPC / subnets / firewall the compute + postgres modules attach
# to. The concrete implementation is selected per cloud by the consuming
# environment; resources are intentionally commented out so this skeleton plans
# offline and stays `terraform fmt` clean.
#
# Example (GCP):
#   resource "google_compute_network" "this" {
#     name                    = "${var.name_prefix}-net"
#     auto_create_subnetworks = false
#   }
#
# Example (AWS):
#   resource "aws_vpc" "this" {
#     cidr_block = var.cidr_block
#     tags       = merge(var.tags, { Name = "${var.name_prefix}-vpc" })
#   }
