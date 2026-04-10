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


def _load_tool_view_file(path: Path) -> JsonDict:
    if not path.exists():
        raise FileNotFoundError(f"tool view file not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in {".yml", ".yaml"}:
        raise ValueError(f"unsupported tool view file suffix: {suffix}")
    try:
        import yaml  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - optional dependency branch
        raise RuntimeError(
            "yaml tool view config requires PyYAML; install dependency or use inline config"
        ) from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("tool view yaml root must be a mapping")
    if isinstance(data.get("tool_views"), dict):
        return dict(data["tool_views"])
    return dict(data)


def _load_external_tool_views(config: JsonDict, *, config_path: str | None) -> JsonDict:
    files_raw = config.get("tool_view_files")
    if files_raw is None:
        return config
    files: list[str]
    if isinstance(files_raw, str):
        files = [item.strip() for item in files_raw.split(",") if item.strip()]
    elif isinstance(files_raw, (list, tuple)):
        files = [str(item).strip() for item in files_raw if str(item).strip()]
    else:
        files = [str(files_raw).strip()] if str(files_raw).strip() else []
    if not files:
        return config

    base_dir = Path(config_path).expanduser().resolve().parent if config_path else Path.cwd()
    merged_views: JsonDict = dict(config.get("tool_views") or {})
    for raw in files:
        view_path = Path(raw).expanduser()
        if not view_path.is_absolute():
            view_path = (base_dir / view_path).resolve()
        file_views = _load_tool_view_file(view_path)
        merged_views = _deep_merge(merged_views, file_views)
    resolved = dict(config)
    resolved["tool_views"] = merged_views
    return resolved


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

    resolved = _load_external_tool_views(resolved, config_path=config_path)

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
