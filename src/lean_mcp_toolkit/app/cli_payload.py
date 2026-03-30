"""Payload construction helpers for dynamic CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cli_catalog import ToolMeta


def load_payload_base(*, json_text: str | None, payload_file: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if payload_file:
        loaded = json.loads(Path(payload_file).read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("payload file must contain a JSON object")
        payload.update(loaded)
    if json_text:
        loaded = json.loads(json_text)
        if not isinstance(loaded, dict):
            raise ValueError("--json must decode to a JSON object")
        payload.update(loaded)
    return payload


def namespace_to_payload(ns: Any, tool: ToolMeta) -> dict[str, Any]:
    payload = load_payload_base(
        json_text=getattr(ns, "__payload_json", None),
        payload_file=getattr(ns, "__payload_file", None),
    )
    for param in tool.params:
        value = getattr(ns, param.name, None)
        if value is None:
            continue
        if isinstance(value, list):
            if not value:
                continue
            payload[param.name] = value
            continue
        payload[param.name] = value
    return payload
