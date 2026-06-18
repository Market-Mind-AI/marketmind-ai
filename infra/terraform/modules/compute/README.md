# Module: compute

Runs the MarketMind `api` + `web` container images. The **most provider-specific
module**, so its per-cloud implementations live in **submodules inside this
directory**:

```
compute/
├── aws/     # ECS/Fargate or EKS
├── gcp/     # Cloud Run or GKE Autopilot (default target — scale-to-zero)
└── azure/   # Container Apps or AKS
```

This top-level module is the **stable interface** environments reference; it
dispatches to the submodule selected by `var.cloud`. The portability boundary is
the container API — the same images run unchanged across all three.

| Input | Description |
|---|---|
| `name_prefix` | Resource name prefix. |
| `region` | Cloud region. |
| `cloud` | Target cloud: `aws` \| `gcp` \| `azure` (selects submodule). |
| `network_id` | Network from the `networking` module. |
| `api_image` / `web_image` | Container image refs. |
| `min_instances` / `max_instances` | Scaling (min `0` = scale-to-zero). |
| `env` | Non-secret env vars for the api container. |
| `tags` | Tags / labels. |

| Output | Description |
|---|---|
| `api_url` | Public api URL. |
| `web_url` | Public web URL. |

**Status:** stub — interface only; `aws/ gcp/ azure/` submodules to be authored
for Phase 2. See `../../README.md`.
