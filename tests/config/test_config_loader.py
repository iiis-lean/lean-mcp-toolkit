from lean_mcp_toolkit.config.cli import ConfigCLIArgs, cli_args_to_overrides
from lean_mcp_toolkit.config.loader import load_toolkit_config


def test_env_override() -> None:
    env = {
        "LEAN_MCP_TOOLKIT__SERVER__PORT": "19090",
        "LEAN_MCP_TOOLKIT__SERVER__MCP_TRANSPORT": "stdio",
        "LEAN_MCP_TOOLKIT__DIAGNOSTICS__DEFAULT_BUILD_DEPS": "true",
        "LEAN_MCP_TOOLKIT__GROUPS__ENABLED_GROUPS": "diagnostics,lsp_core",
        "LEAN_MCP_TOOLKIT__TOOLCHAIN__USE_LAKE_ENV_FOR_LEAN": "false",
    }
    cfg = load_toolkit_config(env=env)
    assert cfg.server.port == 19090
    assert cfg.server.mcp_transport == "stdio"
    assert cfg.diagnostics.default_build_deps is True
    assert cfg.groups.enabled_groups == ("diagnostics", "lsp_core")
    assert cfg.toolchain.use_lake_env_for_lean is False


def test_cli_override_priority() -> None:
    args = ConfigCLIArgs(
        mode="http",
        port=20001,
        project_root="/tmp/project-from-cli",
        enable_groups=["diagnostics"],
        set_items=["backends.lean_command.max_concurrent_lean_checks=9"],
    )
    overrides = cli_args_to_overrides(args)
    cfg = load_toolkit_config(cli_overrides=overrides)
    assert cfg.server.mode == "http"
    assert cfg.server.port == 20001
    assert cfg.server.default_project_root == "/tmp/project-from-cli"
    assert cfg.groups.enabled_groups == ("diagnostics",)
    assert cfg.backends.lean_command.max_concurrent_lean_checks == 9


def test_default_diagnostics_config() -> None:
    cfg = load_toolkit_config()
    assert cfg.diagnostics.default_build_deps is True
    assert cfg.diagnostics.default_emit_artifacts is True
    assert cfg.diagnostics.default_enabled_checks == ("no_sorry", "axiom_audit")
    assert cfg.diagnostics.axiom_audit_allowed_axioms == (
        "propext",
        "Classical.choice",
        "Quot.sound",
    )
    assert cfg.diagnostics.axiom_audit_include_sorry_ax is False


def test_default_nav_group_activation() -> None:
    cfg = load_toolkit_config()
    assert "build_base" not in cfg.groups.enabled_groups
    assert "lsp_heavy" not in cfg.groups.enabled_groups
    assert "search_alt" not in cfg.groups.enabled_groups
    assert "mathlib_nav" in cfg.groups.enabled_groups
    assert "search_nav" not in cfg.groups.enabled_groups
    assert "proof_search_alt" not in cfg.groups.enabled_groups
    assert cfg.build_base.enabled is False
    assert cfg.lsp_heavy.enabled is False
    assert cfg.search_alt.enabled is False
    assert cfg.mathlib_nav.enabled is True
    assert cfg.search_nav.enabled is False
    assert cfg.proof_search_alt.enabled is False


def test_declarations_config_override() -> None:
    cfg = load_toolkit_config(
        cli_overrides={
            "declarations": {
                "default_backend": "lean_interact",
                "default_include_value": True,
            },
            "backends": {
                "lean_interact": {
                    "use_auto_server": True,
                    "project_auto_build": True,
                    "build_repl": False,
                    "verbose": True,
                }
            },
        }
    )
    assert cfg.declarations.default_backend == "lean_interact"
    assert cfg.declarations.default_include_value is True
    assert cfg.backends.lean_interact.use_auto_server is True
    assert cfg.backends.lean_interact.project_auto_build is True
    assert cfg.backends.lean_interact.build_repl is False
    assert cfg.backends.lean_interact.verbose is True


def test_warmup_config_structure() -> None:
    cfg = load_toolkit_config(
        cli_overrides={
            "warmup": {
                "policy": {
                    "enabled": True,
                    "run_on_startup": True,
                    "continue_on_error": False,
                    "default_project_root": "/tmp/demo",
                },
                "probe_file": {
                    "rel_path": "LeanMcpToolkitWarmup/Probe.lean",
                    "conflict_strategy": "suffix_if_exists",
                    "cleanup": True,
                },
                "plan": {
                    "order": [
                        "search.mathlib_decl.find",
                        "declarations.extract",
                        "diagnostics.file",
                    ]
                },
                "calls": {
                    "search.mathlib_decl.find": {
                        "enabled": True,
                        "request": {
                            "query": "Nat.succ",
                            "limit": 1,
                            "rerank_top": 0,
                            "packages": ["Mathlib"],
                        },
                    },
                    "declarations.extract": {
                        "enabled": True,
                        "use_probe_file": True,
                        "request": {},
                    },
                    "diagnostics.file": {
                        "enabled": True,
                        "use_probe_file": True,
                        "request": {
                            "include_content": False,
                            "context_lines": 0,
                        },
                    },
                },
            }
        }
    )
    assert cfg.warmup.policy.enabled is True
    assert cfg.warmup.policy.continue_on_error is False
    assert cfg.warmup.policy.default_project_root == "/tmp/demo"
    assert cfg.warmup.plan.order == (
        "search.mathlib_decl.find",
        "declarations.extract",
        "diagnostics.file",
    )
    assert cfg.warmup.probe_file.rel_path == "LeanMcpToolkitWarmup/Probe.lean"
    assert cfg.warmup.calls["declarations.extract"].use_probe_file is True
    assert cfg.warmup.calls["diagnostics.file"].request["context_lines"] == 0
