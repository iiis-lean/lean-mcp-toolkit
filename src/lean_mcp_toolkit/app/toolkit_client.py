"""Top-level HTTP toolkit client wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..config import ToolkitConfig
from ..core.services import (
    BuildBaseService,
    DeclarationsService,
    DiagnosticsService,
    LspAssistService,
    LspHeavyService,
    LspCoreService,
    MathlibNavService,
    ProofSearchAltService,
    SearchAltService,
    SearchCoreService,
    SearchNavService,
)
from ..groups import GroupPlugin, ToolHandler, builtin_group_plugins
from ..groups.plugin_base import resolve_active_group_names, resolve_aliases_by_canonical
from ..transport.http import HttpConfig


@dataclass(slots=True)
class ToolkitHttpClient:
    """HTTP client wrapper for all exposed toolkit groups."""

    config: ToolkitConfig = field(default_factory=ToolkitConfig)
    http_config: HttpConfig | None = None
    build_base: BuildBaseService | None = None
    diagnostics: DiagnosticsService | None = None
    declarations: DeclarationsService | None = None
    lsp_core: LspCoreService | None = None
    lsp_assist: LspAssistService | None = None
    lsp_heavy: LspHeavyService | None = None
    search_alt: SearchAltService | None = None
    search_core: SearchCoreService | None = None
    mathlib_nav: MathlibNavService | None = None
    search_nav: SearchNavService | None = None
    proof_search_alt: ProofSearchAltService | None = None
    _group_plugins: tuple[GroupPlugin, ...] = field(default_factory=tuple, repr=False)
    _group_clients: dict[str, Any] = field(default_factory=dict, repr=False)
    _canonical_handlers: dict[str, ToolHandler] = field(default_factory=dict, repr=False)
    _tool_alias_handlers: dict[str, ToolHandler] = field(default_factory=dict, repr=False)
    _api_route_handlers: dict[str, ToolHandler] = field(default_factory=dict, repr=False)
    _aliases_by_group: dict[str, dict[str, tuple[str, ...]]] = field(
        default_factory=dict, repr=False
    )

    @classmethod
    def from_http_config(
        cls,
        http_config: HttpConfig,
        *,
        config: ToolkitConfig | None = None,
        plugins: tuple[GroupPlugin, ...] | None = None,
    ) -> "ToolkitHttpClient":
        resolved = config or ToolkitConfig()
        client = cls(config=resolved, http_config=http_config)
        client._wire_plugins(plugins or builtin_group_plugins())
        return client

    def dispatch_api(self, route_path: str, payload: dict) -> dict:
        route = route_path.strip()
        if route in self._tool_alias_handlers:
            return self._tool_alias_handlers[route](payload)

        api_prefix = self._normalized_api_prefix()
        if api_prefix and route.startswith(api_prefix + "/"):
            route = route[len(api_prefix) :]
            if not route.startswith("/"):
                route = "/" + route
        if route in self._api_route_handlers:
            return self._api_route_handlers[route](payload)

        if not route.startswith("/"):
            slash_route = "/" + route
            if slash_route in self._api_route_handlers:
                return self._api_route_handlers[slash_route](payload)
        raise KeyError(f"unsupported route/tool: {route_path}")

    def available_tool_aliases(self) -> tuple[str, ...]:
        return tuple(sorted(self._tool_alias_handlers.keys()))

    def available_http_routes(self) -> tuple[str, ...]:
        return tuple(sorted(self._api_route_handlers.keys()))

    def _wire_plugins(self, plugins: tuple[GroupPlugin, ...]) -> None:
        if self.http_config is None:
            raise ValueError("http_config is required for plugin-based ToolkitHttpClient")

        plugin_by_name: dict[str, GroupPlugin] = {}
        for plugin in plugins:
            if plugin.group_name not in plugin_by_name:
                plugin_by_name[plugin.group_name] = plugin

        active_group_names = resolve_active_group_names(
            config=self.config,
            available_group_names=tuple(plugin_by_name.keys()),
        )
        self._group_plugins = tuple(plugin_by_name[name] for name in active_group_names)

        for plugin in self._group_plugins:
            group_client = plugin.create_http_client(config=self.config, http_config=self.http_config)
            self._group_clients[plugin.group_name] = group_client
            if plugin.group_name == "build_base":
                self.build_base = group_client
            if plugin.group_name == "diagnostics":
                self.diagnostics = group_client
            if plugin.group_name == "declarations":
                self.declarations = group_client
            if plugin.group_name == "lsp_core":
                self.lsp_core = group_client
            if plugin.group_name == "lsp_assist":
                self.lsp_assist = group_client
            if plugin.group_name == "lsp_heavy":
                self.lsp_heavy = group_client
            if plugin.group_name == "search_alt":
                self.search_alt = group_client
            if plugin.group_name == "search_core":
                self.search_core = group_client
            if plugin.group_name == "mathlib_nav":
                self.mathlib_nav = group_client
            if plugin.group_name == "search_nav":
                self.search_nav = group_client
            if plugin.group_name == "proof_search_alt":
                self.proof_search_alt = group_client

            specs = plugin.tool_specs()
            spec_by_canonical = {spec.canonical_name: spec for spec in specs}
            handler_by_canonical = dict(plugin.tool_handlers(group_client))
            aliases_by_canonical = resolve_aliases_by_canonical(
                specs=specs,
                naming_mode=self.config.groups.tool_naming_mode,
                include_tools=self.config.groups.include_tools,
                exclude_tools=self.config.groups.exclude_tools,
            )
            self._aliases_by_group[plugin.group_name] = aliases_by_canonical

            for canonical_name, aliases in aliases_by_canonical.items():
                handler = handler_by_canonical.get(canonical_name)
                if handler is None:
                    raise KeyError(
                        f"missing handler for canonical tool `{canonical_name}` in group `{plugin.group_name}`"
                    )
                spec = spec_by_canonical.get(canonical_name)
                if spec is None:
                    raise KeyError(
                        f"missing tool spec for canonical tool `{canonical_name}` in group `{plugin.group_name}`"
                    )

                self._register_canonical_handler(canonical_name, handler)
                self._register_api_route_handler(spec.api_path, handler)
                for alias in aliases:
                    self._register_alias_handler(alias, handler)

    def _register_canonical_handler(self, canonical_name: str, handler: ToolHandler) -> None:
        existing = self._canonical_handlers.get(canonical_name)
        if existing is not None and existing is not handler:
            raise ValueError(f"duplicate canonical handler: {canonical_name}")
        self._canonical_handlers[canonical_name] = handler

    def _register_alias_handler(self, alias: str, handler: ToolHandler) -> None:
        existing = self._tool_alias_handlers.get(alias)
        if existing is not None and existing is not handler:
            raise ValueError(f"tool alias collision: {alias}")
        self._tool_alias_handlers[alias] = handler

    def _register_api_route_handler(self, route_path: str, handler: ToolHandler) -> None:
        existing = self._api_route_handlers.get(route_path)
        if existing is not None and existing is not handler:
            raise ValueError(f"http route collision: {route_path}")
        self._api_route_handlers[route_path] = handler

    def _normalized_api_prefix(self) -> str:
        prefix = (self.http_config.api_prefix if self.http_config is not None else "").strip()
        if not prefix:
            return ""
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        if len(prefix) > 1 and prefix.endswith("/"):
            prefix = prefix[:-1]
        return prefix
