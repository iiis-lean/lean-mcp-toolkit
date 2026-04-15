"""Top-level toolkit server wrapper."""

from __future__ import annotations

import contextlib
import copy
from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any

from ..backends import BackendContext, BackendKey, build_backend_context
from ..backends.lean.path import resolve_project_root
from ..config import ToolkitConfig, ToolViewConfig, load_toolkit_config
from ..contracts.base import serialize_payload
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
    ToolViewLeaseManager,
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
    aliases_by_group: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)
    output_schema_by_canonical: dict[str, Any | None] = field(default_factory=dict)


@dataclass(slots=True)
class _ViewBoundServiceProxy:
    service: Any
    view_name: str

    def __getattr__(self, name: str) -> Any:
        target = getattr(self.service, name)
        if not callable(target) or name == "close" or name.startswith("_"):
            return target

        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            with audit_view(self.view_name):
                return target(*args, **kwargs)

        return _wrapped


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
    _tool_view_configs: dict[str, ToolViewConfig] = field(default_factory=dict, repr=False)
    _tool_view_leases: ToolViewLeaseManager = field(default_factory=ToolViewLeaseManager, repr=False)
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
    ) -> Any:
        view = self._get_tool_view_runtime(view_name)
        route = route_path.strip()
        if route in view.tool_alias_handlers:
            with audit_view(view.resolved.name):
                return serialize_payload(view.tool_alias_handlers[route](payload))

        if route.startswith(self.api_prefix + "/"):
            route = route[len(self.api_prefix) :]
            if not route.startswith("/"):
                route = "/" + route
        if route in view.api_route_handlers:
            with audit_view(view.resolved.name):
                return serialize_payload(view.api_route_handlers[route](payload))

        if not route.startswith("/"):
            slash_route = "/" + route
            if slash_route in view.api_route_handlers:
                with audit_view(view.resolved.name):
                    return serialize_payload(view.api_route_handlers[slash_route](payload))
        raise KeyError(f"unsupported route/tool: {route_path}")

    def available_tool_aliases(self, *, view_name: str | None = None) -> tuple[str, ...]:
        return tuple(sorted(self._get_tool_view_runtime(view_name).tool_alias_handlers.keys()))

    def available_http_routes(self, *, view_name: str | None = None) -> tuple[str, ...]:
        return tuple(sorted(self._get_tool_view_runtime(view_name).api_route_handlers.keys()))

    def describe_tools(self, *, view_name: str | None = None) -> tuple[dict[str, Any], ...]:
        view = self._get_tool_view_runtime(view_name)
        output_schemas = self._get_tool_output_schemas(view.resolved.name)
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
            row = spec.to_dict(aliases=aliases)
            schema = output_schemas.get(canonical_name)
            row["output_schema"] = copy.deepcopy(schema) if schema is not None else None
            rows.append(row)
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

        @app.get(
            f"{self.api_prefix}/debug/tool-views",
            summary="List runtime tool views",
            description="Return configured tool view summaries.",
        )
        def _debug_tool_views():
            return {"views": self.list_tool_views()}

        @app.get(
            f"{self.api_prefix}/debug/tool-views/{{view_name}}",
            summary="Get runtime tool view",
            description="Return one tool view summary and usage state.",
        )
        def _debug_tool_view(view_name: str):
            return self.get_tool_view(view_name)

        @app.put(
            f"{self.api_prefix}/debug/tool-views/{{view_name}}",
            summary="Create or update a runtime tool view",
            description="Create or update a tool view when it has no active leases.",
        )
        def _debug_put_tool_view(view_name: str, payload: dict[str, Any] | None = None):
            from fastapi.responses import JSONResponse

            result = self.upsert_tool_view(view_name, payload or {})
            return JSONResponse(result, status_code=409 if not result.get("ok", False) else 200)

        @app.delete(
            f"{self.api_prefix}/debug/tool-views/{{view_name}}",
            summary="Delete a runtime tool view",
            description="Delete a non-default tool view when it has no active leases.",
        )
        def _debug_delete_tool_view(view_name: str):
            from fastapi.responses import JSONResponse

            result = self.delete_tool_view(view_name)
            return JSONResponse(result, status_code=409 if not result.get("ok", False) else 200)

        @app.post(
            f"{self.api_prefix}/debug/tool-views/save",
            summary="Save runtime tool views to YAML",
            description="Persist non-default runtime tool views to a YAML file.",
        )
        def _debug_save_tool_views(payload: dict[str, Any] | None = None):
            body = payload or {}
            return self.save_tool_views(str(body.get("path") or "configs/tool_views.yaml"))

        @app.post(
            f"{self.api_prefix}/debug/tool-views/load",
            summary="Load runtime tool views from YAML",
            description="Load runtime tool views from a YAML file.",
        )
        def _debug_load_tool_views(payload: dict[str, Any] | None = None):
            body = payload or {}
            return self.load_tool_views(
                str(body.get("path") or "configs/tool_views.yaml"),
                replace=bool(body.get("replace", False)),
            )

        @app.post(
            f"{self.api_prefix}/debug/tool-views/{{view_name}}/acquire",
            summary="Acquire a tool view lease",
            description="Mark a tool view as in use by an external session or hook.",
        )
        def _debug_acquire_tool_view(view_name: str, payload: dict[str, Any] | None = None):
            body = payload or {}
            return self.acquire_tool_view(
                view_name,
                owner=body.get("owner"),
                reason=body.get("reason"),
                client=body.get("client"),
            )

        @app.post(
            f"{self.api_prefix}/debug/tool-views/{{view_name}}/release",
            summary="Release a tool view lease",
            description="Release a previously acquired tool view lease.",
        )
        def _debug_release_tool_view(view_name: str, payload: dict[str, Any] | None = None):
            body = payload or {}
            return self.release_tool_view(view_name, lease_id=body.get("lease_id"))

        @app.get(
            f"{self.api_prefix}/debug/tool-views/{{view_name}}/usage",
            summary="Get tool view usage state",
            description="Return active leases for one tool view.",
        )
        def _debug_tool_view_usage(view_name: str):
            return self.tool_view_usage(view_name)

        @app.post(
            f"{self.api_prefix}/debug/tool-views/{{view_name}}/release-all",
            summary="Release all tool view leases",
            description="Clear all active leases for one tool view.",
        )
        def _debug_release_all_tool_view(view_name: str):
            return self.release_all_tool_view(view_name)

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

    def create_mcp_server(self, *, view_name: str | None = None):
        """Create FastMCP server and register toolkit tools."""
        try:
            from mcp.server.fastmcp import FastMCP
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("mcp sdk is required to create MCP server") from exc

        view = self._get_tool_view_runtime(view_name)
        mcp = FastMCP(
            name="lean-mcp-toolkit" if view.resolved.name == "default" else f"lean-mcp-toolkit:{view.resolved.name}",
            stateless_http=self.config.server.mcp_stateless_http,
            json_response=self.config.server.mcp_json_response,
        )

        self._register_mcp_tools(mcp, view_name=view.resolved.name)
        return mcp

    def _register_mcp_tools(self, mcp: Any, *, view_name: str | None = None) -> None:
        view = self._get_tool_view_runtime(view_name)
        for plugin in self._group_plugins:
            aliases_by_canonical = view.aliases_by_group.get(plugin.group_name, {})
            if not aliases_by_canonical:
                continue
            service = self._group_services.get(plugin.group_name)
            if service is None:
                continue
            view_service = _ViewBoundServiceProxy(
                service=service,
                view_name=view.resolved.name,
            )
            plugin.register_mcp_tools(
                mcp,
                service=view_service,
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
        mcp_by_view = {
            view_name: self.create_mcp_server(view_name=view_name)
            for view_name in sorted(self._tool_view_runtimes.keys())
        }
        for mcp in mcp_by_view.values():
            # Mount each MCP app without an extra /mcp suffix.
            mcp.settings.streamable_http_path = "/"

        mcp_mount_path = self._normalize_path(self.config.server.mcp_mount_path, default="/mcp")

        @contextlib.asynccontextmanager
        async def lifespan(app: Any):
            _ = app
            try:
                async with contextlib.AsyncExitStack() as stack:
                    for mcp in mcp_by_view.values():
                        await stack.enter_async_context(mcp.session_manager.run())
                    yield
            finally:
                self.close()

        routes = []
        for view_name, mcp in sorted(mcp_by_view.items()):
            if view_name == "default":
                continue
            routes.append(
                Mount(
                    f"{mcp_mount_path}/{view_name}",
                    app=mcp.streamable_http_app(),
                )
            )
        routes.extend(
            [
                Mount(mcp_mount_path, app=mcp_by_view["default"].streamable_http_app()),
                Mount("/", app=api_app),
            ]
        )
        app = Starlette(
            routes=routes,
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

    def list_tool_views(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in sorted(self._tool_view_runtimes.keys()):
            runtime = self._tool_view_runtimes[name]
            usage = self._tool_view_leases.usage(view=name)
            rows.append(
                {
                    "name": name,
                    "builtin": name == "default",
                    "tool_count": len(runtime.resolved.specs_by_canonical),
                    "active_count": usage["active_count"],
                    "http_meta_endpoint": (
                        f"{self.api_prefix}/meta/tools"
                        if name == "default"
                        else f"{self.api_prefix}/views/{name}/meta/tools"
                    ),
                    "mcp_endpoint": (
                        self._normalize_path(self.config.server.mcp_mount_path, default="/mcp")
                        if name == "default"
                        else f"{self._normalize_path(self.config.server.mcp_mount_path, default='/mcp')}/{name}"
                    ),
                }
            )
        return rows

    def get_tool_view(self, view_name: str) -> dict[str, Any]:
        name = normalize_view_name(view_name)
        runtime = self._get_tool_view_runtime(name)
        usage = self._tool_view_leases.usage(view=name)
        return {
            "ok": True,
            "name": name,
            "builtin": name == "default",
            "tool_count": len(runtime.resolved.specs_by_canonical),
            "config": runtime.resolved.config.to_dict(),
            "usage": usage,
        }

    def upsert_tool_view(self, view_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        name = normalize_view_name(view_name)
        if name == "default":
            return {"ok": False, "error": "default view cannot be overwritten", "view": name}
        active_count = self._tool_view_leases.active_count(view=name)
        if active_count > 0:
            return {
                "ok": False,
                "error": "view is in use",
                "view": name,
                "active_count": active_count,
            }
        self._tool_view_configs[name] = ToolViewConfig.from_dict(payload)
        self._build_tool_views()
        runtime = self._get_tool_view_runtime(name)
        return {
            "ok": True,
            "name": name,
            "tool_count": len(runtime.resolved.specs_by_canonical),
            "http_meta_endpoint": f"{self.api_prefix}/views/{name}/meta/tools",
            "mcp_endpoint": f"{self._normalize_path(self.config.server.mcp_mount_path, default='/mcp')}/{name}",
        }

    def delete_tool_view(self, view_name: str) -> dict[str, Any]:
        name = normalize_view_name(view_name)
        if name == "default":
            return {"ok": False, "error": "default view cannot be deleted", "view": name}
        active_count = self._tool_view_leases.active_count(view=name)
        if active_count > 0:
            return {
                "ok": False,
                "error": "view is in use",
                "view": name,
                "active_count": active_count,
            }
        existed = name in self._tool_view_configs
        self._tool_view_configs.pop(name, None)
        self._tool_view_runtimes.pop(name, None)
        self._build_tool_views()
        return {"ok": True, "name": name, "deleted": existed}

    def save_tool_views(self, path: str) -> dict[str, Any]:
        import yaml

        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            name: self._tool_view_configs[name].to_dict()
            for name in sorted(self._tool_view_configs.keys())
            if name != "default"
        }
        target.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=True),
            encoding="utf-8",
        )
        return {
            "ok": True,
            "path": str(target),
            "saved_count": len(payload),
            "view_names": sorted(payload.keys()),
        }

    def load_tool_views(self, path: str, *, replace: bool = False) -> dict[str, Any]:
        import yaml

        source = Path(path).expanduser()
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
        if data is None:
            raw_views: dict[str, Any] = {}
        elif isinstance(data, dict) and isinstance(data.get("tool_views"), dict):
            raw_views = dict(data["tool_views"])
        elif isinstance(data, dict):
            raw_views = dict(data)
        else:
            raise ValueError("tool view yaml root must be a mapping")
        if replace:
            self._tool_view_configs.clear()
        loaded: list[str] = []
        for raw_name, raw_config in raw_views.items():
            if not isinstance(raw_config, dict):
                continue
            name = normalize_view_name(str(raw_name))
            if name == "default":
                continue
            active_count = self._tool_view_leases.active_count(view=name)
            if active_count > 0:
                continue
            self._tool_view_configs[name] = ToolViewConfig.from_dict(raw_config)
            loaded.append(name)
        self._build_tool_views()
        return {
            "ok": True,
            "path": str(source),
            "loaded_count": len(loaded),
            "view_names": sorted(loaded),
        }

    def acquire_tool_view(
        self,
        view_name: str,
        *,
        owner: str | None = None,
        reason: str | None = None,
        client: str | None = None,
    ) -> dict[str, Any]:
        name = normalize_view_name(view_name)
        self._get_tool_view_runtime(name)
        return self._tool_view_leases.acquire(
            view=name,
            owner=owner,
            reason=reason,
            client=client,
        )

    def release_tool_view(self, view_name: str, *, lease_id: str | None) -> dict[str, Any]:
        name = normalize_view_name(view_name)
        self._get_tool_view_runtime(name)
        return self._tool_view_leases.release(view=name, lease_id=lease_id)

    def release_all_tool_view(self, view_name: str) -> dict[str, Any]:
        name = normalize_view_name(view_name)
        self._get_tool_view_runtime(name)
        return self._tool_view_leases.release_all(view=name)

    def tool_view_usage(self, view_name: str) -> dict[str, Any]:
        name = normalize_view_name(view_name)
        self._get_tool_view_runtime(name)
        return self._tool_view_leases.usage(view=name)

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
        if not self._tool_view_configs:
            self._tool_view_configs = {
                name: view_config
                for name, view_config in self.config.tool_views.items()
                if normalize_view_name(name) != "default"
            }
        configs = {"default": default_config, **dict(self._tool_view_configs)}
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
        runtime.aliases_by_group = aliases_by_group
        if resolved.name == "default":
            self._aliases_by_group = aliases_by_group
        return runtime

    def _get_tool_view_runtime(self, view_name: str | None = None) -> _ToolViewRuntime:
        normalized = normalize_view_name(view_name)
        runtime = self._tool_view_runtimes.get(normalized)
        if runtime is None:
            raise KeyError(f"unknown tool view: {normalized}")
        return runtime

    def _get_tool_output_schemas(self, view_name: str | None = None) -> dict[str, Any | None]:
        runtime = self._get_tool_view_runtime(view_name)
        if runtime.output_schema_by_canonical:
            return runtime.output_schema_by_canonical

        schemas: dict[str, Any | None] = {
            canonical_name: None
            for canonical_name in runtime.resolved.specs_by_canonical.keys()
        }
        try:
            mcp = self.create_mcp_server(view_name=runtime.resolved.name)
        except Exception as exc:
            _LOG.debug(
                "unable to derive MCP output schemas for view `%s`: %s",
                runtime.resolved.name,
                exc,
            )
            runtime.output_schema_by_canonical = schemas
            return runtime.output_schema_by_canonical

        tools = getattr(getattr(mcp, "_tool_manager", None), "_tools", {})
        if isinstance(tools, dict):
            for alias, tool in tools.items():
                spec = runtime.specs_by_alias.get(alias)
                if spec is None:
                    continue
                schema = getattr(tool, "output_schema", None)
                if schema is None:
                    continue
                if schemas.get(spec.canonical_name) is None:
                    schemas[spec.canonical_name] = schema

        runtime.output_schema_by_canonical = schemas
        return runtime.output_schema_by_canonical

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
                return JSONResponse(serialize_payload(handler(payload)))

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
