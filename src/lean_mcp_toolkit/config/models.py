"""Strongly-typed toolkit configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..contracts.base import JsonDict, to_bool, to_int, to_list_of_str

ServerMode = Literal["mcp", "http", "unified"]
MCPTransport = Literal["stdio", "sse", "streamable-http"]
ToolNamingMode = Literal["raw", "prefixed", "both"]


@dataclass(slots=True, frozen=True)
class ServerConfig:
    mode: ServerMode = "unified"
    host: str = "127.0.0.1"
    port: int = 18080
    log_level: str = "info"
    api_prefix: str = "/api/v1"
    default_project_root: str | None = None
    default_timeout_seconds: int | None = None
    mcp_transport: MCPTransport = "streamable-http"
    mcp_streamable_http_path: str = "/mcp"
    mcp_mount_path: str = "/mcp"
    mcp_json_response: bool = True
    mcp_stateless_http: bool = True

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ServerConfig":
        mode_raw = str(data.get("mode") or "unified")
        mode: ServerMode = "unified"
        if mode_raw in {"mcp", "http", "unified"}:
            mode = mode_raw  # type: ignore[assignment]
        mcp_transport_raw = str(data.get("mcp_transport") or "streamable-http")
        mcp_transport: MCPTransport = "streamable-http"
        if mcp_transport_raw in {"stdio", "sse", "streamable-http"}:
            mcp_transport = mcp_transport_raw  # type: ignore[assignment]
        return cls(
            mode=mode,
            host=str(data.get("host") or "127.0.0.1"),
            port=to_int(data.get("port"), default=18080) or 18080,
            log_level=str(data.get("log_level") or "info"),
            api_prefix=str(data.get("api_prefix") or "/api/v1"),
            default_project_root=(
                str(data["default_project_root"])
                if data.get("default_project_root") is not None
                else None
            ),
            default_timeout_seconds=to_int(data.get("default_timeout_seconds"), default=None),
            mcp_transport=mcp_transport,
            mcp_streamable_http_path=str(data.get("mcp_streamable_http_path") or "/mcp"),
            mcp_mount_path=str(data.get("mcp_mount_path") or "/mcp"),
            mcp_json_response=to_bool(data.get("mcp_json_response"), default=True),
            mcp_stateless_http=to_bool(data.get("mcp_stateless_http"), default=True),
        )

    def to_dict(self) -> JsonDict:
        return {
            "mode": self.mode,
            "host": self.host,
            "port": self.port,
            "log_level": self.log_level,
            "api_prefix": self.api_prefix,
            "default_project_root": self.default_project_root,
            "default_timeout_seconds": self.default_timeout_seconds,
            "mcp_transport": self.mcp_transport,
            "mcp_streamable_http_path": self.mcp_streamable_http_path,
            "mcp_mount_path": self.mcp_mount_path,
            "mcp_json_response": self.mcp_json_response,
            "mcp_stateless_http": self.mcp_stateless_http,
        }


@dataclass(slots=True, frozen=True)
class GroupActivationConfig:
    enabled_groups: tuple[str, ...] = ("diagnostics", "lsp_core", "search_core")
    disabled_groups: tuple[str, ...] = field(default_factory=tuple)
    include_tools: tuple[str, ...] = field(default_factory=tuple)
    exclude_tools: tuple[str, ...] = field(default_factory=tuple)
    auto_enable_group_deps: bool = True
    tool_naming_mode: ToolNamingMode = "prefixed"

    @classmethod
    def from_dict(cls, data: JsonDict) -> "GroupActivationConfig":
        mode_raw = str(data.get("tool_naming_mode") or "prefixed")
        mode: ToolNamingMode = "prefixed"
        if mode_raw in {"raw", "prefixed", "both"}:
            mode = mode_raw  # type: ignore[assignment]
        enabled = to_list_of_str(data.get("enabled_groups"))
        disabled = to_list_of_str(data.get("disabled_groups"))
        includes = to_list_of_str(data.get("include_tools"))
        excludes = to_list_of_str(data.get("exclude_tools"))
        return cls(
            enabled_groups=tuple(enabled or ("diagnostics", "lsp_core", "search_core")),
            disabled_groups=tuple(disabled or ()),
            include_tools=tuple(includes or ()),
            exclude_tools=tuple(excludes or ()),
            auto_enable_group_deps=to_bool(data.get("auto_enable_group_deps"), default=True),
            tool_naming_mode=mode,
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled_groups": list(self.enabled_groups),
            "disabled_groups": list(self.disabled_groups),
            "include_tools": list(self.include_tools),
            "exclude_tools": list(self.exclude_tools),
            "auto_enable_group_deps": self.auto_enable_group_deps,
            "tool_naming_mode": self.tool_naming_mode,
        }


@dataclass(slots=True, frozen=True)
class DiagnosticsConfig:
    enabled: bool = True
    default_include_content: bool = True
    default_context_lines: int = 2
    default_build_deps: bool = True
    default_emit_artifacts: bool = True
    default_timeout_seconds: int | None = None
    max_concurrent_lean_checks: int = 4
    max_concurrent_lake_build: int = 1
    enable_concurrency_limits: bool = False
    lake_build_jobs: int | None = None
    default_enabled_checks: tuple[str, ...] = ("no_sorry", "no_axiom_decl", "axiom_usage")

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DiagnosticsConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            default_include_content=to_bool(data.get("default_include_content"), default=True),
            default_context_lines=to_int(data.get("default_context_lines"), default=2) or 2,
            default_build_deps=to_bool(data.get("default_build_deps"), default=True),
            default_emit_artifacts=to_bool(data.get("default_emit_artifacts"), default=True),
            default_timeout_seconds=to_int(data.get("default_timeout_seconds"), default=None),
            max_concurrent_lean_checks=to_int(data.get("max_concurrent_lean_checks"), default=4)
            or 4,
            max_concurrent_lake_build=to_int(data.get("max_concurrent_lake_build"), default=1)
            or 1,
            enable_concurrency_limits=to_bool(
                data.get("enable_concurrency_limits"), default=False
            ),
            lake_build_jobs=to_int(data.get("lake_build_jobs"), default=None),
            default_enabled_checks=tuple(
                to_list_of_str(data.get("default_enabled_checks"))
                or ("no_sorry", "no_axiom_decl", "axiom_usage")
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "default_include_content": self.default_include_content,
            "default_context_lines": self.default_context_lines,
            "default_build_deps": self.default_build_deps,
            "default_emit_artifacts": self.default_emit_artifacts,
            "default_timeout_seconds": self.default_timeout_seconds,
            "max_concurrent_lean_checks": self.max_concurrent_lean_checks,
            "max_concurrent_lake_build": self.max_concurrent_lake_build,
            "enable_concurrency_limits": self.enable_concurrency_limits,
            "lake_build_jobs": self.lake_build_jobs,
            "default_enabled_checks": list(self.default_enabled_checks),
        }


@dataclass(slots=True, frozen=True)
class ToolchainConfig:
    lean_bin: str = "lean"
    lake_bin: str = "lake"
    elan_bin: str = "elan"
    prefer_elan: bool = False
    use_lake_env_for_lean: bool = True
    extra_env: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ToolchainConfig":
        raw_extra_env = data.get("extra_env")
        return cls(
            lean_bin=str(data.get("lean_bin") or "lean"),
            lake_bin=str(data.get("lake_bin") or "lake"),
            elan_bin=str(data.get("elan_bin") or "elan"),
            prefer_elan=to_bool(data.get("prefer_elan"), default=False),
            use_lake_env_for_lean=to_bool(data.get("use_lake_env_for_lean"), default=True),
            extra_env=dict(raw_extra_env) if isinstance(raw_extra_env, dict) else {},
        )

    def to_dict(self) -> JsonDict:
        return {
            "lean_bin": self.lean_bin,
            "lake_bin": self.lake_bin,
            "elan_bin": self.elan_bin,
            "prefer_elan": self.prefer_elan,
            "use_lake_env_for_lean": self.use_lake_env_for_lean,
            "extra_env": dict(self.extra_env),
        }


@dataclass(slots=True, frozen=True)
class ToolkitConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    groups: GroupActivationConfig = field(default_factory=GroupActivationConfig)
    diagnostics: DiagnosticsConfig = field(default_factory=DiagnosticsConfig)
    toolchain: ToolchainConfig = field(default_factory=ToolchainConfig)
    raw_group_overrides: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ToolkitConfig":
        raw_server = data.get("server")
        raw_groups = data.get("groups")
        raw_diag = data.get("diagnostics")
        raw_toolchain = data.get("toolchain")
        raw_overrides = data.get("raw_group_overrides")
        return cls(
            server=ServerConfig.from_dict(raw_server) if isinstance(raw_server, dict) else ServerConfig(),
            groups=(
                GroupActivationConfig.from_dict(raw_groups)
                if isinstance(raw_groups, dict)
                else GroupActivationConfig()
            ),
            diagnostics=(
                DiagnosticsConfig.from_dict(raw_diag)
                if isinstance(raw_diag, dict)
                else DiagnosticsConfig()
            ),
            toolchain=(
                ToolchainConfig.from_dict(raw_toolchain)
                if isinstance(raw_toolchain, dict)
                else ToolchainConfig()
            ),
            raw_group_overrides=(dict(raw_overrides) if isinstance(raw_overrides, dict) else {}),
        )

    def to_dict(self) -> JsonDict:
        return {
            "server": self.server.to_dict(),
            "groups": self.groups.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
            "toolchain": self.toolchain.to_dict(),
            "raw_group_overrides": dict(self.raw_group_overrides),
        }
