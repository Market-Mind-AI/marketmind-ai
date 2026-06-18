"""Real vision-LLM attribute extractor using the Anthropic Messages API.

Implements :class:`ProductAttributeExtractor` with Claude Haiku (vision) and
structured output via tool use: a single tool ``record_product_attributes``
whose ``input_schema`` mirrors :class:`ProductAttributes`, forced with
``tool_choice``. The model returns one ``tool_use`` block we map to the VO.

The ``anthropic`` SDK is imported lazily (inside ``__init__``) so this module
remains importable with the SDK absent — the offline default uses
:class:`FakeAttributeExtractor`. Images are loaded from :class:`ObjectStorage`
by ref and sent as base64 image content blocks.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

from marketmind.application.ports.ports import (
    ObjectStorage,
    ProductAttributeExtractor,
)
from marketmind.domain.model.product import ProductAttributes

if TYPE_CHECKING:  # pragma: no cover - typing only
    import anthropic

# Pinned vision/extraction model (do not change — see project contract).
_DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# Structured-output tool: the model is forced to call this so we get a
# schema-validated attribute object back instead of free text.
_EXTRACTION_TOOL: dict[str, Any] = {
    "name": "record_product_attributes",
    "description": (
        "Record the structured commercial attributes extracted from the "
        "product images and description."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Top-level product category."},
            "subcategory": {"type": "string", "description": "More specific subcategory."},
            "materials": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Primary materials.",
            },
            "color": {"type": "string", "description": "Dominant color."},
            "style": {"type": "string", "description": "Design style descriptor."},
            "key_features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Salient selling-point features.",
            },
            "suggested_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Marketplace search keywords.",
            },
            "confidence": {
                "type": "number",
                "description": "Self-reported confidence in [0, 1].",
            },
        },
        "required": [
            "category",
            "subcategory",
            "materials",
            "color",
            "style",
            "key_features",
            "suggested_keywords",
            "confidence",
        ],
    },
}

_MEDIA_TYPE_BY_SUFFIX = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "image/webp",
    b"GIF8": "image/gif",
}


def _sniff_media_type(data: bytes) -> str:
    """Best-effort image media-type sniff (defaults to PNG)."""
    for magic, media_type in _MEDIA_TYPE_BY_SUFFIX.items():
        if data.startswith(magic):
            return media_type
    return "image/png"


class ClaudeAttributeExtractor(ProductAttributeExtractor):
    """Vision-LLM extractor backed by Anthropic Claude Haiku."""

    def __init__(
        self,
        client: "anthropic.AsyncAnthropic",
        storage: ObjectStorage,
        *,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._client = client
        self._storage = storage
        self._model = model

    async def extract(
        self, description: str, image_refs: list[str]
    ) -> ProductAttributes:
        content: list[dict[str, Any]] = []
        for ref in image_refs:
            try:
                raw = await self._storage.load(ref)
            except Exception:  # noqa: BLE001 - skip unreadable images, keep going
                continue
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": _sniff_media_type(raw),
                        "data": base64.standard_b64encode(raw).decode("ascii"),
                    },
                }
            )
        content.append(
            {
                "type": "text",
                "text": (
                    "Extract the structured commercial attributes for this "
                    "product. Description provided by the seller:\n\n"
                    f"{description}\n\n"
                    "Call record_product_attributes with your best estimate."
                ),
            }
        )

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            tools=[_EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "record_product_attributes"},
            messages=[{"role": "user", "content": content}],
        )

        tool_input = self._first_tool_input(message)
        return _attributes_from_tool_input(tool_input)

    @staticmethod
    def _first_tool_input(message: Any) -> dict[str, Any]:
        for block in message.content:
            if getattr(block, "type", None) == "tool_use":
                return dict(block.input)
        raise ValueError(
            "Claude did not return a record_product_attributes tool_use block."
        )


def _attributes_from_tool_input(data: dict[str, Any]) -> ProductAttributes:
    """Map the tool-use payload into the domain VO, clamping confidence."""
    confidence = float(data.get("confidence", 0.5))
    confidence = min(1.0, max(0.0, confidence))
    return ProductAttributes(
        category=str(data["category"]),
        subcategory=str(data.get("subcategory", "")),
        materials=tuple(str(m) for m in data.get("materials", ())),
        color=str(data.get("color", "unspecified")),
        style=str(data.get("style", "")),
        key_features=tuple(str(f) for f in data.get("key_features", ())),
        suggested_keywords=tuple(str(k) for k in data.get("suggested_keywords", ())),
        confidence=confidence,
    )
