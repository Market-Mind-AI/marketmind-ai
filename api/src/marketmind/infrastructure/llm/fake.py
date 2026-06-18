"""Offline fake LLM adapters: keyword-based extraction + template report.

Neither requires an LLM, an API key, or network access. They let the whole
pipeline run end-to-end offline (the default ``provider_mode="fake"``).

- :class:`FakeAttributeExtractor` derives :class:`ProductAttributes` from simple
  keyword heuristics over the free-text description.
- :class:`TemplateReportGenerator` assembles a coherent :class:`OpportunityReport`
  from the already-computed score and ranked markets — no generation involved.
  (Exported also as ``FakeReportGenerator`` to match the contract name.)
"""

from __future__ import annotations

from decimal import Decimal

from marketmind.application.ports.ports import (
    ProductAttributeExtractor,
    ReportGenerator,
)
from marketmind.domain.model.analysis import Analysis
from marketmind.domain.model.product import ProductAttributes
from marketmind.domain.model.report import (
    Citation,
    LaunchWindow,
    MarketRecommendation,
    OpportunityReport,
    PriceBand,
)

# Ordered keyword → (category, subcategory, default materials, style) heuristics.
_CATEGORY_RULES: tuple[tuple[tuple[str, ...], str, str, tuple[str, ...], str], ...] = (
    (
        ("sneaker", "shoe", "boot", "footwear"),
        "Footwear",
        "Casual Shoes",
        ("textile", "rubber"),
        "casual",
    ),
    (
        ("bag", "backpack", "purse", "tote"),
        "Bags & Luggage",
        "Backpacks",
        ("nylon", "polyester"),
        "functional",
    ),
    (("watch", "smartwatch"), "Watches", "Smartwatches", ("aluminium", "glass"), "modern"),
    (
        ("jacket", "coat", "hoodie", "sweater"),
        "Apparel",
        "Outerwear",
        ("cotton", "polyester"),
        "streetwear",
    ),
    (
        ("lamp", "chair", "table", "sofa", "desk"),
        "Home & Furniture",
        "Furniture",
        ("wood", "metal"),
        "minimalist",
    ),
    (
        ("bottle", "mug", "tumbler", "flask"),
        "Kitchen & Dining",
        "Drinkware",
        ("stainless steel",),
        "utilitarian",
    ),
    (("headphone", "earbud", "speaker"), "Electronics", "Audio", ("plastic", "silicone"), "modern"),
    (("toy", "game", "puzzle"), "Toys & Games", "Toys", ("plastic",), "playful"),
)

_COLOR_KEYWORDS = (
    "black",
    "white",
    "red",
    "blue",
    "green",
    "yellow",
    "pink",
    "grey",
    "gray",
    "brown",
    "beige",
    "navy",
    "silver",
    "gold",
)

_MATERIAL_KEYWORDS = (
    "leather",
    "cotton",
    "wool",
    "silk",
    "linen",
    "denim",
    "wood",
    "bamboo",
    "steel",
    "aluminium",
    "aluminum",
    "glass",
    "ceramic",
    "plastic",
    "rubber",
    "nylon",
    "polyester",
    "silicone",
)


class FakeAttributeExtractor(ProductAttributeExtractor):
    """Derives plausible structured attributes from description keywords."""

    def __init__(self) -> None:
        pass

    async def extract(self, description: str, image_refs: list[str]) -> ProductAttributes:
        text = (description or "").lower()
        words = [w.strip(".,!?;:\"'()[]") for w in text.split()]

        category: str = "General Merchandise"
        subcategory: str = "Miscellaneous"
        default_materials: tuple[str, ...] = ("composite",)
        style: str = "contemporary"
        for keywords, cat, sub, mats, sty in _CATEGORY_RULES:
            if any(k in text for k in keywords):
                category, subcategory, default_materials, style = cat, sub, mats, sty
                break

        materials = tuple(m for m in _MATERIAL_KEYWORDS if m in text) or default_materials
        color = next((c for c in _COLOR_KEYWORDS if c in text), "unspecified")

        # Key features: a few salient descriptive words (deduped, capped).
        stop = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "with",
            "for",
            "this",
            "that",
            "is",
            "are",
            "of",
            "to",
            "in",
            "on",
            "it",
            "very",
            "made",
        }
        seen: list[str] = []
        for w in words:
            if len(w) > 3 and w not in stop and w not in seen:
                seen.append(w)
            if len(seen) >= 5:
                break
        key_features = tuple(seen) or ("product",)

        keyword_pool = [category.lower(), subcategory.lower(), style, color]
        keyword_pool.extend(materials)
        keyword_pool.extend(key_features)
        suggested_keywords = tuple(
            dict.fromkeys(k for k in keyword_pool if k and k != "unspecified")
        )[:8]

        # Confidence scales with how much signal we found in the text.
        signal = (
            (category != "General Merchandise")
            + (color != "unspecified")
            + bool(materials)
            + bool(key_features and key_features != ("product",))
        )
        confidence = round(0.45 + 0.125 * signal, 3)

        return ProductAttributes(
            category=category,
            subcategory=subcategory,
            materials=tuple(materials),
            color=color,
            style=style,
            key_features=key_features,
            suggested_keywords=suggested_keywords,
            confidence=min(confidence, 0.95),
        )


_VERDICT_BY_TIER = {
    "strong": "Strong market opportunity",
    "moderate": "Moderate market opportunity",
    "weak": "Limited market opportunity",
}

# Coarse, attribute-aware default price bands by category (illustrative only).
_PRICE_BANDS: dict[str, tuple[str, str]] = {
    "Footwear": ("45", "120"),
    "Bags & Luggage": ("35", "95"),
    "Watches": ("120", "350"),
    "Apparel": ("25", "80"),
    "Home & Furniture": ("80", "260"),
    "Kitchen & Dining": ("15", "45"),
    "Electronics": ("60", "180"),
    "Toys & Games": ("12", "40"),
}


class TemplateReportGenerator(ReportGenerator):
    """Builds a coherent OpportunityReport from the score + markets, no LLM."""

    def __init__(self) -> None:
        pass

    async def generate(self, analysis: Analysis, comparables: list[dict]) -> OpportunityReport:
        score = analysis.score
        attributes = analysis.attributes
        if score is None or attributes is None:
            raise ValueError(
                "TemplateReportGenerator requires a scored analysis " "with extracted attributes."
            )

        tier = score.tier
        verdict = _VERDICT_BY_TIER.get(tier, "Market opportunity")

        markets = analysis.markets or ()
        if not markets:
            # Fallback single market so the report is always well-formed.
            markets = (
                MarketRecommendation(
                    country_code="US",
                    country_name="United States",
                    score=round(score.total, 1),
                    rationale="Default primary market (no ranking available).",
                ),
            )

        top_market = markets[0]
        summary = (
            f"{attributes.category} ({attributes.style}, {attributes.color}) "
            f"scores {score.total:.0f}/100 — a {tier} opportunity. "
            f"The strongest target market is {top_market.country_name} "
            f"({top_market.score:.0f}/100). "
            f"{score.explanation().splitlines()[0]}"
        )

        low_s, high_s = _PRICE_BANDS.get(attributes.category, ("20", "60"))
        # Nudge the band up/down with the opportunity tier.
        multiplier = {"strong": Decimal("1.10"), "moderate": Decimal("1.0")}.get(
            tier, Decimal("0.90")
        )
        price_band = PriceBand(
            low=(Decimal(low_s) * multiplier).quantize(Decimal("0.01")),
            high=(Decimal(high_s) * multiplier).quantize(Decimal("0.01")),
            currency="USD",
            note=f"Indicative band for {attributes.category}, adjusted for a {tier} score.",
        )

        # Timing driven by the seasonality factor where available.
        seasonality_fs = next(
            (fs for fs in score.factor_scores if fs.factor.value == "seasonality"),
            None,
        )
        if seasonality_fs is not None and seasonality_fs.normalized_score >= 60:
            launch_window = LaunchWindow(
                label="Q4 (pre-holiday)",
                peak_note="High seasonality detected; align launch with the Q4 peak.",
            )
        else:
            launch_window = LaunchWindow(
                label="Q1-Q2 (any time)",
                peak_note="Low seasonality; demand is broadly stable year-round.",
            )

        keyword = (
            attributes.suggested_keywords[0]
            if attributes.suggested_keywords
            else attributes.category
        )
        recommendations = (
            f"Lead with the {top_market.country_name} market and the " f"'{keyword}' keyword set.",
            f"Price within {price_band.currency} {price_band.low}-{price_band.high} "
            "to match the band.",
            f"Time the launch to the {launch_window.label} window.",
        )

        citations = (
            Citation(
                source="MarketMind MOS",
                detail=f"Transparent weighted score ({tier} tier).",
                as_of=analysis.created_at.date().isoformat(),
            ),
            Citation(
                source="Comparable products",
                detail=f"{len(comparables)} comparable item(s) considered.",
                as_of=analysis.created_at.date().isoformat(),
            ),
        )

        return OpportunityReport(
            verdict=verdict,
            summary=summary,
            markets=tuple(markets),
            price_band=price_band,
            launch_window=launch_window,
            recommendations=recommendations,
            citations=citations,
        )


# Contract alias: the authoritative contract names the offline report adapter
# ``FakeReportGenerator``; the task brief names it ``TemplateReportGenerator``.
# Same adapter — expose both.
FakeReportGenerator = TemplateReportGenerator
