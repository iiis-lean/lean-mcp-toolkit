"""Top-level toolkit server wrapper."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
import logging
from typing import Any

from ..backends import BackendContext, BackendKey, build_backend_context
from ..backends.lean.path import resolve_project_root
from ..config import ToolkitConfig, load_toolkit_config
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
from ..groups.plugin_base import GroupToolSpec
from ..groups.plugin_base import resolve_active_group_names
from ..tool_audit import AuditedServiceProxy, ToolkitAuditLogger, audit_view
from ..tool_views import (
    ResolvedToolView,
    apply_tool_metadata,
    default_view_config_from_groups,
    normalize_view_name,
    resolve_tool_view,
)
from .warmup import ToolkitWarmupRunner

_LOG = logging.getLogger(__name__)


@dataclass(slots=True)
class _ToolViewRuntime:
    resolved: ResolvedToolView
    tool_alias_handlers: dict[str, ToolHandler] = field(default_factory=dict)
    api_route_handlers: dict[str, ToolHandler] = field(default_factory=dict)
    specs_by_alias: dict[str, GroupToolSpec] = field(default_factory=dict)
    specs_by_api_path: dict[str, GroupToolSpec] = field(default_factory=dict)


@dataclass(slots=True)
class ToolkitServer:
    """Unified toolkit server object.

    This wrapper keeps service wiring centralized. HTTP/MCP transport startup can
    build on top of this object without changing service logic.
    """

    config: ToolkitConfig
    api_prefix: str = "/api/v1"
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
    _group_services: dict[str, Any] = field(default_factory=dict, repr=False)
    _canonical_handlers: dict[str, ToolHandler] = field(default_factory=dict, repr=False)
    _tool_alias_handlers: dict[str, ToolHandler] = field(default_factory=dict, repr=False)
    _api_route_handlers: dict[str, ToolHandler] = field(default_factory=dict, repr=False)
    _tool_specs_by_canonical: dict[str, GroupToolSpec] = field(default_factory=dict, repr=False)
    _tool_specs_by_alias: dict[str, GroupToolSpec] = field(default_factory=dict, repr=False)
    _tool_specs_by_api_path: dict[str, GroupToolSpec] = field(default_factory=dict, repr=False)
    _aliases_by_group: dict[str, dict[str, tuple[str, ...]]] = field(
        default_factory=dict, repr=False
    )
    _tool_view_runtimes: dict[str, _ToolViewRuntime] = field(default_factory=dict, repr=False)
    _backend_context: BackendContext | None = field(default=None, repr=False)
    _last_warmup_report: dict[str, Any] | None = field(default=None, repr=False)
    _audit_logger: ToolkitAuditLogger | None = field(default=None, repr=False)

    @classmethod
    def from_config(
        cls,
        config: ToolkitConfig,
        *,
        plugins: tuple[GroupPlugin, ...] | None = None,
    ) -> "ToolkitServer":
        server = cls(
            config=config,
            api_prefix=cls._normalize_path(config.server.api_prefix, default="/api/v1"),
        )
        plugin_list = plugins or builtin_group_plugins()
        server._wire_plugins(plugin_list)
        return server

    @classmethod
    def from_config_path(
        cls,
        config_path: str | None = None,
        *,
        plugins: tuple[GroupPlugin, ...] | None = None,
    ) -> "ToolkitServer":
        config = load_toolkit_config(config_path=config_path)
        return cls.from_config(config, plugins=plugins)

    def dispatch_api(
        self,
        route_path: str,
        payload: dict[str, Any],
        *,
        view_name: str | None = None,
    ) -> dict[str, Any]:
        view = self._get_tool_view_runtime(view_name)
        route = route_path.strip()
        if route in view.tool_alias_handlers:
            with audit_view(view.resolved.name):
                return view.tool_alias_handlers[route](payload)

        if route.startswith(self.api_prefix + "/"):
            route = route[len(self.api_prefix) :]
            if not route.startswith("/"):
                route = "/" + route
        if route in view.api_route_handlers:
            with audit_view(view.resolved.name):
                return view.api_route_handlers[route](payload)

        if not route.startswith("/"):
            slash_route = "/" + route
            if slash_route in view.api_route_handlers:
                with audit_view(view.resolved.name):
                    return view.api_route_handlers[slash_route](payload)
        raise KeyError(f"unsupported route/tool: {route_path}")

    def available_tool_aliases(self, *, view_name: str | None = None) -> tuple[str, ...]:
        return tuple(sorted(self._get_tool_view_runtime(view_name).tool_alias_handlers.keys()))

    def available_http_routes(self, *, view_name: str | None = None) -> tuple[str, ...]:
        return tuple(sorted(self._get_tool_view_runtime(view_name).api_route_handlers.keys()))

    def describe_tools(self, *, view_name: str | None = None) -> tuple[dict[str, Any], ...]:
        view = self._get_tool_view_runtime(view_name)
        rows: list[dict[str, Any]] = []
        for canonical_name in sorted(view.resolved.specs_by_canonical.keys()):
            spec = view.resolved.specs_by_canonical[canonical_name]
            aliases = tuple(
                sorted(
                    alias
                    for alias, alias_spec in view.specs_by_alias.items()
                    if alias_spec.canonical_name == canonical_name
                )
            )
            rows.append(spec.to_dict(aliases=aliases))
        return tuple(rows)

    def create_fastapi_app(self):
        """Create FastAPI app with toolkit JSON API routes."""
        try:
            from fastapi import FastAPI
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("fastapi is required to create HTTP app") from exc

        @contextlib.asynccontextmanager
        async def lifespan(app: Any):
            _ = app
            try:
                yield
            finally:
                self.close()

        app = FastAPI(title="lean-mcp-toolkit", lifespan=lifespan)

        @app.get(
            f"{self.api_prefix}/meta/tools",
            summary="List active tools metadata",
            description="Return active tool contracts including params and returns.",
        )
        def _meta_tools():
            return {"tools": list(self.describe_tools())}

        @app.get(
            f"{self.api_prefix}/views/{{view_name}}/meta/tools",
            summary="List active tools metadata for a tool view",
            description="Return active tool contracts for one named tool view.",
        )
        def _view_meta_tools(view_name: str):
            return {"tools": list(self.describe_tools(view_name=view_name))}

        @app.get(
            f"{self.api_prefix}/meta/warmup",
            summary="Get last startup warmup report",
            description="Return startup warmup execution report for backend/tool pre-heating.",
        )
        def _meta_warmup():
            return self._last_warmup_report or {
                "enabled": bool(self.config.warmup.policy.enabled),
                "executed": False,
                "success": True,
                "project_root": None,
                "steps": [],
            }

        @app.get(
            f"{self.api_prefix}/debug/calls/tail",
            summary="Tail toolkit audit calls",
            description="Return recent toolkit call audit summaries.",
        )
        def _debug_calls_tail(
            project_root: str | None = None,
            view: str | None = None,
            limit: int = 20,
        ):
            logger = self._audit_logger
            if logger is None:
                return {"calls": []}
            return {"calls": logger.tail_calls(project_root=project_root, view=view, limit=limit)}

        @app.get(
            f"{self.api_prefix}/debug/calls/{{call_id}}",
            summary="Get toolkit audit call metadata",
            description="Return metadata for a toolkit audit call.",
        )
        def _debug_call_detail(
            call_id: str,
            project_root: str | None = None,
            view: str | None = None,
        ):
            logger = self._audit_logger
            if logger is None:
                return {"meta": None}
            return {"meta": logger.load_call_meta(project_root=project_root, call_id=call_id, view=view)}

        @app.get(
            f"{self.api_prefix}/debug/calls/{{call_id}}/timing",
            summary="Get toolkit audit call timing",
            description="Return timing payload for a toolkit audit call.",
        )
        def _debug_call_timing(
            call_id: str,
            project_root: str | None = None,
            view: str | None = None,
        ):
            logger = self._audit_logger
            if logger is None:
                return {"timing": None}
            return {"timing": logger.load_call_timing(project_root=project_root, call_id=call_id, view=view)}

        @app.post(
            f"{self.api_prefix}/debug/backends/recycle/lsp",
            summary="Recycle LSP backend for one project",
            description="Drop cached Lean LSP client state for the selected project root.",
        )
        def _debug_recycle_lsp(payload: dict[str, Any] | None = None):
            body = payload or {}
            return self.recycle_lsp_backend(project_root=body.get("project_root"))

        @app.post(
            f"{self.api_prefix}/debug/backends/recycle/lean_interact",
            summary="Recycle lean_interact backend for one project",
            description="Drop cached lean_interact runtime state for the selected project root.",
        )
        def _debug_recycle_lean_interact(payload: dict[str, Any] | None = None):
            body = payload or {}
            return self.recycle_lean_interact_backend(project_root=body.get("project_root"))

        for route_path, handler in sorted(self._api_route_handlers.items()):
            endpoint = self._make_fastapi_endpoint(handler=handler, route_path=route_path)
            spec = self._tool_specs_by_api_path.get(route_path)
            app.add_api_route(
                f"{self.api_prefix}{route_path}",
                endpoint=endpoint,
                methods=["POST"],
                name=endpoint.__name__,
                summary=(spec.canonical_name if spec is not None else route_path),
                description=(
                    spec.render_api_description()
                    if spec is not None
                    else "Tool API endpoint."
                ),
                response_description=(
                    "Tool response payload."
                    if spec is None
                    else "See `Returns` section in description."
                ),
            )

        @app.post(
            f"{self.api_prefix}/views/{{view_name}}/{{tool_path:path}}",
            summary="Invoke a tool through one named tool view",
            description="Invoke a tool API endpoint if it is visible in the selected view.",
        )
        def _view_tool_endpoint(view_name: str, tool_path: str, payload: dict[str, Any]):
            return self.dispatch_api("/" + tool_path, payload, view_name=view_name)

        return app

    def create_mcp_server(self):
        """Create FastMCP server and register toolkit tools."""
        try:
            from mcp.server.fastmcp import FastMCP
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("mcp sdk is required to create MCP server") from exc

        mcp = FastMCP(
            name="lean-mcp-toolkit",
            stateless_http=self.config.server.mcp_stateless_http,
            json_response=self.config.server.mcp_json_response,
        )

        self._register_mcp_tools(mcp)
        return mcp

    def _register_mcp_tools(self, mcp: Any) -> None:
        for plugin in self._group_plugins:
            aliases_by_canonical = self._aliases_by_group.get(plugin.group_name, {})
            if not aliases_by_canonical:
                continue
            service = self._group_services.get(plugin.group_name)
            if service is None:
                continue
            plugin.register_mcp_tools(
                mcp,
                service=service,
                aliases_by_canonical=aliases_by_canonical,
                normalize_str_list=self._normalize_str_list,
                prune_none=self._prune_none,
            )

    def create_unified_asgi_app(self):
        """Create Starlette app that serves API and MCP in one process."""
        try:
            from starlette.applications import Starlette
            from starlette.routing import Mount
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("starlette is required to create unified app") from exc

        api_app = self.create_fastapi_app()
        mcp = self.create_mcp_server()

        # Mount MCP app at configured mount path without extra /mcp suffix.
        mcp.settings.streamable_http_path = "/"

        mcp_mount_path = self._normalize_path(self.config.server.mcp_mount_path, default="/mcp")

        @contextlib.asynccontextmanager
        async def lifespan(app: Any):
            _ = app
            try:
                async with mcp.session_manager.run():
                    yield
            finally:
                self.close()

        app = Starlette(
            routes=[
                Mount(mcp_mount_path, app=mcp.streamable_http_app()),
                Mount("/", app=api_app),
            ],
            lifespan=lifespan,
        )
        return app

    def run_http(self, *, host: str | None = None, port: int | None = None) -> None:
        try:
            import uvicorn
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("uvicorn is required to run HTTP server") from exc

        app = self.create_fastapi_app()
        try:
            uvicorn.run(
                app,
                host=host or self.config.server.host,
                port=port or self.config.server.port,
                log_level=self.config.server.log_level,
            )
        finally:
            self.close()

    def run_mcp(self) -> None:
        mcp = self.create_mcp_server()
        transport = self.config.server.mcp_transport

        if transport == "stdio":
            mcp.run(transport="stdio")
            return

        if transport == "sse":
            mcp.run(
                transport="sse",
                host=self.config.server.host,
                port=self.config.server.port,
            )
            return

        if transport == "streamable-http":
            mcp.run(
                transport="streamable-http",
                host=self.config.server.host,
                port=self.config.server.port,
                streamable_http_path=self._normalize_path(
                    self.config.server.mcp_streamable_http_path,
                    default="/mcp",
                ),
                json_response=self.config.server.mcp_json_response,
                stateless_http=self.config.server.mcp_stateless_http,
            )
            return

        raise ValueError(f"unsupported mcp transport: {transport}")

    def run_unified(self, *, host: str | None = None, port: int | None = None) -> None:
        try:
            import uvicorn
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("uvicorn is required to run unified server") from exc

        app = self.create_unified_asgi_app()
        try:
            uvicorn.run(
                app,
                host=host or self.config.server.host,
                port=port or self.config.server.port,
                log_level=self.config.server.log_level,
            )
        finally:
            self.close()

    def close(self) -> None:
        self._close_value(self._backend_context)
        self._backend_context = None

    def recycle_lsp_backend(self, *, project_root: str | None = None) -> dict[str, Any]:
        resolved_root = self._resolve_backend_project_root(project_root)
        manager = self._get_backend(BackendKey.LSP_CLIENT_MANAGER)
        if manager is None:
            return {
                "ok": False,
                "backend": "lsp",
                "project_root": resolved_root,
                "message": "lsp backend is not initialized",
            }
        recycle = getattr(manager, "recycle_client", None)
        if not callable(recycle):
            return {
                "ok": False,
                "backend": "lsp",
                "project_root": resolved_root,
                "message": "lsp backend does not support recycle_client",
            }
        recycle(resolve_project_root(resolved_root, allow_cwd_fallback=False))
        return {
            "ok": True,
            "backend": "lsp",
            "project_root": resolved_root,
            "message": "recycled lsp backend for project",
        }

    def recycle_lean_interact_backend(self, *, project_root: str | None = None) -> dict[str, Any]:
        resolved_root = self._resolve_backend_project_root(project_root)
        backend_map = self._get_backend(BackendKey.DECLARATIONS_BACKENDS)
        if not isinstance(backend_map, dict):
            return {
                "ok": False,
                "backend": "lean_interact",
                "project_root": resolved_root,
                "message": "declarations backends are not initialized",
            }
        lean_interact_backend = backend_map.get("lean_interact")
        runtime_manager = getattr(lean_interact_backend, "runtime_manager", None)
        recycle = getattr(runtime_manager, "recycle_runtime", None)
        if not callable(recycle):
            return {
                "ok": False,
                "backend": "lean_interact",
                "project_root": resolved_root,
                "message": "lean_interact backend does not support recycle_runtime",
            }
        recycle(resolve_project_root(resolved_root, allow_cwd_fallback=False))
        return {
            "ok": True,
            "backend": "lean_interact",
            "project_root": resolved_root,
            "message": "recycled lean_interact backend for project",
        }

    def run(self) -> None:
        self.run_startup_warmup()
        mode = self.config.server.mode
        if mode == "http":
            self.run_http()
            return
        if mode == "mcp":
            self.run_mcp()
            return
        if mode == "unified":
            self.run_unified()
            return
        raise ValueError(f"unsupported server mode: {mode}")

    def _close_value(self, value: Any) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            for item in value.values():
                self._close_value(item)
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                self._close_value(item)
            return
        if isinstance(value, BackendContext):
            for key in value.keys():
                self._close_value(value.get(key))
            return
        close = getattr(value, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    def _get_backend(self, key: str) -> Any:
        if self._backend_context is None:
            return None
        return self._backend_context.get(key)

    def _resolve_backend_project_root(self, project_root: str | None) -> str:
        resolved = resolve_project_root(
            project_root,
            default_project_root=self.config.server.default_project_root,
            allow_cwd_fallback=True,
        )
        return str(resolved.resolve())

    def run_startup_warmup(self) -> dict[str, Any] | None:
        policy = self.config.warmup.policy
        if not policy.enabled or not policy.run_on_startup:
            return None

        runner = ToolkitWarmupRunner(
            config=self.config,
            diagnostics=self.diagnostics,
            declarations=self.declarations,
            search_core=self.search_core,
        )
        report = runner.run()
        payload = report.to_dict()
        self._last_warmup_report = payload

        if report.success:
            _LOG.info("startup warmup succeeded")
            return payload

        message = "startup warmup failed"
        if policy.continue_on_error:
            _LOG.warning("%s (continue_on_error=true)", message)
            return payload
        raise RuntimeError(message)

    def _wire_plugins(self, plugins: tuple[GroupPlugin, ...]) -> None:
        plugin_by_name: dict[str, GroupPlugin] = {}
        for plugin in plugins:
            if plugin.group_name not in plugin_by_name:
                plugin_by_name[plugin.group_name] = plugin

        active_group_names = resolve_active_group_names(
            config=self.config,
            available_group_names=tuple(plugin_by_name.keys()),
        )
        self._group_plugins = tuple(plugin_by_name[name] for name in active_group_names)
        self._audit_logger = ToolkitAuditLogger(self.config)
        required_backend_keys: list[str] = []
        for plugin in self._group_plugins:
            required_backend_keys.extend(plugin.backend_dependencies())
        self._backend_context = build_backend_context(
            config=self.config,
            required_backend_keys=tuple(required_backend_keys),
        )

        for plugin in self._group_plugins:
            raw_service = plugin.create_local_service(
                self.config,
                backends=self._backend_context,
            )
            service = AuditedServiceProxy(
                service=raw_service,
                group_name=plugin.group_name,
                logger=self._audit_logger,
                method_aliases=self._default_method_aliases_for_group(plugin.group_name),
            )
            self._group_services[plugin.group_name] = service
            if plugin.group_name == "build_base":
                self.build_base = service
            if plugin.group_name == "diagnostics":
                self.diagnostics = service
            if plugin.group_name == "declarations":
                self.declarations = service
            if plugin.group_name == "lsp_core":
                self.lsp_core = service
            if plugin.group_name == "lsp_assist":
                self.lsp_assist = service
            if plugin.group_name == "lsp_heavy":
                self.lsp_heavy = service
            if plugin.group_name == "search_alt":
                self.search_alt = service
            if plugin.group_name == "search_core":
                self.search_core = service
            if plugin.group_name == "mathlib_nav":
                self.mathlib_nav = service
            if plugin.group_name == "search_nav":
                self.search_nav = service
            if plugin.group_name == "proof_search_alt":
                self.proof_search_alt = service

            specs = plugin.tool_specs()
            spec_by_canonical = {
                spec.canonical_name: apply_tool_metadata(spec, self.config.tool_metadata)
                for spec in specs
            }
            handler_by_canonical = dict(plugin.tool_handlers(service))

            for canonical_name, spec in spec_by_canonical.items():
                handler = handler_by_canonical.get(canonical_name)
                if handler is None:
                    raise KeyError(
                        f"missing handler for canonical tool `{canonical_name}` in group `{plugin.group_name}`"
                    )
                self._register_canonical_handler(canonical_name, handler, spec=spec)

        self._build_tool_views()

    def _register_canonical_handler(
        self,
        canonical_name: str,
        handler: ToolHandler,
        *,
        spec: GroupToolSpec,
    ) -> None:
        existing = self._canonical_handlers.get(canonical_name)
        if existing is not None and existing is not handler:
            raise ValueError(f"duplicate canonical handler: {canonical_name}")
        self._canonical_handlers[canonical_name] = handler
        self._tool_specs_by_canonical[canonical_name] = spec

    def _build_tool_views(self) -> None:
        self._tool_view_runtimes.clear()
        self._aliases_by_group.clear()
        specs = tuple(self._tool_specs_by_canonical.values())
        default_config = default_view_config_from_groups(
            include_tools=self.config.groups.include_tools,
            exclude_tools=self.config.groups.exclude_tools,
            tool_naming_mode=self.config.groups.tool_naming_mode,
        )
        configs = {"default": default_config, **dict(self.config.tool_views)}
        for view_name, view_config in configs.items():
            resolved = resolve_tool_view(
                name=view_name,
                specs=specs,
                view_config=view_config,
                default_tool_naming_mode=self.config.groups.tool_naming_mode,
            )
            runtime = self._build_tool_view_runtime(resolved)
            self._tool_view_runtimes[resolved.name] = runtime

        default_runtime = self._get_tool_view_runtime("default")
        self._tool_alias_handlers = dict(default_runtime.tool_alias_handlers)
        self._api_route_handlers = dict(default_runtime.api_route_handlers)
        self._tool_specs_by_alias = dict(default_runtime.specs_by_alias)
        self._tool_specs_by_api_path = dict(default_runtime.specs_by_api_path)

    def _build_tool_view_runtime(self, resolved: ResolvedToolView) -> _ToolViewRuntime:
        runtime = _ToolViewRuntime(resolved=resolved)
        aliases_by_group: dict[str, dict[str, tuple[str, ...]]] = {}
        for canonical_name, aliases in resolved.aliases_by_canonical.items():
            spec = resolved.specs_by_canonical[canonical_name]
            handler = self._canonical_handlers.get(canonical_name)
            if handler is None:
                raise KeyError(f"missing handler for canonical tool `{canonical_name}`")
            existing_route = runtime.api_route_handlers.get(spec.api_path)
            if existing_route is not None and existing_route is not handler:
                raise ValueError(f"http route collision in view `{resolved.name}`: {spec.api_path}")
            runtime.api_route_handlers[spec.api_path] = handler
            runtime.specs_by_api_path[spec.api_path] = spec
            for alias in aliases:
                existing = runtime.tool_alias_handlers.get(alias)
                if existing is not None and existing is not handler:
                    raise ValueError(f"tool alias collision in view `{resolved.name}`: {alias}")
                runtime.tool_alias_handlers[alias] = handler
                runtime.specs_by_alias[alias] = spec
            aliases_by_group.setdefault(spec.group_name, {})[canonical_name] = aliases
        if resolved.name == "default":
            self._aliases_by_group = aliases_by_group
        return runtime

    def _get_tool_view_runtime(self, view_name: str | None = None) -> _ToolViewRuntime:
        normalized = normalize_view_name(view_name)
        runtime = self._tool_view_runtimes.get(normalized)
        if runtime is None:
            raise KeyError(f"unknown tool view: {normalized}")
        return runtime

    def _register_alias_handler(
        self,
        alias: str,
        handler: ToolHandler,
        *,
        spec: GroupToolSpec,
    ) -> None:
        existing = self._tool_alias_handlers.get(alias)
        if existing is not None and existing is not handler:
            raise ValueError(f"tool alias collision: {alias}")
        self._tool_alias_handlers[alias] = handler
        self._tool_specs_by_alias[alias] = spec

    def _register_api_route_handler(
        self,
        route_path: str,
        handler: ToolHandler,
        *,
        spec: GroupToolSpec,
    ) -> None:
        existing = self._api_route_handlers.get(route_path)
        if existing is not None and existing is not handler:
            raise ValueError(f"http route collision: {route_path}")
        self._api_route_handlers[route_path] = handler
        self._tool_specs_by_api_path[route_path] = spec

    @staticmethod
    def _make_fastapi_endpoint(*, handler: ToolHandler, route_path: str):
        from fastapi.responses import JSONResponse

        def _endpoint(payload: dict[str, Any]):
            with audit_view("default"):
                return JSONResponse(handler(payload))

        endpoint_name = "tool_" + route_path.strip("/").replace("/", "_").replace(".", "_")
        _endpoint.__name__ = endpoint_name or "tool_root"
        return _endpoint

    @staticmethod
    def _default_method_aliases_for_group(group_name: str) -> dict[str, str]:
        if group_name == "build_base":
            return {"run_workspace": "build.workspace"}
        if group_name == "diagnostics":
            return {
                "run_build": "diagnostics.build",
                "run_file": "diagnostics.file",
                "run_lint": "diagnostics.lint",
                "run_lint_no_sorry": "diagnostics.lint.no_sorry",
                "run_lint_axiom_audit": "diagnostics.lint.axiom_audit",
            }
        if group_name == "declarations":
            return {
                "extract": "declarations.extract",
                "locate": "declarations.locate",
            }
        return {}

    @staticmethod
    def _normalize_path(value: str | None, *, default: str) -> str:
        text = (value or default).strip()
        if not text:
            text = default
        if not text.startswith("/"):
            text = "/" + text
        if len(text) > 1 and text.endswith("/"):
            text = text[:-1]
        return text

    @staticmethod
    def _normalize_str_list(value: list[str] | str | None) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            return [value]
        return [str(item) for item in value]

    @staticmethod
    def _prune_none(payload: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in payload.items() if v is not None}
