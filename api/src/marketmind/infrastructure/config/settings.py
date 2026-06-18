"""Application settings (pydantic-settings).

Defaults are tuned for a fully offline, all-fakes run: ``provider_mode="fake"``
plus in-memory persistence means the app boots end-to-end with no external
services and no API keys. Real adapters are selected only when
``provider_mode="real"`` and the relevant credentials are present.

Settings live in the infrastructure layer only — pydantic must never leak into
``application`` or ``domain``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration loaded from environment / ``.env``.

    Env prefix is ``MARKETMIND_`` (e.g. ``MARKETMIND_PROVIDER_MODE=real``).
    """

    model_config = SettingsConfigDict(
        env_prefix="MARKETMIND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- provider / persistence selection -------------------------------
    provider_mode: Literal["fake", "real"] = "fake"
    database_url: str = (
        "postgresql+asyncpg://marketmind:marketmind@localhost:5432/marketmind"
    )
    use_in_memory_persistence: bool = True

    # --- LLM / embedding credentials & models ---------------------------
    anthropic_api_key: str | None = None
    cohere_api_key: str | None = None
    extraction_model: str = "claude-haiku-4-5-20251001"
    report_model: str = "claude-sonnet-4-6"
    embedding_model: str = "embed-english-v3.0"
    embedding_dimensions: int = 1024

    # --- object storage -------------------------------------------------
    storage_root: Path = Path("./.data/uploads")
    storage_base_url: str = ""

    # --- external connectors (real mode only) ---------------------------
    dataforseo_login: str | None = None
    dataforseo_password: str | None = None
    ebay_app_id: str | None = None

    # --- HTTP server ----------------------------------------------------
    cors_origins: list[str] = ["*"]
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
