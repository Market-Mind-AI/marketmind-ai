"""Real report generator using the Anthropic Messages API (Claude Sonnet).

Implements :class:`ReportGenerator` with structured output via tool use: the
model is forced to call ``record_opportunity_report`` whose schema mirrors
:class:`OpportunityReport`. We pass the already-computed MOS, ranked markets,
and comparable products as context; the model writes the explainable narrative
(verdict / summary / pricing / timing / citations).

The ``anthropic`` SDK is imported lazily (only ``TYPE_CHECKING``) so this module
imports without the SDK installed; the offline default is
:class:`TemplateReportGenerator`.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from marketmind.application.ports.ports import ReportGenerator
from marketmind.domain.model.analysis import Analysis
from marketmind.domain.model.report import (
    Citation,
    LaunchWindow,
    MarketRecommendation,
    OpportunityReport,
    PriceBand,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    import anthropic

# Pinned report-generation model (do not change — see project contract).
_DEFAULT_MODEL = "claude-sonnet-4-6"

_REPORT_TOOL: dict[str, Any] = {
    "name": "record_opportunity_report",
    "description": (
        "Record the explainable market-opportunity report for the analyzed "
        "product, grounded in the supplied score, markets, and comparables."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "description": "One-line headline verdict."},
            "summary": {"type": "string", "description": "Few-sentence summary."},
            "markets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "country_code": {"type": "string"},
                        "country_name": {"type": "string"},
                        "score": {"type": "number"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["country_code", "country_name", "score", "rationale"],
                },
            },
            "price_band": {
                "type": "object",
                "properties": {
                    "low": {"type": "string", "description": "Decimal string."},
                    "high": {"type": "string", "description": "Decimal string."},
                    "currency": {"type": "string", "description": "ISO-4217 code."},
                    "note": {"type": "string"},
                },
                "required": ["low", "high", "currency"],
            },
            "launch_window": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "peak_note": {"type": "string"},
                },
                "required": ["label", "peak_note"],
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
            },
            "citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "detail": {"type": "string"},
                        "as_of": {"type": "string"},
                    },
                    "required": ["source", "detail", "as_of"],
                },
            },
        },
        "required": [
            "verdict",
            "summary",
            "markets",
            "price_band",
            "launch_window",
        ],
    },
}


class ClaudeReportGenerator(ReportGenerator):
    """Explainable-report generator backed by Anthropic Claude Sonnet."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        *,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._client = client
        self._model = model

    async def generate(self, analysis: Analysis, comparables: list[dict]) -> OpportunityReport:
        context = _build_context(analysis, comparables)
        # The inline dict messages/tool_choice are valid at runtime but don't
        # match the SDK's strict TypedDict param overloads.
        message = await self._client.messages.create(  # type: ignore[call-overload]
            model=self._model,
            max_tokens=2048,
            tools=[_REPORT_TOOL],
            tool_choice={"type": "tool", "name": "record_opportunity_report"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a commercial-intelligence analyst. Using the "
                        "JSON context below (the transparent Market Opportunity "
                        "Score, ranked markets, attributes, and comparable "
                        "products), write an explainable opportunity report. Be "
                        "concrete and cite the score and comparables. Call "
                        "record_opportunity_report with your result.\n\n"
                        f"{json.dumps(context, indent=2, default=str)}"
                    ),
                }
            ],
        )
        tool_input = self._first_tool_input(message)
        return _report_from_tool_input(tool_input, analysis)

    @staticmethod
    def _first_tool_input(message: Any) -> dict[str, Any]:
        for block in message.content:
            if getattr(block, "type", None) == "tool_use":
                return dict(block.input)
        raise ValueError("Claude did not return a record_opportunity_report tool_use block.")


def _build_context(analysis: Analysis, comparables: list[dict]) -> dict[str, Any]:
    score = analysis.score
    attributes = analysis.attributes
    return {
        "attributes": (
            None
            if attributes is None
            else {
                "category": attributes.category,
                "subcategory": attributes.subcategory,
                "materials": list(attributes.materials),
                "color": attributes.color,
                "style": attributes.style,
                "key_features": list(attributes.key_features),
                "suggested_keywords": list(attributes.suggested_keywords),
                "confidence": attributes.confidence,
            }
        ),
        "score": (
            None
            if score is None
            else {
                "total": score.total,
                "tier": score.tier,
                "explanation": score.explanation(),
            }
        ),
        "markets": [
            {
                "country_code": m.country_code,
                "country_name": m.country_name,
                "score": m.score,
                "rationale": m.rationale,
            }
            for m in analysis.markets
        ],
        "comparables": comparables,
        "as_of": analysis.created_at.date().isoformat(),
    }


def _to_decimal(value: Any, default: str) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _report_from_tool_input(data: dict[str, Any], analysis: Analysis) -> OpportunityReport:
    """Map the tool-use payload into the domain VO with safe fallbacks."""
    markets = tuple(
        MarketRecommendation(
            country_code=str(m["country_code"]),
            country_name=str(m.get("country_name", m["country_code"])),
            score=min(100.0, max(0.0, float(m.get("score", 0.0)))),
            rationale=str(m.get("rationale", "")),
        )
        for m in data.get("markets", ())
    )
    if not markets:
        markets = analysis.markets

    pb = data.get("price_band", {})
    low = _to_decimal(pb.get("low"), "0")
    high = _to_decimal(pb.get("high"), str(low))
    if high < low:
        low, high = high, low
    currency = str(pb.get("currency", "USD"))[:3].upper() or "USD"
    price_band = PriceBand(low=low, high=high, currency=currency, note=str(pb.get("note", "")))

    lw = data.get("launch_window", {})
    launch_window = LaunchWindow(
        label=str(lw.get("label") or "Any time"),
        peak_note=str(lw.get("peak_note", "")),
    )

    citations = tuple(
        Citation(
            source=str(c.get("source") or "Claude"),
            detail=str(c.get("detail", "")),
            as_of=str(c.get("as_of") or analysis.created_at.date().isoformat()),
        )
        for c in data.get("citations", ())
        if c.get("source")
    )

    return OpportunityReport(
        verdict=str(data.get("verdict") or "Market opportunity"),
        summary=str(data.get("summary", "")),
        markets=markets,
        price_band=price_band,
        launch_window=launch_window,
        recommendations=tuple(str(r) for r in data.get("recommendations", ())),
        citations=citations,
    )
