"""Uvicorn entrypoint.

Module-level ``app`` enables ``uvicorn marketmind.main:app``; ``main()`` runs
the server using host/port/log-level from settings (offline by default).
"""

from __future__ import annotations

from marketmind.infrastructure.api.app import create_app
from marketmind.infrastructure.config.settings import get_settings

app = create_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "marketmind.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
