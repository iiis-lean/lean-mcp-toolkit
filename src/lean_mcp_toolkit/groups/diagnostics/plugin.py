"""Diagnostics group plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ...adapters.http import (
    handle_diagnostics_build,
    handle_diagnostics_lint,
    handle_diagnostics_lint_no_sorry,
)
from ...config import ToolkitConfig
from ...contracts.base import JsonDict
from ...transport.http import HttpConfig
from .factory import create_diagnostics_client, create_diagnostics_service
from ..plugin_base import GroupPlugin, GroupToolSpec, ToolHandler

_TOOL_SPECS: tuple[GroupToolSpec, ...] = (
    GroupToolSpec(
        group_name="diagnostics",
        canonical_name="diagnostics.build",
        raw_name="build",
        api_path="/diagnostics/build",
        description="Run multi-file Lean build diagnostics with structured output.",
    ),
    GroupToolSpec(
        group_name="diagnostics",
        canonical_name="diagnostics.lint",
        raw_name="lint",
        api_path="/diagnostics/lint",
        description="Run configured lint checks and return all check results.",
    ),
    GroupToolSpec(
        group_name="diagnostics",
        canonical_name="diagnostics.lint.no_sorry",
        raw_name="lint.no_sorry",
        api_path="/diagnostics/lint/no_sorry",
        description="Run sorry-only lint check and return all sorry diagnostics.",
    ),
)


@dataclass(slots=True, frozen=True)
class DiagnosticsGroupPlugin(GroupPlugin):
    group_name: str = "diagnostics"

    def create_local_service(self, config: ToolkitConfig):
        return create_diagnostics_service(config=config)

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        return create_diagnostics_client(http_config=http_config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return _TOOL_SPECS

    def tool_handlers(self, service: Any) -> Mapping[str, ToolHandler]:
        return {
            "diagnostics.build": lambda payload: handle_diagnostics_build(service, payload),
            "diagnostics.lint": lambda payload: handle_diagnostics_lint(service, payload),
            "diagnostics.lint.no_sorry": (
                lambda payload: handle_diagnostics_lint_no_sorry(service, payload)
            ),
        }

    def register_mcp_tools(
        self,
        mcp: Any,
        *,
        service: Any,
        aliases_by_canonical: Mapping[str, tuple[str, ...]],
        normalize_str_list,
        prune_none,
    ) -> None:
        for alias in aliases_by_canonical.get("diagnostics.build", ()):
            self._register_build(
                mcp=mcp,
                alias=alias,
                service=service,
                normalize_str_list=normalize_str_list,
                prune_none=prune_none,
            )
        for alias in aliases_by_canonical.get("diagnostics.lint", ()):
            self._register_lint(
                mcp=mcp,
                alias=alias,
                service=service,
                normalize_str_list=normalize_str_list,
                prune_none=prune_none,
            )
        for alias in aliases_by_canonical.get("diagnostics.lint.no_sorry", ()):
            self._register_lint_no_sorry(
                mcp=mcp,
                alias=alias,
                service=service,
                normalize_str_list=normalize_str_list,
                prune_none=prune_none,
            )

    @staticmethod
    def _register_build(
        *,
        mcp: Any,
        alias: str,
        service: Any,
        normalize_str_list,
        prune_none,
    ) -> None:
        @mcp.tool(
            name=alias,
            description="Run multi-file Lean build diagnostics with structured output.",
        )
        def _diagnostics_build(
            project_root: str | None = None,
            targets: list[str] | str | None = None,
            build_deps: bool | None = None,
            emit_artifacts: bool | None = None,
            include_content: bool | None = None,
            context_lines: int | None = None,
            timeout_seconds: int | None = None,
        ) -> JsonDict:
            payload = {
                "project_root": project_root,
                "targets": normalize_str_list(targets),
                "build_deps": build_deps,
                "emit_artifacts": emit_artifacts,
                "include_content": include_content,
                "context_lines": context_lines,
                "timeout_seconds": timeout_seconds,
            }
            return handle_diagnostics_build(service, prune_none(payload))

    @staticmethod
    def _register_lint(
        *,
        mcp: Any,
        alias: str,
        service: Any,
        normalize_str_list,
        prune_none,
    ) -> None:
        @mcp.tool(
            name=alias,
            description="Run configured lint checks and return all check results.",
        )
        def _diagnostics_lint(
            project_root: str | None = None,
            targets: list[str] | str | None = None,
            enabled_checks: list[str] | str | None = None,
            include_content: bool | None = None,
            context_lines: int | None = None,
            timeout_seconds: int | None = None,
        ) -> JsonDict:
            payload = {
                "project_root": project_root,
                "targets": normalize_str_list(targets),
                "enabled_checks": normalize_str_list(enabled_checks),
                "include_content": include_content,
                "context_lines": context_lines,
                "timeout_seconds": timeout_seconds,
            }
            return handle_diagnostics_lint(service, prune_none(payload))

    @staticmethod
    def _register_lint_no_sorry(
        *,
        mcp: Any,
        alias: str,
        service: Any,
        normalize_str_list,
        prune_none,
    ) -> None:
        @mcp.tool(
            name=alias,
            description="Run sorry-only lint check and return all sorry diagnostics.",
        )
        def _diagnostics_lint_no_sorry(
            project_root: str | None = None,
            targets: list[str] | str | None = None,
            include_content: bool | None = None,
            context_lines: int | None = None,
            timeout_seconds: int | None = None,
        ) -> JsonDict:
            payload = {
                "project_root": project_root,
                "targets": normalize_str_list(targets),
                "include_content": include_content,
                "context_lines": context_lines,
                "timeout_seconds": timeout_seconds,
            }
            return handle_diagnostics_lint_no_sorry(service, prune_none(payload))

__all__ = ["DiagnosticsGroupPlugin"]
