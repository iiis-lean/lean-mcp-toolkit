"""Environment variable parsing for toolkit config."""

from __future__ import annotations

import os
from typing import Any, Mapping

from ..contracts.base import JsonDict

ENV_PREFIX = "LEAN_MCP_TOOLKIT__"


def _coerce_scalar(value: str) -> Any:
    text = value.strip()
    lower = text.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        try:
            return int(text)
        except ValueError:
            pass
    return text


def _coerce_value(value: str) -> Any:
    if "," in value:
        parts = [part.strip() for part in value.split(",") if part.strip()]
        return [_coerce_scalar(part) for part in parts]
    return _coerce_scalar(value)


def _set_nested(mapping: JsonDict, keys: list[str], value: Any) -> None:
    if not keys:
        return
    current: JsonDict = mapping
    for key in keys[:-1]:
        existing = current.get(key)
        if not isinstance(existing, dict):
            next_map: JsonDict = {}
            current[key] = next_map
            current = next_map
        else:
            current = existing
    current[keys[-1]] = value


def load_env_overrides(env: Mapping[str, str] | None = None) -> JsonDict:
    source = env if env is not None else os.environ
    result: JsonDict = {}
    for key, raw_value in source.items():
        if not key.startswith(ENV_PREFIX):
            continue
        path = key[len(ENV_PREFIX) :]
        if not path:
            continue
        segments = [seg.strip().lower() for seg in path.split("__") if seg.strip()]
        if not segments:
            continue
        _set_nested(result, segments, _coerce_value(raw_value))
    return result
