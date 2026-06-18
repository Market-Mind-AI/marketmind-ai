# Environment: dev (single cloud — Phase 2, optional/stretch)

This is the **one** cloud environment. It composes the provider-neutral modules
(`../../modules/*`) into a small, scale-to-zero deployment on a single target
cloud (GKE Autopilot / Cloud Run, or a VM running docker-compose). It is a stub:
no `.tf` resource files are committed yet — only this contract.

## Intended composition (Phase 2)

```hcl
# main.tf (to author for Phase 2)
module "networking"     { source = "../../modules/networking" }
module "postgres"       { source = "../../modules/postgres" }       # + pgvector
module "object_storage" { source = "../../modules/object-storage" } # product image uploads
module "secrets"        { source = "../../modules/secrets" }        # Anthropic / Cohere keys
module "compute"        { source = "../../modules/compute" }        # cluster / Cloud Run / VM
```

## Wiring notes

- The same container images and manifests used by the local compose stack are
  deployed here unchanged — the portability boundary is the container API.
- `MARKETMIND_DATABASE_URL` comes from the `postgres` module output; secrets
  (Anthropic/Cohere/DataForSEO/eBay) come from the `secrets` module.
- Provider + backend (HCP Terraform free tier) are configured at apply time;
  pin providers with `~>` and commit `.terraform.lock.hcl`.

## Usage (once authored)

```sh
terraform -chdir=infra/terraform/environments/dev init
terraform -chdir=infra/terraform/environments/dev plan -var-file=dev.tfvars
terraform -chdir=infra/terraform/environments/dev apply -var-file=dev.tfvars
```
