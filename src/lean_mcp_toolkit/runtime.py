"""Unified runtime wrapper for local/http toolkit usage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .adapters.http import (
    handle_diagnostics_build,
    handle_diagnostics_lint,
    handle_diagnostics_lint_no_sorry,
)
from .app import create_diagnostics_service, create_toolkit_http_client
from .config import ToolkitConfig, load_toolkit_config
from .contracts.base import JsonDict
from .core.services import DiagnosticsService
from .transport.http import HttpConfig

ToolkitRuntimeMode = Literal["local", "http"]


class ToolkitInvoker(Protocol):
    """Tool-style invoker API shared by local and http runtime handles."""

    diagnostics: DiagnosticsService

    def diagnostics_build(self, payload: JsonDict) -> JsonDict:
        ...

    def diagnostics_lint(self, payload: JsonDict) -> JsonDict:
        ...

    def diagnostics_lint_no_sorry(self, payload: JsonDict) -> JsonDict:
        ...

    def dispatch_api(self, route_path: str, payload: JsonDict) -> JsonDict:
        ...


@dataclass(slots=True)
class _LocalToolkitInvoker(ToolkitInvoker):
    diagnostics: DiagnosticsService

    def diagnostics_build(self, payload: JsonDict) -> JsonDict:
        return handle_diagnostics_build(self.diagnostics, payload)

    def diagnostics_lint(self, payload: JsonDict) -> JsonDict:
        return handle_diagnostics_lint(self.diagnostics, payload)

    def diagnostics_lint_no_sorry(self, payload: JsonDict) -> JsonDict:
        return handle_diagnostics_lint_no_sorry(self.diagnostics, payload)

    def dispatch_api(self, route_path: str, payload: JsonDict) -> JsonDict:
        route = route_path.strip()
        if route in {"/diagnostics/build", "diagnostics.build"}:
            return self.diagnostics_build(payload)
        if route in {"/diagnostics/lint", "diagnostics.lint"}:
            return self.diagnostics_lint(payload)
        if route in {"/diagnostics/lint/no_sorry", "diagnostics.lint.no_sorry"}:
            return self.diagnostics_lint_no_sorry(payload)
        raise KeyError(f"unsupported route/tool: {route_path}")


@dataclass(slots=True)
class ToolkitRuntime:
    """Lightweight unified runtime for both local service and HTTP client."""

    mode: ToolkitRuntimeMode
    config: ToolkitConfig
    diagnostics: DiagnosticsService
    toolkit: ToolkitInvoker
    http_config: HttpConfig | None = None

    def diagnostics_build(self, payload: JsonDict) -> JsonDict:
        return self.toolkit.diagnostics_build(payload)

    def diagnostics_lint(self, payload: JsonDict) -> JsonDict:
        return self.toolkit.diagnostics_lint(payload)

    def diagnostics_lint_no_sorry(self, payload: JsonDict) -> JsonDict:
        return self.toolkit.diagnostics_lint_no_sorry(payload)

    def dispatch_api(self, route_path: str, payload: JsonDict) -> JsonDict:
        return self.toolkit.dispatch_api(route_path, payload)


def create_toolkit_runtime(
    *,
    mode: ToolkitRuntimeMode,
    config_path: str | None = None,
    http_base_url_override: str | None = None,
) -> ToolkitRuntime:
    """Create toolkit runtime with unified shape for local/http modes."""

    config = load_toolkit_config(config_path=config_path)

    if mode == "local":
        diagnostics = create_diagnostics_service(config=config)
        invoker = _LocalToolkitInvoker(diagnostics=diagnostics)
        return ToolkitRuntime(
            mode="local",
            config=config,
            diagnostics=diagnostics,
            toolkit=invoker,
            http_config=None,
        )

    if mode == "http":
        http_config = _resolve_http_config(
            config=config,
            http_base_url_override=http_base_url_override,
        )
        toolkit_client = create_toolkit_http_client(http_config=http_config, config=config)
        return ToolkitRuntime(
            mode="http",
            config=config,
            diagnostics=toolkit_client.diagnostics,
            toolkit=toolkit_client,
            http_config=http_config,
        )

    raise ValueError(f"unsupported runtime mode: {mode}")


def _resolve_http_config(
    *,
    config: ToolkitConfig,
    http_base_url_override: str | None,
) -> HttpConfig:
    raw = (http_base_url_override or "").strip()
    if raw:
        base_url = raw.rstrip("/")
    else:
        base_url = f"http://{config.server.host}:{config.server.port}"
    timeout = (
        float(config.server.default_timeout_seconds)
        if config.server.default_timeout_seconds is not None
        else 30.0
    )
    return HttpConfig(
        base_url=base_url,
        api_prefix=config.server.api_prefix,
        timeout_seconds=timeout,
    )


__all__ = ["ToolkitRuntime", "ToolkitRuntimeMode", "create_toolkit_runtime"]
