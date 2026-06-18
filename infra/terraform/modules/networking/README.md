# Module: networking

Provider-neutral VPC / subnets / firewall for MarketMind AI. Exposes a stable
interface (`variables.tf` / `outputs.tf`); the cloud-specific implementation is
swapped per environment.

| Input | Description |
|---|---|
| `name_prefix` | Resource name prefix (default `marketmind`). |
| `region` | Cloud region. |
| `cidr_block` | Primary network CIDR. |
| `tags` | Tags / labels. |

| Output | Description |
|---|---|
| `network_id` | VPC / network ID (consumed by `compute`, `postgres`). |
| `subnet_ids` | Subnet IDs. |

**Status:** stub — no real resources. See `../../README.md` for strategy.
