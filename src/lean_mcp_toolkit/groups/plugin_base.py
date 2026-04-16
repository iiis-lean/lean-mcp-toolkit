"""Group-plugin base protocol and tool-filter utilities."""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass, replace
from weakref import WeakKeyDictionary
from typing import Any, Callable, Mapping, Protocol

from ..backends.context import BackendContext
from ..config import ToolkitConfig
from ..contracts.base import JsonDict
from ..contracts.schema_utils import build_output_schema
from ..transport.http import HttpConfig

ToolHandler = Callable[[JsonDict], Any]

DEFAULT_MCP_BLOCKING_TOOL_MAX_CONCURRENCY = 8
_MCP_BLOCKING_TOOL_SEMAPHORES: WeakKeyDictionary[
    asyncio.AbstractEventLoop,
    dict[int, asyncio.Semaphore],
] = WeakKeyDictionary()


def _get_mcp_blocking_tool_semaphore(limit: int) -> asyncio.Semaphore:
    normalized = max(int(limit), 1)
    loop = asyncio.get_running_loop()
    per_loop = _MCP_BLOCKING_TOOL_SEMAPHORES.setdefault(loop, {})
    sem = per_loop.get(normalized)
    if sem is None:
        sem = asyncio.Semaphore(normalized)
        per_loop[normalized] = sem
    return sem


async def run_sync_mcp_handler(
    handler: Callable[[JsonDict], Any],
    payload: JsonDict,
    *,
    max_concurrency: int = DEFAULT_MCP_BLOCKING_TOOL_MAX_CONCURRENCY,
) -> Any:
    """Run a synchronous MCP handler off the event loop."""
    sem = _get_mcp_blocking_tool_semaphore(max_concurrency)
    async with sem:
        return await asyncio.to_thread(handler, payload)


async def run_sync_mcp_service_handler(
    handler: Callable[[Any, JsonDict], Any],
    service: Any,
    payload: JsonDict,
    *,
    max_concurrency: int = DEFAULT_MCP_BLOCKING_TOOL_MAX_CONCURRENCY,
) -> Any:
    """Run a synchronous service-bound MCP handler off the event loop."""
    sem = _get_mcp_blocking_tool_semaphore(max_concurrency)
    async with sem:
        return await asyncio.to_thread(handler, service, payload)


@dataclass(slots=True, frozen=True)
class ToolParamSpec:
    name: str
    type_hint: str
    description: str
    required: bool = False
    default_value: str | None = None

    def to_doc_line(self) -> str:
        required_text = "required" if self.required else "optional"
        line = (
            f"- `{self.name}` (`{self.type_hint}`, {required_text}): "
            f"{self.description.strip()}"
        )
        if self.default_value is not None:
            line += f" Default: `{self.default_value}`."
        return line

    def to_dict(self) -> JsonDict:
        return {
            "name": self.name,
            "type": self.type_hint,
            "description": self.description,
            "required": self.required,
            "default": self.default_value,
        }


@dataclass(slots=True, frozen=True)
class ToolReturnSpec:
    field_path: str
    type_hint: str
    description: str
    children: tuple["ToolReturnSpec", ...] = tuple()

    def to_doc_lines(self, *, level: int = 0) -> list[str]:
        indent = "  " * max(0, level)
        lines = [
            (
                f"{indent}- `{self.field_path}` (`{self.type_hint}`): "
                f"{self.description.strip()}"
            )
        ]
        for child in self.children:
            lines.extend(child.to_doc_lines(level=level + 1))
        return lines

    def to_dict(self) -> JsonDict:
        return {
            "field_path": self.field_path,
            "type": self.type_hint,
            "description": self.description,
            "children": [item.to_dict() for item in self.children],
        }


@dataclass(slots=True, frozen=True)
class GroupToolSpec:
    group_name: str
    canonical_name: str
    raw_name: str
    api_path: str
    description: str
    params: tuple[ToolParamSpec, ...] = tuple()
    returns: tuple[ToolReturnSpec, ...] = tuple()
    tags: tuple[str, ...] = tuple()
    output_schema: JsonDict | None = None

    def match_tokens(self) -> set[str]:
        tokens = {
            self.canonical_name.strip(),
            self.raw_name.strip(),
            self.api_path.strip(),
            self.api_path.strip().lstrip("/"),
        }
        return {token for token in tokens if token}

    def render_mcp_description(self) -> str:
        return self._render_description(
            include_endpoint=False,
            include_params=False,
            include_returns=True,
        )

    def render_api_description(self) -> str:
        return self._render_description(
            include_endpoint=True,
            include_params=False,
            include_returns=True,
        )

    def to_dict(self, *, aliases: tuple[str, ...] = tuple()) -> JsonDict:
        return {
            "group_name": self.group_name,
            "canonical_name": self.canonical_name,
            "raw_name": self.raw_name,
            "aliases": list(aliases),
            "api_path": self.api_path,
            "description": self.description,
            "tags": list(self.tags),
            "params": [item.to_dict() for item in self.params],
            "returns": [item.to_dict() for item in self.returns],
            "output_schema": copy.deepcopy(self.output_schema)
            if self.output_schema is not None
            else None,
            "mcp_description": self.render_mcp_description(),
            "api_description": self.render_api_description(),
        }

    def _render_description(
        self,
        *,
        include_endpoint: bool,
        include_params: bool,
        include_returns: bool,
    ) -> str:
        parts: list[str] = [self.description.strip()]
        if include_endpoint:
            parts.extend(
                [
                    "",
                    f"Canonical tool: `{self.canonical_name}`",
                    f"API path: `{self.api_path}`",
                ]
            )
        if include_params and self.params:
            parts.append("")
            parts.append("Parameters:")
            parts.extend(param.to_doc_line() for param in self.params)
        if include_returns and self.returns:
            parts.append("")
            parts.append("Returns:")
            for ret in self.returns:
                parts.extend(ret.to_doc_lines())
        return "\n".join(parts).strip()


class GroupPlugin(Protocol):
    group_name: str

    def backend_dependencies(self) -> tuple[str, ...]:
        ...

    def create_local_service(
        self,
        config: ToolkitConfig,
        *,
        backends: BackendContext | None = None,
    ) -> Any:
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


def with_output_schema(spec: GroupToolSpec, response_type: Any) -> GroupToolSpec:
    return replace(spec, output_schema=build_output_schema(response_type))


def with_output_schemas(
    specs: tuple[GroupToolSpec, ...],
    response_types: Mapping[str, Any],
) -> tuple[GroupToolSpec, ...]:
    return tuple(
        with_output_schema(spec, response_types[spec.canonical_name])
        if spec.canonical_name in response_types
        else spec
        for spec in specs
    )


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
    "ToolParamSpec",
    "ToolReturnSpec",
    "GroupToolSpec",
    "GroupPlugin",
    "resolve_active_group_names",
    "resolve_aliases_by_canonical",
]
