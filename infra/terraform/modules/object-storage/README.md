# Module: object-storage

Bucket / container for uploaded product images — the cloud counterpart of the
local `LocalFilesystemObjectStorage` adapter (the api's `S3ObjectStorage` adapter
binds to it). Provider-neutral interface; implemented per cloud as S3 / GCS /
Azure Blob.

| Input | Description |
|---|---|
| `name_prefix` | Bucket name prefix. |
| `region` | Region / location. |
| `versioning` | Enable object versioning. |
| `force_destroy` | Delete non-empty bucket on destroy (dev only). |
| `tags` | Tags / labels. |

| Output | Description |
|---|---|
| `bucket_name` | Bucket / container name (→ `S3ObjectStorage`). |
| `bucket_url` | Base URL → `MARKETMIND_STORAGE_BASE_URL`. |

**Status:** stub — no real resources. See `../../README.md`.
