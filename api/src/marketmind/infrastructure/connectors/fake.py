"""Offline fake market-signal providers and geo-market ranker.

These adapters let the whole pipeline run with no external services or API keys
(the default ``provider_mode="fake"``). Every value is DETERMINISTIC: derived
from a stable hash of the product attributes plus a per-provider salt, so the
same product always yields the same signals (important for reproducible MOS and
for the thesis demo / tests).

Each provider declares the single :class:`MosFactor` it feeds and implements
:class:`MarketSignalProvider`. ``fetch`` returns a raw ``float`` (the use case
maps hard failures to ``None``/imputed — fakes never need a sentinel).
"""

from __future__ import annotations

import hashlib

from marketmind.application.ports.ports import GeoMarketRanker, MarketSignalProvider
from marketmind.domain.model.product import ProductAttributes
from marketmind.domain.model.report import MarketRecommendation
from marketmind.domain.model.scoring import MosFactor


def _attributes_fingerprint(attributes: ProductAttributes) -> str:
    """A stable string fingerprint of the salient attribute fields."""
    parts = (
        attributes.category,
        attributes.subcategory,
        attributes.color,
        attributes.style,
        "|".join(attributes.materials),
        "|".join(attributes.key_features),
        "|".join(attributes.suggested_keywords),
    )
    return "␟".join(p.strip().lower() for p in parts)


def _stable_unit(seed: int, salt: str, fingerprint: str) -> float:
    """Deterministic float in [0.0, 1.0) from (seed, salt, fingerprint).

    Uses BLAKE2b so results are stable across processes/Python runs (unlike the
    salted built-in ``hash``).
    """
    digest = hashlib.blake2b(
        f"{seed}␟{salt}␟{fingerprint}".encode("utf-8"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, "big") / float(1 << 64)


class _DeterministicProvider:
    """Shared base: maps the attribute fingerprint to a raw value in a range."""

    _salt: str = ""
    _low: float = 0.0
    _high: float = 1.0

    def __init__(self, *, seed: int = 0) -> None:
        self._seed = seed

    def _raw(self, attributes: ProductAttributes) -> float:
        unit = _stable_unit(
            self._seed, self._salt, _attributes_fingerprint(attributes)
        )
        return self._low + unit * (self._high - self._low)


class FakeTrendsProvider(_DeterministicProvider, MarketSignalProvider):
    """Fakes a search-interest trend signal (stands in for DataForSEO/Trends)."""

    _salt = "trends"
    _low, _high = 0.0, 100.0

    @property
    def factor(self) -> MosFactor:
        return MosFactor.TREND

    async def fetch(self, attributes: ProductAttributes) -> float:
        return self._raw(attributes)


class FakeMacroProvider(_DeterministicProvider, MarketSignalProvider):
    """Fakes a macro/growth signal (stands in for World Bank indicators)."""

    _salt = "macro-growth"
    _low, _high = -2.0, 8.0  # plausible GDP-growth-like percentage range

    @property
    def factor(self) -> MosFactor:
        return MosFactor.GROWTH

    async def fetch(self, attributes: ProductAttributes) -> float:
        return self._raw(attributes)


class FakeGeographicProvider(_DeterministicProvider, MarketSignalProvider):
    """Fakes a geographic-fit signal."""

    _salt = "geographic"
    _low, _high = 0.0, 100.0

    @property
    def factor(self) -> MosFactor:
        return MosFactor.GEOGRAPHIC

    async def fetch(self, attributes: ProductAttributes) -> float:
        return self._raw(attributes)


class FakeSeasonalityProvider(_DeterministicProvider, MarketSignalProvider):
    """Fakes a seasonality-strength signal (0 = flat, 1 = highly seasonal)."""

    _salt = "seasonality"
    _low, _high = 0.0, 1.0

    @property
    def factor(self) -> MosFactor:
        return MosFactor.SEASONALITY

    async def fetch(self, attributes: ProductAttributes) -> float:
        return self._raw(attributes)


class FakeConsumerProvider(_DeterministicProvider, MarketSignalProvider):
    """Fakes a consumer/marketplace-demand signal (stands in for eBay etc.)."""

    _salt = "consumer-marketplace"
    _low, _high = 0.0, 100.0

    @property
    def factor(self) -> MosFactor:
        return MosFactor.CONSUMER

    async def fetch(self, attributes: ProductAttributes) -> float:
        return self._raw(attributes)


# The task brief names this provider ``FakeMarketplaceProvider``; the
# authoritative contract names it ``FakeConsumerProvider``. They are the same
# CONSUMER-factor adapter — keep both names available so DI wiring against
# either name works.
FakeMarketplaceProvider = FakeConsumerProvider


# Candidate target markets the fake ranker scores. ISO-3166 alpha-2 codes.
_CANDIDATE_MARKETS: tuple[tuple[str, str], ...] = (
    ("US", "United States"),
    ("DE", "Germany"),
    ("GB", "United Kingdom"),
    ("JP", "Japan"),
    ("FR", "France"),
    ("CA", "Canada"),
    ("AU", "Australia"),
    ("ES", "Spain"),
)


class FakeGeoMarketRanker(GeoMarketRanker):
    """Deterministically ranks candidate countries for a product.

    Blends a per-country hash of the product fingerprint with the overall
    geographic signal so the ranking is stable and plausibly attribute-driven.
    """

    def __init__(self, *, seed: int = 0) -> None:
        self._seed = seed

    async def rank(
        self,
        attributes: ProductAttributes,
        signals: dict[MosFactor, float | None],
    ) -> list[MarketRecommendation]:
        fingerprint = _attributes_fingerprint(attributes)
        geo_signal = signals.get(MosFactor.GEOGRAPHIC)
        geo_bias = (geo_signal / 100.0) if geo_signal is not None else 0.5

        scored: list[MarketRecommendation] = []
        for code, name in _CANDIDATE_MARKETS:
            unit = _stable_unit(self._seed, f"market-{code}", fingerprint)
            # Weight the country-specific hash with the global geo bias.
            score = round(min(100.0, max(0.0, 100.0 * (0.6 * unit + 0.4 * geo_bias))), 1)
            scored.append(
                MarketRecommendation(
                    country_code=code,
                    country_name=name,
                    score=score,
                    rationale=(
                        f"Estimated fit for {attributes.category} "
                        f"({attributes.style}) in {name}: "
                        f"attribute affinity {unit:.0%}, geographic signal "
                        f"{geo_bias:.0%}."
                    ),
                )
            )

        scored.sort(key=lambda m: m.score, reverse=True)
        return scored[:5]
