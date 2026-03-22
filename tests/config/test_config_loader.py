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
        enable_groups=["diagnostics"],
        set_items=["backends.lean_command.max_concurrent_lean_checks=9"],
    )
    overrides = cli_args_to_overrides(args)
    cfg = load_toolkit_config(cli_overrides=overrides)
    assert cfg.server.mode == "http"
    assert cfg.server.port == 20001
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
