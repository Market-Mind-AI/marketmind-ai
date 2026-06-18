# compute module — STUB (provider-agnostic interface, no real resources).
#
# Runs the MarketMind api + web container images. This is the most
# provider-specific module, so the per-cloud implementations live in
# SUBMODULES inside this directory:
#
#   compute/aws/    # ECS/Fargate or EKS
#   compute/gcp/    # Cloud Run or GKE Autopilot   (default target — scale-to-zero)
#   compute/azure/  # Container Apps or AKS
#
# This top-level module is the STABLE INTERFACE the environments reference; it
# dispatches to the submodule selected by var.cloud. The portability boundary is
# the container API — the same images run unchanged across all three submodules.
#
# Example dispatch (to author for Phase 2):
#   module "impl" {
#     source        = "./${var.cloud}"
#     name_prefix   = var.name_prefix
#     region        = var.region
#     network_id    = var.network_id
#     api_image     = var.api_image
#     web_image     = var.web_image
#     min_instances = var.min_instances
#     max_instances = var.max_instances
#     env           = var.env
#     tags          = var.tags
#   }
