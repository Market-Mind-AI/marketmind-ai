# Environment: local

**No Terraform here by design.** The local environment is the
`docker compose` stack at the repo root (`../../../../docker-compose.yml`):

```sh
make up        # db (pgvector) + api (FastAPI) + web (Astro)
make logs
make down
```

The api defaults to `provider_mode="fake"`, so the whole platform runs offline
with no cloud resources and no API keys. This directory exists only to mark the
local phase in the phased-deploy strategy (see `../../../README.md`).
