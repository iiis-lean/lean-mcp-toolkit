"""Group-plugin base protocol and tool-filter utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from ..config import ToolkitConfig
from ..contracts.base import JsonDict
from ..transport.http import HttpConfig

ToolHandler = Callable[[JsonDict], JsonDict]


@dataclass(slots=True, frozen=True)
class GroupToolSpec:
    group_name: str
    canonical_name: str
    raw_name: str
    api_path: str
    description: str

    def match_tokens(self) -> set[str]:
        tokens = {
            self.canonical_name.strip(),
            self.raw_name.strip(),
            self.api_path.strip(),
            self.api_path.strip().lstrip("/"),
        }
        return {token for token in tokens if token}


class GroupPlugin(Protocol):
    group_name: str

    def create_local_service(self, config: ToolkitConfig) -> Any:
        ...

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig) -> Any:
        ...

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        ...

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        ...

    def register_mcp_tools(
        self,
        mcp: Any,
        *,
        service: Any,
        aliases_by_canonical: Mapping[str, tuple[str, ...]],
        normalize_str_list: Callable[[list[str] | str | None], list[str] | None],
        prune_none: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        ...


def resolve_active_group_names(
    *,
    config: ToolkitConfig,
    available_group_names: tuple[str, ...],
) -> tuple[str, ...]:
    disabled = {name.strip() for name in config.groups.disabled_groups if name.strip()}
    enabled = [name.strip() for name in config.groups.enabled_groups if name.strip()]
    available_set = set(available_group_names)

    ordered: list[str] = []
    seen: set[str] = set()
    for name in enabled:
        if name in seen:
            continue
        seen.add(name)
        if name in disabled:
            continue
        if name not in available_set:
            continue
        ordered.append(name)
    return tuple(ordered)


def resolve_aliases_by_canonical(
    *,
    specs: tuple[GroupToolSpec, ...],
    naming_mode: str,
    include_tools: tuple[str, ...],
    exclude_tools: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    include_set = {item.strip() for item in include_tools if item.strip()}
    exclude_set = {item.strip() for item in exclude_tools if item.strip()}

    aliases_by_canonical: dict[str, tuple[str, ...]] = {}
    for spec in specs:
        tokens = spec.match_tokens()
        if include_set and tokens.isdisjoint(include_set):
            continue
        if exclude_set and not tokens.isdisjoint(exclude_set):
            continue

        aliases = _aliases_for_mode(spec=spec, naming_mode=naming_mode)
        if not aliases:
            continue
        aliases_by_canonical[spec.canonical_name] = aliases
    return aliases_by_canonical


def _aliases_for_mode(*, spec: GroupToolSpec, naming_mode: str) -> tuple[str, ...]:
    if naming_mode == "raw":
        candidates = [spec.raw_name]
    elif naming_mode == "both":
        candidates = [spec.canonical_name, spec.raw_name]
    else:
        candidates = [spec.canonical_name]

    aliases: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        name = item.strip()
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        aliases.append(name)
    return tuple(aliases)


__all__ = [
    "ToolHandler",
    "GroupToolSpec",
    "GroupPlugin",
    "resolve_active_group_names",
    "resolve_aliases_by_canonical",
]
