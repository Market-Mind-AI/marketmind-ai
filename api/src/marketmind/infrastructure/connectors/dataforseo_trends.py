"""Real (stub) DataForSEO trends provider — feeds the TREND factor.

DataForSEO's Google Trends / Keyword endpoints require Basic-auth credentials
(login + password). This adapter is a credentialed stub: it documents the
intended call and raises ``NotImplementedError`` until implemented. The offline
default uses :class:`FakeTrendsProvider` instead.
"""

from __future__ import annotations

import httpx

from marketmind.application.ports.ports import MarketSignalProvider
from marketmind.domain.model.product import ProductAttributes
from marketmind.domain.model.scoring import MosFactor

_API_BASE = "https://api.dataforseo.com/v3"


class DataForSeoTrendsProvider(MarketSignalProvider):
    """Search-interest trend signal from the DataForSEO API."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        login: str,
        password: str,
    ) -> None:
        self._client = client
        self._login = login
        self._password = password

    @property
    def factor(self) -> MosFactor:
        return MosFactor.TREND

    async def fetch(self, attributes: ProductAttributes) -> float:
        # TODO: POST the product's suggested_keywords to
        #   f"{_API_BASE}/keywords_data/google_trends/explore/live"
        # using httpx Basic auth (self._login, self._password), then reduce the
        # returned interest-over-time series to a single 0..100 trend value.
        raise NotImplementedError(
            "DataForSeoTrendsProvider requires live DataForSEO credentials; "
            "use FakeTrendsProvider in offline/fake mode."
        )
