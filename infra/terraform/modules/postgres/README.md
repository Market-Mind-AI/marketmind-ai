# Module: postgres

Managed Postgres 16 + **pgvector** for MarketMind AI — backs the analysis
repository and the vector store (comparable-product retrieval). Provider-neutral
interface; implemented per cloud as RDS / Cloud SQL / Azure Database.

| Input | Description |
|---|---|
| `name_prefix` | Resource name prefix. |
| `region` | Cloud region. |
| `network_id` | Network for private connectivity. |
| `postgres_version` | Major version (default `16`). |
| `db_name` / `db_user` | Initial database + master user. |
| `instance_size` | Provider-neutral size hint. |
| `enable_pgvector` | Create the `vector` extension (default `true`). |
| `tags` | Tags / labels. |

| Output | Description |
|---|---|
| `host` / `port` | Connection endpoint. |
| `database_url` | `postgresql+asyncpg://…` DSN → `MARKETMIND_DATABASE_URL` (sensitive). |

**Status:** stub — no real resources. See `../../README.md`.
