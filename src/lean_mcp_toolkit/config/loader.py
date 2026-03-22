"""Toolkit config loader with layered override support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..contracts.base import JsonDict
from .env import load_env_overrides
from .models import ToolkitConfig


def _deep_merge(base: JsonDict, override: JsonDict) -> JsonDict:
    merged: JsonDict = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def _load_file_dict(config_path: str | None) -> JsonDict:
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")

    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("json config root must be an object")
        return data

    if suffix in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - optional dependency branch
            raise RuntimeError(
                "yaml config requires PyYAML; install dependency or use json config"
            ) from exc
        data = yaml.safe_load(text)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError("yaml config root must be a mapping")
        return dict(data)

    raise ValueError(f"unsupported config file suffix: {suffix}")


def load_toolkit_config(
    *,
    config_path: str | None = None,
    env: Mapping[str, str] | None = None,
    cli_overrides: JsonDict | None = None,
) -> ToolkitConfig:
    """Load resolved config with precedence: defaults < file < env < cli."""

    resolved: JsonDict = ToolkitConfig().to_dict()

    file_data = _load_file_dict(config_path)
    if file_data:
        resolved = _deep_merge(resolved, file_data)

    env_data = load_env_overrides(env)
    if env_data:
        resolved = _deep_merge(resolved, env_data)

    if cli_overrides:
        resolved = _deep_merge(resolved, cli_overrides)

    return ToolkitConfig.from_dict(resolved)


def apply_path_override(target: JsonDict, path: str, value: Any) -> None:
    segments = [seg.strip() for seg in path.split(".") if seg.strip()]
    if not segments:
        return
    current: JsonDict = target
    for segment in segments[:-1]:
        node = current.get(segment)
        if not isinstance(node, dict):
            new_node: JsonDict = {}
            current[segment] = new_node
            current = new_node
        else:
            current = node
    current[segments[-1]] = value
