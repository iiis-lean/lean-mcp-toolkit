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
    enabled_groups: tuple[str, ...] = ("diagnostics", "declarations", "lsp_core", "search_core")
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
            enabled_groups=tuple(enabled or ("diagnostics", "declarations", "lsp_core", "search_core")),
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
    default_enabled_checks: tuple[str, ...] = ("no_sorry", "axiom_audit")
    axiom_audit_allowed_axioms: tuple[str, ...] = (
        "propext",
        "Classical.choice",
        "Quot.sound",
    )
    axiom_audit_include_sorry_ax: bool = False
    axiom_audit_decl_kinds: tuple[str, ...] = ("axiom", "constant")
    axiom_audit_fail_on_unresolved: bool = True

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DiagnosticsConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            default_include_content=to_bool(data.get("default_include_content"), default=True),
            default_context_lines=to_int(data.get("default_context_lines"), default=2) or 2,
            default_build_deps=to_bool(data.get("default_build_deps"), default=True),
            default_emit_artifacts=to_bool(data.get("default_emit_artifacts"), default=True),
            default_timeout_seconds=to_int(data.get("default_timeout_seconds"), default=None),
            default_enabled_checks=tuple(
                to_list_of_str(data.get("default_enabled_checks"))
                or ("no_sorry", "axiom_audit")
            ),
            axiom_audit_allowed_axioms=tuple(
                to_list_of_str(data.get("axiom_audit_allowed_axioms"))
                or ("propext", "Classical.choice", "Quot.sound")
            ),
            axiom_audit_include_sorry_ax=to_bool(
                data.get("axiom_audit_include_sorry_ax"),
                default=False,
            ),
            axiom_audit_decl_kinds=tuple(
                to_list_of_str(data.get("axiom_audit_decl_kinds")) or ("axiom", "constant")
            ),
            axiom_audit_fail_on_unresolved=to_bool(
                data.get("axiom_audit_fail_on_unresolved"),
                default=True,
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
            "default_enabled_checks": list(self.default_enabled_checks),
            "axiom_audit_allowed_axioms": list(self.axiom_audit_allowed_axioms),
            "axiom_audit_include_sorry_ax": self.axiom_audit_include_sorry_ax,
            "axiom_audit_decl_kinds": list(self.axiom_audit_decl_kinds),
            "axiom_audit_fail_on_unresolved": self.axiom_audit_fail_on_unresolved,
        }


DeclarationsBackend = Literal["lean_interact", "native"]


@dataclass(slots=True, frozen=True)
class DeclarationsConfig:
    enabled: bool = True
    default_backend: DeclarationsBackend = "lean_interact"
    default_include_value: bool = False
    default_timeout_seconds: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DeclarationsConfig":
        backend_raw = str(data.get("default_backend") or "lean_interact")
        backend: DeclarationsBackend = "lean_interact"
        if backend_raw in {"lean_interact", "native"}:
            backend = backend_raw  # type: ignore[assignment]
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            default_backend=backend,
            default_include_value=to_bool(data.get("default_include_value"), default=False),
            default_timeout_seconds=to_int(data.get("default_timeout_seconds"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "default_backend": self.default_backend,
            "default_include_value": self.default_include_value,
            "default_timeout_seconds": self.default_timeout_seconds,
        }


@dataclass(slots=True, frozen=True)
class LspCoreConfig:
    enabled: bool = True
    default_response_format: str = "structured"
    default_max_declarations: int | None = None
    hover_include_diagnostics_default: bool = True
    code_actions_max_actions: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspCoreConfig":
        response_format = str(data.get("default_response_format") or "structured").strip()
        if response_format not in {"structured", "markdown"}:
            response_format = "structured"
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            default_response_format=response_format,
            default_max_declarations=to_int(data.get("default_max_declarations"), default=None),
            hover_include_diagnostics_default=to_bool(
                data.get("hover_include_diagnostics_default"),
                default=True,
            ),
            code_actions_max_actions=to_int(data.get("code_actions_max_actions"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "default_response_format": self.default_response_format,
            "default_max_declarations": self.default_max_declarations,
            "hover_include_diagnostics_default": self.hover_include_diagnostics_default,
            "code_actions_max_actions": self.code_actions_max_actions,
        }


@dataclass(slots=True, frozen=True)
class SearchCoreConfig:
    enabled: bool = True
    default_limit: int = 10
    default_rerank_top: int | None = 50
    default_packages: tuple[str, ...] = ("Mathlib",)
    mathlib_lean_version: str = "4.28.0"
    require_mathlib: bool = True
    local_decl_default_limit: int = 10
    local_decl_include_dependencies: bool = True
    local_decl_include_stdlib: bool = True
    local_decl_max_candidates: int = 2048
    local_decl_require_rg: bool = True

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchCoreConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            default_limit=to_int(data.get("default_limit"), default=10) or 10,
            default_rerank_top=to_int(data.get("default_rerank_top"), default=50),
            default_packages=tuple(to_list_of_str(data.get("default_packages")) or ("Mathlib",)),
            mathlib_lean_version=str(data.get("mathlib_lean_version") or "4.28.0"),
            require_mathlib=to_bool(data.get("require_mathlib"), default=True),
            local_decl_default_limit=to_int(data.get("local_decl_default_limit"), default=10) or 10,
            local_decl_include_dependencies=to_bool(
                data.get("local_decl_include_dependencies"),
                default=True,
            ),
            local_decl_include_stdlib=to_bool(
                data.get("local_decl_include_stdlib"),
                default=True,
            ),
            local_decl_max_candidates=(
                to_int(data.get("local_decl_max_candidates"), default=2048) or 2048
            ),
            local_decl_require_rg=to_bool(data.get("local_decl_require_rg"), default=True),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "default_limit": self.default_limit,
            "default_rerank_top": self.default_rerank_top,
            "default_packages": list(self.default_packages),
            "mathlib_lean_version": self.mathlib_lean_version,
            "require_mathlib": self.require_mathlib,
            "local_decl_default_limit": self.local_decl_default_limit,
            "local_decl_include_dependencies": self.local_decl_include_dependencies,
            "local_decl_include_stdlib": self.local_decl_include_stdlib,
            "local_decl_max_candidates": self.local_decl_max_candidates,
            "local_decl_require_rg": self.local_decl_require_rg,
        }


@dataclass(slots=True, frozen=True)
class LeanCommandBackendConfig:
    max_concurrent_lean_checks: int = 4
    max_concurrent_lake_build: int = 1
    enable_concurrency_limits: bool = False
    lake_build_jobs: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LeanCommandBackendConfig":
        return cls(
            max_concurrent_lean_checks=(
                to_int(data.get("max_concurrent_lean_checks"), default=4) or 4
            ),
            max_concurrent_lake_build=(
                to_int(data.get("max_concurrent_lake_build"), default=1) or 1
            ),
            enable_concurrency_limits=to_bool(
                data.get("enable_concurrency_limits"), default=False
            ),
            lake_build_jobs=to_int(data.get("lake_build_jobs"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "max_concurrent_lean_checks": self.max_concurrent_lean_checks,
            "max_concurrent_lake_build": self.max_concurrent_lake_build,
            "enable_concurrency_limits": self.enable_concurrency_limits,
            "lake_build_jobs": self.lake_build_jobs,
        }


@dataclass(slots=True, frozen=True)
class LeanInteractBackendConfig:
    use_auto_server: bool = False
    project_auto_build: bool = False
    build_repl: bool = True
    force_pull_repl: bool = False
    memory_hard_limit_mb: int | None = None
    enable_incremental_optimization: bool = True
    enable_parallel_elaboration: bool = True
    verbose: bool = False

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LeanInteractBackendConfig":
        return cls(
            use_auto_server=to_bool(data.get("use_auto_server"), default=False),
            project_auto_build=to_bool(data.get("project_auto_build"), default=False),
            build_repl=to_bool(data.get("build_repl"), default=True),
            force_pull_repl=to_bool(data.get("force_pull_repl"), default=False),
            memory_hard_limit_mb=to_int(data.get("memory_hard_limit_mb"), default=None),
            enable_incremental_optimization=to_bool(
                data.get("enable_incremental_optimization"), default=True
            ),
            enable_parallel_elaboration=to_bool(
                data.get("enable_parallel_elaboration"), default=True
            ),
            verbose=to_bool(data.get("verbose"), default=False),
        )

    def to_dict(self) -> JsonDict:
        return {
            "use_auto_server": self.use_auto_server,
            "project_auto_build": self.project_auto_build,
            "build_repl": self.build_repl,
            "force_pull_repl": self.force_pull_repl,
            "memory_hard_limit_mb": self.memory_hard_limit_mb,
            "enable_incremental_optimization": self.enable_incremental_optimization,
            "enable_parallel_elaboration": self.enable_parallel_elaboration,
            "verbose": self.verbose,
        }


@dataclass(slots=True, frozen=True)
class LspBackendConfig:
    enabled: bool = True
    default_timeout_seconds: int | None = None
    initial_build: bool = False
    diagnostics_timeout_seconds: int = 15
    inactivity_timeout_seconds: int = 15
    workspace_symbol_limit: int = 2000

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspBackendConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            default_timeout_seconds=to_int(data.get("default_timeout_seconds"), default=None),
            initial_build=to_bool(data.get("initial_build"), default=False),
            diagnostics_timeout_seconds=(
                to_int(data.get("diagnostics_timeout_seconds"), default=15) or 15
            ),
            inactivity_timeout_seconds=(
                to_int(data.get("inactivity_timeout_seconds"), default=15) or 15
            ),
            workspace_symbol_limit=to_int(data.get("workspace_symbol_limit"), default=2000)
            or 2000,
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "default_timeout_seconds": self.default_timeout_seconds,
            "initial_build": self.initial_build,
            "diagnostics_timeout_seconds": self.diagnostics_timeout_seconds,
            "inactivity_timeout_seconds": self.inactivity_timeout_seconds,
            "workspace_symbol_limit": self.workspace_symbol_limit,
        }


@dataclass(slots=True, frozen=True)
class LeanExploreBackendConfig:
    enabled: bool = True
    mode: str = "local"
    cache_dir: str | None = None
    data_dir: str | None = None
    packages_root: str | None = None
    auto_fetch_missing_toolchain: bool = True
    fetch_timeout_seconds: int = 1800
    startup_verify_index: bool = True
    startup_verify_mathlib: bool = True
    api_base_url: str = "https://www.leanexplore.com/api/v2"
    api_key_env: str = "LEANEXPLORE_API_KEY"
    api_timeout_seconds: int = 30

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LeanExploreBackendConfig":
        mode = str(data.get("mode") or "local").strip().lower()
        if mode not in {"local", "api"}:
            mode = "local"
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            mode=mode,
            cache_dir=(str(data["cache_dir"]) if data.get("cache_dir") is not None else None),
            data_dir=(str(data["data_dir"]) if data.get("data_dir") is not None else None),
            packages_root=(
                str(data["packages_root"]) if data.get("packages_root") is not None else None
            ),
            auto_fetch_missing_toolchain=to_bool(
                data.get("auto_fetch_missing_toolchain"),
                default=True,
            ),
            fetch_timeout_seconds=(
                to_int(data.get("fetch_timeout_seconds"), default=1800) or 1800
            ),
            startup_verify_index=to_bool(data.get("startup_verify_index"), default=True),
            startup_verify_mathlib=to_bool(data.get("startup_verify_mathlib"), default=True),
            api_base_url=str(data.get("api_base_url") or "https://www.leanexplore.com/api/v2"),
            api_key_env=str(data.get("api_key_env") or "LEANEXPLORE_API_KEY"),
            api_timeout_seconds=to_int(data.get("api_timeout_seconds"), default=30) or 30,
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "cache_dir": self.cache_dir,
            "data_dir": self.data_dir,
            "packages_root": self.packages_root,
            "auto_fetch_missing_toolchain": self.auto_fetch_missing_toolchain,
            "fetch_timeout_seconds": self.fetch_timeout_seconds,
            "startup_verify_index": self.startup_verify_index,
            "startup_verify_mathlib": self.startup_verify_mathlib,
            "api_base_url": self.api_base_url,
            "api_key_env": self.api_key_env,
            "api_timeout_seconds": self.api_timeout_seconds,
        }


@dataclass(slots=True, frozen=True)
class BackendsConfig:
    lean_command: LeanCommandBackendConfig = field(default_factory=LeanCommandBackendConfig)
    lean_interact: LeanInteractBackendConfig = field(default_factory=LeanInteractBackendConfig)
    lsp: LspBackendConfig = field(default_factory=LspBackendConfig)
    lean_explore: LeanExploreBackendConfig = field(default_factory=LeanExploreBackendConfig)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "BackendsConfig":
        raw_lean_command = data.get("lean_command")
        raw_lean_interact = data.get("lean_interact")
        raw_lsp = data.get("lsp")
        raw_lean_explore = data.get("lean_explore")
        return cls(
            lean_command=(
                LeanCommandBackendConfig.from_dict(raw_lean_command)
                if isinstance(raw_lean_command, dict)
                else LeanCommandBackendConfig()
            ),
            lean_interact=(
                LeanInteractBackendConfig.from_dict(raw_lean_interact)
                if isinstance(raw_lean_interact, dict)
                else LeanInteractBackendConfig()
            ),
            lsp=(
                LspBackendConfig.from_dict(raw_lsp)
                if isinstance(raw_lsp, dict)
                else LspBackendConfig()
            ),
            lean_explore=(
                LeanExploreBackendConfig.from_dict(raw_lean_explore)
                if isinstance(raw_lean_explore, dict)
                else LeanExploreBackendConfig()
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "lean_command": self.lean_command.to_dict(),
            "lean_interact": self.lean_interact.to_dict(),
            "lsp": self.lsp.to_dict(),
            "lean_explore": self.lean_explore.to_dict(),
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
    declarations: DeclarationsConfig = field(default_factory=DeclarationsConfig)
    lsp_core: LspCoreConfig = field(default_factory=LspCoreConfig)
    search_core: SearchCoreConfig = field(default_factory=SearchCoreConfig)
    backends: BackendsConfig = field(default_factory=BackendsConfig)
    toolchain: ToolchainConfig = field(default_factory=ToolchainConfig)
    raw_group_overrides: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ToolkitConfig":
        raw_server = data.get("server")
        raw_groups = data.get("groups")
        raw_diag = data.get("diagnostics")
        raw_declarations = data.get("declarations")
        raw_lsp_core = data.get("lsp_core")
        raw_search_core = data.get("search_core")
        raw_backends = data.get("backends")
        raw_toolchain = data.get("toolchain")
        raw_overrides = data.get("raw_group_overrides")

        diagnostics = (
            DiagnosticsConfig.from_dict(raw_diag)
            if isinstance(raw_diag, dict)
            else DiagnosticsConfig()
        )
        declarations = (
            DeclarationsConfig.from_dict(raw_declarations)
            if isinstance(raw_declarations, dict)
            else DeclarationsConfig()
        )
        lsp_core = (
            LspCoreConfig.from_dict(raw_lsp_core)
            if isinstance(raw_lsp_core, dict)
            else LspCoreConfig()
        )
        search_core = (
            SearchCoreConfig.from_dict(raw_search_core)
            if isinstance(raw_search_core, dict)
            else SearchCoreConfig()
        )
        backends = (
            BackendsConfig.from_dict(raw_backends)
            if isinstance(raw_backends, dict)
            else BackendsConfig()
        )

        return cls(
            server=ServerConfig.from_dict(raw_server) if isinstance(raw_server, dict) else ServerConfig(),
            groups=(
                GroupActivationConfig.from_dict(raw_groups)
                if isinstance(raw_groups, dict)
                else GroupActivationConfig()
            ),
            diagnostics=diagnostics,
            declarations=declarations,
            lsp_core=lsp_core,
            search_core=search_core,
            backends=backends,
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
            "declarations": self.declarations.to_dict(),
            "lsp_core": self.lsp_core.to_dict(),
            "search_core": self.search_core.to_dict(),
            "backends": self.backends.to_dict(),
            "toolchain": self.toolchain.to_dict(),
            "raw_group_overrides": dict(self.raw_group_overrides),
        }
