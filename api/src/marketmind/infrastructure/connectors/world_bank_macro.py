"""World Bank macro provider — feeds the GROWTH factor.

The World Bank Indicators API is free and requires no API key, so this adapter
includes a minimal REAL httpx call (guarded with clear failure semantics). It
fetches a recent GDP-growth indicator for a reference country and returns it as
the raw GROWTH signal. ``MarketSignalProvider.fetch`` must raise on hard failure
(the use case maps that to an imputed/neutral score) — it never returns a
sentinel.

A best-effort :class:`WorldBankGeoMarketRanker` is also provided, but it is a
stub: ranking by per-country indicators is deferred.
"""

from __future__ import annotations

import httpx

from marketmind.application.ports.ports import GeoMarketRanker, MarketSignalProvider
from marketmind.domain.model.product import ProductAttributes
from marketmind.domain.model.report import MarketRecommendation
from marketmind.domain.model.scoring import MosFactor

# NY.GDP.MKTP.KD.ZG = GDP growth (annual %). World aggregate by default.
_API_URL = "https://api.worldbank.org/v2/country/WLD/indicator/NY.GDP.MKTP.KD.ZG"


class WorldBankMacroProvider(MarketSignalProvider):
    """Macro/growth signal from the (free, key-less) World Bank Indicators API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def factor(self) -> MosFactor:
        return MosFactor.GROWTH

    async def fetch(self, attributes: ProductAttributes) -> float:
        """Return the most recent non-null world GDP-growth (annual %).

        Raises on any network/parse failure so the use case can impute a neutral
        score rather than silently using a bogus value.
        """
        response = await self._client.get(
            _API_URL,
            params={"format": "json", "per_page": "10", "mrnev": "5"},
        )
        response.raise_for_status()
        payload = response.json()
        # Shape: [metadata, [ {date, value, ...}, ... ]]
        if not isinstance(payload, list) or len(payload) < 2:
            raise ValueError("Unexpected World Bank API response shape")
        rows = payload[1] or []
        for row in rows:
            value = row.get("value")
            if value is not None:
                return float(value)
        raise ValueError("World Bank API returned no usable GDP-growth value")


class WorldBankGeoMarketRanker(GeoMarketRanker):
    """Optional World-Bank-backed country ranker (deferred)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def rank(
        self,
        attributes: ProductAttributes,
        signals: dict[MosFactor, float | None],
    ) -> list[MarketRecommendation]:
        # TODO: pull per-country indicators (GDP growth, consumption, ecommerce
        # penetration) and rank candidate markets. Deferred — use the fake
        # ranker offline.
        raise NotImplementedError(
            "WorldBankGeoMarketRanker is not implemented; "
            "use FakeGeoMarketRanker in offline/fake mode."
        )
