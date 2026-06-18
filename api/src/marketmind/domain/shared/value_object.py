"""Mixin for immutable value objects.

Some value objects freeze their internal mappings with ``MappingProxyType`` to
stay truly immutable. ``MappingProxyType`` cannot be pickled or deep-copied, so a
naive ``copy.deepcopy`` of an aggregate containing one of these VOs fails (e.g. an
in-memory repository snapshotting an :class:`~marketmind.domain.model.analysis.Analysis`).

Because these objects are immutable, sharing a single instance across copies is
always safe — so ``__copy__``/``__deepcopy__`` simply return ``self``. This keeps
the domain pure (no external deps) while making aggregates snapshot-safe.
"""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T", bound="ImmutableValue")


class ImmutableValue:
    """Marker mixin that makes a frozen value object copy/deepcopy-safe."""

    __slots__ = ()

    def __copy__(self: T) -> T:
        return self

    def __deepcopy__(self: T, memo: dict[int, Any]) -> T:
        return self
