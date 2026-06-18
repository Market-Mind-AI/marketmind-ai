# MarketMind AI — Infrastructure (IaC)

Cloud-portable Infrastructure-as-Code for MarketMind AI. The objective is
**"cloud-portable Terraform," not "multi-cloud-live."** We satisfy the
cloud-agnostic requirement by writing modular, provider-abstracted Terraform
and deploying it **once** (or demonstrating `terraform plan`) plus a written
portability analysis — *not* by standing up a second cloud. A multi-cloud live
proof is months of work for ~30 seconds of examiner attention; we do **not**
build it.

## Portability boundary = the container API

Everything inside the cluster — the **same images, same compose/k8s manifests** —
is portable across clouds. Only three things are provider-specific:

1. **Compute** — the cluster / container runtime (k8s, Cloud Run, or a VM).
2. **Managed Postgres** — RDS / Cloud SQL / Azure Database (+ pgvector).
3. **IAM / networking / secrets** — provisioning and identity.

These are swapped via `tfvars` and provider submodules; application code never
changes when the cloud changes. The application's hexagonal layering reinforces
this: provider adapters live only in `api/.../infrastructure/`, and the offline
default (`provider_mode="fake"`) means the platform runs end-to-end with zero
cloud dependencies.

## Modules behind stable interfaces

Each module exposes a **provider-neutral interface** (its `variables.tf` inputs
and `outputs.tf` outputs). The cloud-specific implementation lives in
`aws/ gcp/ azure/` submodules *inside* the module (notably `compute/`), so the
root environment composition only ever references the stable module interface —
not a provider's resource types.

```
infra/terraform/
├── versions.tf            # pins terraform + note: state backend = HCP Terraform free tier
├── modules/
│   ├── networking/        # vpc / subnets / firewall — stable interface
│   ├── compute/           # cluster OR container-on-VM; submodules: aws/ gcp/ azure/
│   ├── postgres/          # rds | cloud_sql | azurerm_postgresql (+ pgvector)
│   ├── object-storage/    # s3 | gcs | azure blob — product image uploads
│   └── secrets/           # kubernetes_secret | hcp_vault — Anthropic/Cohere/etc keys
└── environments/
    ├── local/             # docker-compose only — NO terraform (see ../../docker-compose.yml)
    └── dev/               # one cloud, small / scale-to-zero nodes
```

## Conventions

- Each module ships `main.tf / variables.tf / outputs.tf / versions.tf / README.md`.
- Pin providers with `~>`; commit `.terraform.lock.hcl`.
- **State backend = HCP Terraform free tier** — provider-neutral, so you don't
  need an S3 bucket before Terraform can provision anything (avoids the
  bootstrap chicken-and-egg).
- Keep `terraform fmt -recursive` clean (`make fmt` from the repo root).
- Follow the **terraform-module-library** conventions for module structure.

## Phased deploy

- **Phase 1 — local (current):** `docker compose up` from the repo root. No
  Terraform. The `environments/local/` dir is documentation only. This is the
  demo/dev path and the default.
- **Phase 2 — single cloud (optional / stretch):** GKE Autopilot or Cloud Run
  (scale-to-zero, GCP credit) **or** a single VM running docker-compose. Convert
  the compose services to manifests; `terraform apply` the `dev` environment.
  Target ~€0–30/mo with caching + scale-to-zero.
- **Phase 3 — does not exist.** Replaced by a written portability analysis in the
  thesis. Do **not** build a second provider.

## Current status

The `modules/` and `environments/` trees here are **valid HCL skeletons / stubs**:
documented, provider-agnostic interfaces with no real resources. They define the
contract for a future single-cloud Phase 2 deploy. Run `terraform fmt -check` to
verify they stay clean.
