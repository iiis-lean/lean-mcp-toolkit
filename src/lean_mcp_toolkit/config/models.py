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
    enabled_groups: tuple[str, ...] = (
        "diagnostics",
        "declarations",
        "lsp_core",
        "search_core",
        "mathlib_nav",
    )
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
            enabled_groups=tuple(
                enabled
                or ("diagnostics", "declarations", "lsp_core", "search_core", "mathlib_nav")
            ),
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
class BuildBaseConfig:
    enabled: bool = False
    default_timeout_seconds: int | None = None
    default_jobs: int | None = None
    default_clean_first: bool = False

    @classmethod
    def from_dict(cls, data: JsonDict) -> "BuildBaseConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=False),
            default_timeout_seconds=to_int(data.get("default_timeout_seconds"), default=None),
            default_jobs=to_int(data.get("default_jobs"), default=None),
            default_clean_first=to_bool(data.get("default_clean_first"), default=False),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "default_timeout_seconds": self.default_timeout_seconds,
            "default_jobs": self.default_jobs,
            "default_clean_first": self.default_clean_first,
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
class LspAssistConfig:
    enabled: bool = False
    default_max_completions: int = 32
    multi_attempt_default_max_attempts: int | None = None
    multi_attempt_max_snippets_hard_limit: int = 16
    run_snippet_default_timeout_seconds: int | None = None
    run_snippet_max_code_chars: int = 20000
    theorem_soundness_scan_source_default: bool = True
    declaration_file_include_content_default: bool = False

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspAssistConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=False),
            default_max_completions=to_int(data.get("default_max_completions"), default=32) or 32,
            multi_attempt_default_max_attempts=to_int(
                data.get("multi_attempt_default_max_attempts"),
                default=None,
            ),
            multi_attempt_max_snippets_hard_limit=(
                to_int(data.get("multi_attempt_max_snippets_hard_limit"), default=16) or 16
            ),
            run_snippet_default_timeout_seconds=to_int(
                data.get("run_snippet_default_timeout_seconds"),
                default=None,
            ),
            run_snippet_max_code_chars=(
                to_int(data.get("run_snippet_max_code_chars"), default=20000) or 20000
            ),
            theorem_soundness_scan_source_default=to_bool(
                data.get("theorem_soundness_scan_source_default"),
                default=True,
            ),
            declaration_file_include_content_default=to_bool(
                data.get("declaration_file_include_content_default"),
                default=False,
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "default_max_completions": self.default_max_completions,
            "multi_attempt_default_max_attempts": self.multi_attempt_default_max_attempts,
            "multi_attempt_max_snippets_hard_limit": self.multi_attempt_max_snippets_hard_limit,
            "run_snippet_default_timeout_seconds": self.run_snippet_default_timeout_seconds,
            "run_snippet_max_code_chars": self.run_snippet_max_code_chars,
            "theorem_soundness_scan_source_default": self.theorem_soundness_scan_source_default,
            "declaration_file_include_content_default": self.declaration_file_include_content_default,
        }


@dataclass(slots=True, frozen=True)
class LspHeavyConfig:
    enabled: bool = False
    proof_profile_default_top_n: int = 5
    proof_profile_default_timeout_seconds: int | None = 60
    widget_source_max_chars: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspHeavyConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=False),
            proof_profile_default_top_n=(
                to_int(data.get("proof_profile_default_top_n"), default=5) or 5
            ),
            proof_profile_default_timeout_seconds=to_int(
                data.get("proof_profile_default_timeout_seconds"),
                default=60,
            ),
            widget_source_max_chars=to_int(data.get("widget_source_max_chars"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "proof_profile_default_top_n": self.proof_profile_default_top_n,
            "proof_profile_default_timeout_seconds": self.proof_profile_default_timeout_seconds,
            "widget_source_max_chars": self.widget_source_max_chars,
        }


LoogleMode = Literal["remote", "local", "prefer_local"]


@dataclass(slots=True, frozen=True)
class SearchAltConfig:
    enabled: bool = False
    leansearch_default_num_results: int = 5
    leandex_default_num_results: int = 5
    loogle_default_num_results: int = 8
    leanfinder_default_num_results: int = 5
    include_raw_payload_default: bool = False

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchAltConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=False),
            leansearch_default_num_results=(
                to_int(data.get("leansearch_default_num_results"), default=5) or 5
            ),
            leandex_default_num_results=(
                to_int(data.get("leandex_default_num_results"), default=5) or 5
            ),
            loogle_default_num_results=(
                to_int(data.get("loogle_default_num_results"), default=8) or 8
            ),
            leanfinder_default_num_results=(
                to_int(data.get("leanfinder_default_num_results"), default=5) or 5
            ),
            include_raw_payload_default=to_bool(
                data.get("include_raw_payload_default"),
                default=False,
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "leansearch_default_num_results": self.leansearch_default_num_results,
            "leandex_default_num_results": self.leandex_default_num_results,
            "loogle_default_num_results": self.loogle_default_num_results,
            "leanfinder_default_num_results": self.leanfinder_default_num_results,
            "include_raw_payload_default": self.include_raw_payload_default,
        }


@dataclass(slots=True, frozen=True)
class ProofSearchAltConfig:
    enabled: bool = False
    state_search_default_num_results: int = 5
    hammer_premise_default_num_results: int = 32
    include_raw_payload_default: bool = False

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ProofSearchAltConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=False),
            state_search_default_num_results=(
                to_int(data.get("state_search_default_num_results"), default=5) or 5
            ),
            hammer_premise_default_num_results=(
                to_int(data.get("hammer_premise_default_num_results"), default=32) or 32
            ),
            include_raw_payload_default=to_bool(
                data.get("include_raw_payload_default"),
                default=False,
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "state_search_default_num_results": self.state_search_default_num_results,
            "hammer_premise_default_num_results": self.hammer_premise_default_num_results,
            "include_raw_payload_default": self.include_raw_payload_default,
        }


@dataclass(slots=True, frozen=True)
class SearchCoreConfig:
    enabled: bool = True
    default_limit: int = 10
    default_rerank_top: int | None = 50
    default_packages: tuple[str, ...] = ("Mathlib",)
    mathlib_lean_version: str = "4.28.0"
    require_mathlib: bool = True

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchCoreConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            default_limit=to_int(data.get("default_limit"), default=10) or 10,
            default_rerank_top=to_int(data.get("default_rerank_top"), default=50),
            default_packages=tuple(to_list_of_str(data.get("default_packages")) or ("Mathlib",)),
            mathlib_lean_version=str(data.get("mathlib_lean_version") or "4.28.0"),
            require_mathlib=to_bool(data.get("require_mathlib"), default=True),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "default_limit": self.default_limit,
            "default_rerank_top": self.default_rerank_top,
            "default_packages": list(self.default_packages),
            "mathlib_lean_version": self.mathlib_lean_version,
            "require_mathlib": self.require_mathlib,
        }


@dataclass(slots=True, frozen=True)
class SearchNavConfig:
    enabled: bool = False
    default_limit: int = 20
    include_deps_default: bool = False
    default_context_lines: int = 2
    read_default_max_lines: int = 120
    read_with_line_numbers_default: bool = True
    outline_include_imports_default: bool = True
    outline_include_module_doc_default: bool = True
    outline_include_section_doc_default: bool = True
    outline_include_decl_headers_default: bool = True
    outline_include_scope_cmds_default: bool = True
    outline_default_limit_decls: int = 200
    refs_include_definition_default: bool = False
    scan_max_file_bytes: int = 2_000_000
    scan_max_files: int = 5000

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchNavConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            default_limit=to_int(data.get("default_limit"), default=20) or 20,
            include_deps_default=to_bool(data.get("include_deps_default"), default=False),
            default_context_lines=to_int(data.get("default_context_lines"), default=2) or 2,
            read_default_max_lines=to_int(data.get("read_default_max_lines"), default=120) or 120,
            read_with_line_numbers_default=to_bool(
                data.get("read_with_line_numbers_default"),
                default=True,
            ),
            outline_include_imports_default=to_bool(
                data.get("outline_include_imports_default"),
                default=True,
            ),
            outline_include_module_doc_default=to_bool(
                data.get("outline_include_module_doc_default"),
                default=True,
            ),
            outline_include_section_doc_default=to_bool(
                data.get("outline_include_section_doc_default"),
                default=True,
            ),
            outline_include_decl_headers_default=to_bool(
                data.get("outline_include_decl_headers_default"),
                default=True,
            ),
            outline_include_scope_cmds_default=to_bool(
                data.get("outline_include_scope_cmds_default"),
                default=True,
            ),
            outline_default_limit_decls=(
                to_int(data.get("outline_default_limit_decls"), default=200) or 200
            ),
            refs_include_definition_default=to_bool(
                data.get("refs_include_definition_default"),
                default=False,
            ),
            scan_max_file_bytes=to_int(data.get("scan_max_file_bytes"), default=2_000_000)
            or 2_000_000,
            scan_max_files=to_int(data.get("scan_max_files"), default=5000) or 5000,
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "default_limit": self.default_limit,
            "include_deps_default": self.include_deps_default,
            "default_context_lines": self.default_context_lines,
            "read_default_max_lines": self.read_default_max_lines,
            "read_with_line_numbers_default": self.read_with_line_numbers_default,
            "outline_include_imports_default": self.outline_include_imports_default,
            "outline_include_module_doc_default": self.outline_include_module_doc_default,
            "outline_include_section_doc_default": self.outline_include_section_doc_default,
            "outline_include_decl_headers_default": self.outline_include_decl_headers_default,
            "outline_include_scope_cmds_default": self.outline_include_scope_cmds_default,
            "outline_default_limit_decls": self.outline_default_limit_decls,
            "refs_include_definition_default": self.refs_include_definition_default,
            "scan_max_file_bytes": self.scan_max_file_bytes,
            "scan_max_files": self.scan_max_files,
        }


@dataclass(slots=True, frozen=True)
class MathlibNavConfig:
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MathlibNavConfig":
        return cls(enabled=to_bool(data.get("enabled"), default=True))

    def to_dict(self) -> JsonDict:
        return {"enabled": self.enabled}


@dataclass(slots=True, frozen=True)
class HttpSearchCommonConfig:
    user_agent: str = "lean-mcp-toolkit/0.1"
    verify_ssl: bool = True
    default_timeout_seconds: int = 10
    connect_timeout_seconds: int | None = None
    retry_count: int = 0
    retry_backoff_seconds: float = 0.0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "HttpSearchCommonConfig":
        return cls(
            user_agent=str(data.get("user_agent") or "lean-mcp-toolkit/0.1"),
            verify_ssl=to_bool(data.get("verify_ssl"), default=True),
            default_timeout_seconds=(
                to_int(data.get("default_timeout_seconds"), default=10) or 10
            ),
            connect_timeout_seconds=to_int(data.get("connect_timeout_seconds"), default=None),
            retry_count=to_int(data.get("retry_count"), default=0) or 0,
            retry_backoff_seconds=float(data.get("retry_backoff_seconds") or 0.0),
        )

    def to_dict(self) -> JsonDict:
        return {
            "user_agent": self.user_agent,
            "verify_ssl": self.verify_ssl,
            "default_timeout_seconds": self.default_timeout_seconds,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "retry_count": self.retry_count,
            "retry_backoff_seconds": self.retry_backoff_seconds,
        }


@dataclass(slots=True, frozen=True)
class LeanSearchProviderConfig:
    enabled: bool = True
    base_url: str = "https://leansearch.net"
    timeout_seconds: int = 10
    startup_verify: bool = False
    max_results_hard_limit: int = 20

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LeanSearchProviderConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            base_url=str(data.get("base_url") or "https://leansearch.net"),
            timeout_seconds=to_int(data.get("timeout_seconds"), default=10) or 10,
            startup_verify=to_bool(data.get("startup_verify"), default=False),
            max_results_hard_limit=to_int(data.get("max_results_hard_limit"), default=20) or 20,
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "startup_verify": self.startup_verify,
            "max_results_hard_limit": self.max_results_hard_limit,
        }


@dataclass(slots=True, frozen=True)
class LeanDexProviderConfig:
    enabled: bool = True
    base_url: str = "https://leandex.projectnumina.ai"
    timeout_seconds: int = 15
    startup_verify: bool = False
    max_results_hard_limit: int = 20
    generate_query: bool = False
    analyze_result: bool = False

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LeanDexProviderConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            base_url=str(data.get("base_url") or "https://leandex.projectnumina.ai"),
            timeout_seconds=to_int(data.get("timeout_seconds"), default=15) or 15,
            startup_verify=to_bool(data.get("startup_verify"), default=False),
            max_results_hard_limit=to_int(data.get("max_results_hard_limit"), default=20) or 20,
            generate_query=to_bool(data.get("generate_query"), default=False),
            analyze_result=to_bool(data.get("analyze_result"), default=False),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "startup_verify": self.startup_verify,
            "max_results_hard_limit": self.max_results_hard_limit,
            "generate_query": self.generate_query,
            "analyze_result": self.analyze_result,
        }


@dataclass(slots=True, frozen=True)
class LoogleProviderConfig:
    enabled: bool = True
    mode: LoogleMode = "remote"
    remote_base_url: str = "https://loogle.lean-lang.org"
    remote_timeout_seconds: int = 10
    local_cache_dir: str | None = None
    local_auto_install: bool = True
    local_startup_verify: bool = False
    local_fallback_to_remote: bool = True
    local_require_unix: bool = True
    max_results_hard_limit: int = 50

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LoogleProviderConfig":
        mode = str(data.get("mode") or "remote").strip().lower()
        if mode not in {"remote", "local", "prefer_local"}:
            mode = "remote"
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            mode=mode,  # type: ignore[arg-type]
            remote_base_url=str(data.get("remote_base_url") or "https://loogle.lean-lang.org"),
            remote_timeout_seconds=to_int(data.get("remote_timeout_seconds"), default=10) or 10,
            local_cache_dir=(
                str(data["local_cache_dir"]) if data.get("local_cache_dir") is not None else None
            ),
            local_auto_install=to_bool(data.get("local_auto_install"), default=True),
            local_startup_verify=to_bool(data.get("local_startup_verify"), default=False),
            local_fallback_to_remote=to_bool(data.get("local_fallback_to_remote"), default=True),
            local_require_unix=to_bool(data.get("local_require_unix"), default=True),
            max_results_hard_limit=to_int(data.get("max_results_hard_limit"), default=50) or 50,
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "remote_base_url": self.remote_base_url,
            "remote_timeout_seconds": self.remote_timeout_seconds,
            "local_cache_dir": self.local_cache_dir,
            "local_auto_install": self.local_auto_install,
            "local_startup_verify": self.local_startup_verify,
            "local_fallback_to_remote": self.local_fallback_to_remote,
            "local_require_unix": self.local_require_unix,
            "max_results_hard_limit": self.max_results_hard_limit,
        }


@dataclass(slots=True, frozen=True)
class LeanFinderProviderConfig:
    enabled: bool = True
    base_url: str = "https://bxrituxuhpc70w8w.us-east-1.aws.endpoints.huggingface.cloud"
    timeout_seconds: int = 10
    startup_verify: bool = False
    mathlib_docs_only: bool = True
    max_results_hard_limit: int = 20

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LeanFinderProviderConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            base_url=str(
                data.get("base_url")
                or "https://bxrituxuhpc70w8w.us-east-1.aws.endpoints.huggingface.cloud"
            ),
            timeout_seconds=to_int(data.get("timeout_seconds"), default=10) or 10,
            startup_verify=to_bool(data.get("startup_verify"), default=False),
            mathlib_docs_only=to_bool(data.get("mathlib_docs_only"), default=True),
            max_results_hard_limit=to_int(data.get("max_results_hard_limit"), default=20) or 20,
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "startup_verify": self.startup_verify,
            "mathlib_docs_only": self.mathlib_docs_only,
            "max_results_hard_limit": self.max_results_hard_limit,
        }


@dataclass(slots=True, frozen=True)
class StateSearchProviderConfig:
    enabled: bool = True
    base_url: str = "https://premise-search.com"
    timeout_seconds: int = 10
    startup_verify: bool = False
    revision: str = "v4.22.0"
    max_results_hard_limit: int = 32

    @classmethod
    def from_dict(cls, data: JsonDict) -> "StateSearchProviderConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            base_url=str(data.get("base_url") or "https://premise-search.com"),
            timeout_seconds=to_int(data.get("timeout_seconds"), default=10) or 10,
            startup_verify=to_bool(data.get("startup_verify"), default=False),
            revision=str(data.get("revision") or "v4.22.0"),
            max_results_hard_limit=to_int(data.get("max_results_hard_limit"), default=32) or 32,
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "startup_verify": self.startup_verify,
            "revision": self.revision,
            "max_results_hard_limit": self.max_results_hard_limit,
        }


@dataclass(slots=True, frozen=True)
class HammerPremiseProviderConfig:
    enabled: bool = True
    base_url: str = "http://leanpremise.net"
    timeout_seconds: int = 10
    startup_verify: bool = False
    max_results_hard_limit: int = 64

    @classmethod
    def from_dict(cls, data: JsonDict) -> "HammerPremiseProviderConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            base_url=str(data.get("base_url") or "http://leanpremise.net"),
            timeout_seconds=to_int(data.get("timeout_seconds"), default=10) or 10,
            startup_verify=to_bool(data.get("startup_verify"), default=False),
            max_results_hard_limit=to_int(data.get("max_results_hard_limit"), default=64) or 64,
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "startup_verify": self.startup_verify,
            "max_results_hard_limit": self.max_results_hard_limit,
        }


@dataclass(slots=True, frozen=True)
class SearchProvidersConfig:
    http_common: HttpSearchCommonConfig = field(default_factory=HttpSearchCommonConfig)
    leansearch: LeanSearchProviderConfig = field(default_factory=LeanSearchProviderConfig)
    leandex: LeanDexProviderConfig = field(default_factory=LeanDexProviderConfig)
    loogle: LoogleProviderConfig = field(default_factory=LoogleProviderConfig)
    leanfinder: LeanFinderProviderConfig = field(default_factory=LeanFinderProviderConfig)
    state_search: StateSearchProviderConfig = field(default_factory=StateSearchProviderConfig)
    hammer_premise: HammerPremiseProviderConfig = field(default_factory=HammerPremiseProviderConfig)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "SearchProvidersConfig":
        return cls(
            http_common=(
                HttpSearchCommonConfig.from_dict(data.get("http_common"))
                if isinstance(data.get("http_common"), dict)
                else HttpSearchCommonConfig()
            ),
            leansearch=(
                LeanSearchProviderConfig.from_dict(data.get("leansearch"))
                if isinstance(data.get("leansearch"), dict)
                else LeanSearchProviderConfig()
            ),
            leandex=(
                LeanDexProviderConfig.from_dict(data.get("leandex"))
                if isinstance(data.get("leandex"), dict)
                else LeanDexProviderConfig()
            ),
            loogle=(
                LoogleProviderConfig.from_dict(data.get("loogle"))
                if isinstance(data.get("loogle"), dict)
                else LoogleProviderConfig()
            ),
            leanfinder=(
                LeanFinderProviderConfig.from_dict(data.get("leanfinder"))
                if isinstance(data.get("leanfinder"), dict)
                else LeanFinderProviderConfig()
            ),
            state_search=(
                StateSearchProviderConfig.from_dict(data.get("state_search"))
                if isinstance(data.get("state_search"), dict)
                else StateSearchProviderConfig()
            ),
            hammer_premise=(
                HammerPremiseProviderConfig.from_dict(data.get("hammer_premise"))
                if isinstance(data.get("hammer_premise"), dict)
                else HammerPremiseProviderConfig()
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "http_common": self.http_common.to_dict(),
            "leansearch": self.leansearch.to_dict(),
            "leandex": self.leandex.to_dict(),
            "loogle": self.loogle.to_dict(),
            "leanfinder": self.leanfinder.to_dict(),
            "state_search": self.state_search.to_dict(),
            "hammer_premise": self.hammer_premise.to_dict(),
        }


@dataclass(slots=True, frozen=True)
class WarmupPolicyConfig:
    enabled: bool = False
    run_on_startup: bool = True
    continue_on_error: bool = True
    default_project_root: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "WarmupPolicyConfig":
        return cls(
            enabled=to_bool(data.get("enabled"), default=False),
            run_on_startup=to_bool(data.get("run_on_startup"), default=True),
            continue_on_error=to_bool(data.get("continue_on_error"), default=True),
            default_project_root=(
                str(data["default_project_root"])
                if data.get("default_project_root") is not None
                else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "run_on_startup": self.run_on_startup,
            "continue_on_error": self.continue_on_error,
            "default_project_root": self.default_project_root,
        }


@dataclass(slots=True, frozen=True)
class WarmupProbeFileConfig:
    rel_path: str = "LeanMcpToolkitWarmup/Probe.lean"
    conflict_strategy: str = "suffix_if_exists"
    cleanup: bool = True

    @classmethod
    def from_dict(cls, data: JsonDict) -> "WarmupProbeFileConfig":
        strategy = str(data.get("conflict_strategy") or "suffix_if_exists").strip()
        if strategy not in {"suffix_if_exists"}:
            strategy = "suffix_if_exists"
        return cls(
            rel_path=str(data.get("rel_path") or "LeanMcpToolkitWarmup/Probe.lean"),
            conflict_strategy=strategy,
            cleanup=to_bool(data.get("cleanup"), default=True),
        )

    def to_dict(self) -> JsonDict:
        return {
            "rel_path": self.rel_path,
            "conflict_strategy": self.conflict_strategy,
            "cleanup": self.cleanup,
        }


@dataclass(slots=True, frozen=True)
class WarmupPlanConfig:
    order: tuple[str, ...] = (
        "search.mathlib_decl.find",
        "declarations.extract",
        "diagnostics.file",
    )

    @classmethod
    def from_dict(cls, data: JsonDict) -> "WarmupPlanConfig":
        return cls(
            order=tuple(
                to_list_of_str(data.get("order"))
                or (
                    "search.mathlib_decl.find",
                    "declarations.extract",
                    "diagnostics.file",
                )
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "order": list(self.order),
        }


@dataclass(slots=True, frozen=True)
class WarmupCallConfig:
    enabled: bool = True
    use_probe_file: bool = False
    request: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "WarmupCallConfig":
        raw_request = data.get("request")
        return cls(
            enabled=to_bool(data.get("enabled"), default=True),
            use_probe_file=to_bool(data.get("use_probe_file"), default=False),
            request=(dict(raw_request) if isinstance(raw_request, dict) else {}),
        )

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "use_probe_file": self.use_probe_file,
            "request": dict(self.request),
        }


def _default_warmup_calls() -> dict[str, WarmupCallConfig]:
    return {
        "search.mathlib_decl.find": WarmupCallConfig(
            enabled=True,
            use_probe_file=False,
            request={
                "query": "Nat.succ",
                "limit": 1,
                "rerank_top": 0,
                "packages": ["Mathlib"],
            },
        ),
        "declarations.extract": WarmupCallConfig(
            enabled=True,
            use_probe_file=True,
            request={},
        ),
        "diagnostics.file": WarmupCallConfig(
            enabled=True,
            use_probe_file=True,
            request={
                "include_content": False,
                "context_lines": 0,
            },
        ),
    }


@dataclass(slots=True, frozen=True)
class WarmupConfig:
    policy: WarmupPolicyConfig = field(default_factory=WarmupPolicyConfig)
    probe_file: WarmupProbeFileConfig = field(default_factory=WarmupProbeFileConfig)
    plan: WarmupPlanConfig = field(default_factory=WarmupPlanConfig)
    calls: dict[str, WarmupCallConfig] = field(default_factory=_default_warmup_calls)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "WarmupConfig":
        raw_policy = data.get("policy")
        raw_probe = data.get("probe_file")
        raw_plan = data.get("plan")
        raw_calls = data.get("calls")

        calls = _default_warmup_calls()
        if isinstance(raw_calls, dict):
            for key, value in raw_calls.items():
                if not isinstance(key, str) or not key.strip():
                    continue
                if isinstance(value, dict):
                    calls[key] = WarmupCallConfig.from_dict(value)

        return cls(
            policy=(
                WarmupPolicyConfig.from_dict(raw_policy)
                if isinstance(raw_policy, dict)
                else WarmupPolicyConfig()
            ),
            probe_file=(
                WarmupProbeFileConfig.from_dict(raw_probe)
                if isinstance(raw_probe, dict)
                else WarmupProbeFileConfig()
            ),
            plan=(
                WarmupPlanConfig.from_dict(raw_plan)
                if isinstance(raw_plan, dict)
                else WarmupPlanConfig()
            ),
            calls=calls,
        )

    def to_dict(self) -> JsonDict:
        calls_dict: JsonDict = {}
        for key in sorted(self.calls.keys()):
            calls_dict[key] = self.calls[key].to_dict()
        return {
            "policy": self.policy.to_dict(),
            "probe_file": self.probe_file.to_dict(),
            "plan": self.plan.to_dict(),
            "calls": calls_dict,
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
    use_server_pool: bool = True
    pool_workers: int | None = 8
    project_auto_build: bool = False
    build_repl: bool = True
    force_pull_repl: bool = False
    repl_rev: str | None = None
    repl_git: str | None = None
    cache_dir: str | None = None
    memory_hard_limit_mb: int | None = None
    enable_incremental_optimization: bool = True
    enable_parallel_elaboration: bool = True
    verbose: bool = False

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LeanInteractBackendConfig":
        return cls(
            use_auto_server=to_bool(data.get("use_auto_server"), default=False),
            use_server_pool=to_bool(data.get("use_server_pool"), default=True),
            pool_workers=to_int(data.get("pool_workers"), default=8),
            project_auto_build=to_bool(data.get("project_auto_build"), default=False),
            build_repl=to_bool(data.get("build_repl"), default=True),
            force_pull_repl=to_bool(data.get("force_pull_repl"), default=False),
            repl_rev=(str(data["repl_rev"]) if data.get("repl_rev") is not None else None),
            repl_git=(str(data["repl_git"]) if data.get("repl_git") is not None else None),
            cache_dir=(str(data["cache_dir"]) if data.get("cache_dir") is not None else None),
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
            "use_server_pool": self.use_server_pool,
            "pool_workers": self.pool_workers,
            "project_auto_build": self.project_auto_build,
            "build_repl": self.build_repl,
            "force_pull_repl": self.force_pull_repl,
            "repl_rev": self.repl_rev,
            "repl_git": self.repl_git,
            "cache_dir": self.cache_dir,
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
    search_providers: SearchProvidersConfig = field(default_factory=SearchProvidersConfig)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "BackendsConfig":
        raw_lean_command = data.get("lean_command")
        raw_lean_interact = data.get("lean_interact")
        raw_lsp = data.get("lsp")
        raw_lean_explore = data.get("lean_explore")
        raw_search_providers = data.get("search_providers")
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
            search_providers=(
                SearchProvidersConfig.from_dict(raw_search_providers)
                if isinstance(raw_search_providers, dict)
                else SearchProvidersConfig()
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "lean_command": self.lean_command.to_dict(),
            "lean_interact": self.lean_interact.to_dict(),
            "lsp": self.lsp.to_dict(),
            "lean_explore": self.lean_explore.to_dict(),
            "search_providers": self.search_providers.to_dict(),
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
    build_base: BuildBaseConfig = field(default_factory=BuildBaseConfig)
    diagnostics: DiagnosticsConfig = field(default_factory=DiagnosticsConfig)
    declarations: DeclarationsConfig = field(default_factory=DeclarationsConfig)
    lsp_core: LspCoreConfig = field(default_factory=LspCoreConfig)
    lsp_assist: LspAssistConfig = field(default_factory=LspAssistConfig)
    lsp_heavy: LspHeavyConfig = field(default_factory=LspHeavyConfig)
    search_alt: SearchAltConfig = field(default_factory=SearchAltConfig)
    search_core: SearchCoreConfig = field(default_factory=SearchCoreConfig)
    mathlib_nav: MathlibNavConfig = field(default_factory=MathlibNavConfig)
    search_nav: SearchNavConfig = field(default_factory=SearchNavConfig)
    proof_search_alt: ProofSearchAltConfig = field(default_factory=ProofSearchAltConfig)
    warmup: WarmupConfig = field(default_factory=WarmupConfig)
    backends: BackendsConfig = field(default_factory=BackendsConfig)
    toolchain: ToolchainConfig = field(default_factory=ToolchainConfig)
    raw_group_overrides: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ToolkitConfig":
        raw_server = data.get("server")
        raw_groups = data.get("groups")
        raw_build_base = data.get("build_base")
        raw_diag = data.get("diagnostics")
        raw_declarations = data.get("declarations")
        raw_lsp_core = data.get("lsp_core")
        raw_lsp_assist = data.get("lsp_assist")
        raw_lsp_heavy = data.get("lsp_heavy")
        raw_search_alt = data.get("search_alt")
        raw_search_core = data.get("search_core")
        raw_mathlib_nav = data.get("mathlib_nav")
        raw_search_nav = data.get("search_nav")
        raw_proof_search_alt = data.get("proof_search_alt")
        raw_warmup = data.get("warmup")
        raw_backends = data.get("backends")
        raw_toolchain = data.get("toolchain")
        raw_overrides = data.get("raw_group_overrides")

        build_base = (
            BuildBaseConfig.from_dict(raw_build_base)
            if isinstance(raw_build_base, dict)
            else BuildBaseConfig()
        )
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
        lsp_assist = (
            LspAssistConfig.from_dict(raw_lsp_assist)
            if isinstance(raw_lsp_assist, dict)
            else LspAssistConfig()
        )
        lsp_heavy = (
            LspHeavyConfig.from_dict(raw_lsp_heavy)
            if isinstance(raw_lsp_heavy, dict)
            else LspHeavyConfig()
        )
        search_core = (
            SearchCoreConfig.from_dict(raw_search_core)
            if isinstance(raw_search_core, dict)
            else SearchCoreConfig()
        )
        search_alt = (
            SearchAltConfig.from_dict(raw_search_alt)
            if isinstance(raw_search_alt, dict)
            else SearchAltConfig()
        )
        mathlib_nav = (
            MathlibNavConfig.from_dict(raw_mathlib_nav)
            if isinstance(raw_mathlib_nav, dict)
            else MathlibNavConfig()
        )
        search_nav = (
            SearchNavConfig.from_dict(raw_search_nav)
            if isinstance(raw_search_nav, dict)
            else SearchNavConfig()
        )
        proof_search_alt = (
            ProofSearchAltConfig.from_dict(raw_proof_search_alt)
            if isinstance(raw_proof_search_alt, dict)
            else ProofSearchAltConfig()
        )
        warmup = (
            WarmupConfig.from_dict(raw_warmup)
            if isinstance(raw_warmup, dict)
            else WarmupConfig()
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
            build_base=build_base,
            diagnostics=diagnostics,
            declarations=declarations,
            lsp_core=lsp_core,
            lsp_assist=lsp_assist,
            lsp_heavy=lsp_heavy,
            search_alt=search_alt,
            search_core=search_core,
            mathlib_nav=mathlib_nav,
            search_nav=search_nav,
            proof_search_alt=proof_search_alt,
            warmup=warmup,
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
            "build_base": self.build_base.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
            "declarations": self.declarations.to_dict(),
            "lsp_core": self.lsp_core.to_dict(),
            "lsp_assist": self.lsp_assist.to_dict(),
            "lsp_heavy": self.lsp_heavy.to_dict(),
            "search_alt": self.search_alt.to_dict(),
            "search_core": self.search_core.to_dict(),
            "mathlib_nav": self.mathlib_nav.to_dict(),
            "search_nav": self.search_nav.to_dict(),
            "proof_search_alt": self.proof_search_alt.to_dict(),
            "warmup": self.warmup.to_dict(),
            "backends": self.backends.to_dict(),
            "toolchain": self.toolchain.to_dict(),
            "raw_group_overrides": dict(self.raw_group_overrides),
        }
