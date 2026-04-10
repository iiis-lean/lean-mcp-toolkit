"""Tool view filtering and metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import re
import threading
from typing import Mapping
import uuid

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


@dataclass(slots=True, frozen=True)
class ToolViewLease:
    lease_id: str
    view: str
    owner: str | None
    reason: str | None
    client: str | None
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "lease_id": self.lease_id,
            "view": self.view,
            "owner": self.owner,
            "reason": self.reason,
            "client": self.client,
            "created_at": self.created_at,
        }


class ToolViewLeaseManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._leases_by_view: dict[str, dict[str, ToolViewLease]] = {}

    def acquire(
        self,
        *,
        view: str,
        owner: str | None = None,
        reason: str | None = None,
        client: str | None = None,
    ) -> dict[str, object]:
        view_name = normalize_view_name(view)
        lease = ToolViewLease(
            lease_id=f"tvlease_{uuid.uuid4().hex}",
            view=view_name,
            owner=_clean_opt(owner),
            reason=_clean_opt(reason),
            client=_clean_opt(client),
            created_at=_utc_now_iso(),
        )
        with self._lock:
            leases = self._leases_by_view.setdefault(view_name, {})
            leases[lease.lease_id] = lease
            active_count = len(leases)
        return {
            "ok": True,
            "view": view_name,
            "lease_id": lease.lease_id,
            "active_count": active_count,
        }

    def release(self, *, view: str, lease_id: str | None) -> dict[str, object]:
        view_name = normalize_view_name(view)
        text = (lease_id or "").strip()
        with self._lock:
            leases = self._leases_by_view.setdefault(view_name, {})
            removed = leases.pop(text, None)
            active_count = len(leases)
        return {
            "ok": removed is not None,
            "view": view_name,
            "lease_id": text or None,
            "active_count": active_count,
        }

    def release_all(self, *, view: str) -> dict[str, object]:
        view_name = normalize_view_name(view)
        with self._lock:
            leases = self._leases_by_view.setdefault(view_name, {})
            released = len(leases)
            leases.clear()
        return {
            "ok": True,
            "view": view_name,
            "released_count": released,
            "active_count": 0,
        }

    def usage(self, *, view: str) -> dict[str, object]:
        view_name = normalize_view_name(view)
        with self._lock:
            leases = tuple(self._leases_by_view.setdefault(view_name, {}).values())
        return {
            "view": view_name,
            "active_count": len(leases),
            "leases": [lease.to_dict() for lease in leases],
        }

    def active_count(self, *, view: str) -> int:
        view_name = normalize_view_name(view)
        with self._lock:
            return len(self._leases_by_view.setdefault(view_name, {}))


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


def _clean_opt(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
