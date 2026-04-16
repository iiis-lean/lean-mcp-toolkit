"""Helpers for deriving machine-readable output schemas from contract types."""

from __future__ import annotations

import logging
from typing import Any

from .base import JsonDict

_LOG = logging.getLogger(__name__)


def build_output_schema(response_type: Any) -> JsonDict | None:
    """Build JSON Schema for one structured tool response type."""
    if response_type is None:
        return None
    try:
        from pydantic import TypeAdapter
    except Exception:  # pragma: no cover - optional runtime dependency
        return None

    try:
        schema = TypeAdapter(response_type).json_schema()
    except Exception as exc:  # pragma: no cover - defensive
        _LOG.debug("failed to derive output schema for %r: %s", response_type, exc)
        return None
    if not isinstance(schema, dict):
        return None
    return schema


__all__ = ["build_output_schema"]
