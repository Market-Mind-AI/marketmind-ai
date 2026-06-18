"""Real (stub) eBay marketplace provider — feeds the CONSUMER factor.

eBay's Browse / Marketplace Insights APIs require an OAuth app credential
(``app_id``). This adapter is a credentialed stub documenting the intended call;
it raises ``NotImplementedError`` until implemented. The offline default uses
:class:`FakeConsumerProvider` instead.
"""

from __future__ import annotations

import httpx

from marketmind.application.ports.ports import MarketSignalProvider
from marketmind.domain.model.product import ProductAttributes
from marketmind.domain.model.scoring import MosFactor

_API_BASE = "https://api.ebay.com/buy/browse/v1"


class EbayMarketplaceProvider(MarketSignalProvider):
    """Consumer-demand signal derived from eBay marketplace activity."""

    def __init__(self, client: httpx.AsyncClient, *, app_id: str) -> None:
        self._client = client
        self._app_id = app_id

    @property
    def factor(self) -> MosFactor:
        return MosFactor.CONSUMER

    async def fetch(self, attributes: ProductAttributes) -> float:
        # TODO: obtain an OAuth application token from self._app_id, then query
        #   f"{_API_BASE}/item_summary/search?q=<keywords>"
        # and reduce listing volume / sold counts to a 0..100 demand signal.
        raise NotImplementedError(
            "EbayMarketplaceProvider requires eBay OAuth credentials; "
            "use FakeConsumerProvider in offline/fake mode."
        )
