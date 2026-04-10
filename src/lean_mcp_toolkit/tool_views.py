"""Tool view filtering and metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Mapping

from .config import ToolMetadataOverrideConfig, ToolViewConfig
from .groups.plugin_base import GroupToolSpec

_VIEW_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(slots=True, frozen=True)
class ResolvedToolView:
    name: str
    config: ToolViewConfig
    specs_by_canonical: dict[str, GroupToolSpec]
    aliases_by_canonical: dict[str, tuple[str, ...]]

    def to_summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "tool_count": len(self.specs_by_canonical),
            "config": self.config.to_dict(),
        }


def normalize_view_name(name: str | None, *, default: str = "default") -> str:
    text = (name or default).strip()
    if not text:
        text = default
    if not _VIEW_NAME_RE.fullmatch(text):
        raise ValueError(f"invalid tool view name: {text}")
    return text


def apply_tool_metadata(
    spec: GroupToolSpec,
    metadata: Mapping[str, ToolMetadataOverrideConfig],
) -> GroupToolSpec:
    override = metadata.get(spec.canonical_name) or metadata.get(spec.raw_name)
    if override is None:
        return spec

    if override.replace_tags is not None:
        tags = _normalize_ordered(override.replace_tags)
    else:
        tags = _normalize_ordered(spec.tags)
    if override.add_tags:
        tags = _normalize_ordered((*tags, *override.add_tags))
    if override.remove_tags:
        remove = {item.strip() for item in override.remove_tags if item.strip()}
        tags = tuple(item for item in tags if item not in remove)
    return replace(spec, tags=tags)


def resolve_tool_view(
    *,
    name: str,
    specs: tuple[GroupToolSpec, ...],
    view_config: ToolViewConfig,
    default_tool_naming_mode: str,
) -> ResolvedToolView:
    view_name = normalize_view_name(name)
    include_groups = _norm_set(view_config.include_groups)
    exclude_groups = _norm_set(view_config.exclude_groups)
    include_tools = _norm_set(view_config.include_tools)
    exclude_tools = _norm_set(view_config.exclude_tools)
    include_tags = _norm_set(view_config.include_tags)
    exclude_tags = _norm_set(view_config.exclude_tags)
    naming_mode = view_config.tool_naming_mode or default_tool_naming_mode

    specs_by_canonical: dict[str, GroupToolSpec] = {}
    aliases_by_canonical: dict[str, tuple[str, ...]] = {}
    for spec in specs:
        if include_groups and spec.group_name not in include_groups:
            continue
        if spec.group_name in exclude_groups:
            continue
        tokens = spec.match_tokens()
        if include_tools and tokens.isdisjoint(include_tools):
            continue
        if exclude_tools and not tokens.isdisjoint(exclude_tools):
            continue
        tags = _norm_set(spec.tags)
        if include_tags and tags.isdisjoint(include_tags):
            continue
        if exclude_tags and not tags.isdisjoint(exclude_tags):
            continue
        aliases = _aliases_for_mode(spec=spec, naming_mode=naming_mode)
        if not aliases:
            continue
        specs_by_canonical[spec.canonical_name] = spec
        aliases_by_canonical[spec.canonical_name] = aliases

    return ResolvedToolView(
        name=view_name,
        config=view_config,
        specs_by_canonical=specs_by_canonical,
        aliases_by_canonical=aliases_by_canonical,
    )


def default_view_config_from_groups(
    *,
    include_tools: tuple[str, ...],
    exclude_tools: tuple[str, ...],
    tool_naming_mode: str,
) -> ToolViewConfig:
    return ToolViewConfig(
        include_tools=include_tools,
        exclude_tools=exclude_tools,
        tool_naming_mode=tool_naming_mode if tool_naming_mode in {"raw", "prefixed", "both"} else "prefixed",
    )


def _aliases_for_mode(*, spec: GroupToolSpec, naming_mode: str) -> tuple[str, ...]:
    if naming_mode == "raw":
        candidates = [spec.raw_name]
    elif naming_mode == "both":
        candidates = [spec.canonical_name, spec.raw_name]
    else:
        candidates = [spec.canonical_name]

    aliases: list[str] = []
    seen: set[str] = set()
    for alias in candidates:
        text = alias.strip()
        if text and text not in seen:
            aliases.append(text)
            seen.add(text)
    return tuple(aliases)


def _normalize_ordered(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        ordered.append(text)
        seen.add(text)
    return tuple(ordered)


def _norm_set(values: tuple[str, ...]) -> set[str]:
    return {str(value).strip() for value in values if str(value).strip()}
