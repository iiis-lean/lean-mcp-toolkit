from dataclasses import dataclass

from lean_mcp_toolkit.app import ToolkitHttpClient
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.groups.plugin_base import GroupToolSpec
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeGroupClient:
    group: str = "diagnostics"


@dataclass(slots=True, frozen=True)
class _FakePlugin:
    group_name: str = "diagnostics"

    def backend_dependencies(self) -> tuple[str, ...]:
        return tuple()

    def create_local_service(self, config: ToolkitConfig, *, backends=None):
        _ = config
        _ = backends
        return object()

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        _ = http_config
        return _FakeGroupClient()

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return (
            GroupToolSpec(
                group_name="diagnostics",
                canonical_name="diagnostics.build",
                raw_name="build",
                api_path="/diagnostics/build",
                description="build",
            ),
            GroupToolSpec(
                group_name="diagnostics",
                canonical_name="diagnostics.lint",
                raw_name="lint",
                api_path="/diagnostics/lint",
                description="lint",
            ),
            GroupToolSpec(
                group_name="diagnostics",
                canonical_name="diagnostics.lint.no_sorry",
                raw_name="lint.no_sorry",
                api_path="/diagnostics/lint/no_sorry",
                description="no_sorry",
            ),
        )

    def tool_handlers(self, service) -> dict[str, callable]:
        _ = service
        return {
            "diagnostics.build": lambda payload: {"ok": True, "tool": "build", "payload": payload},
            "diagnostics.lint": lambda payload: {"ok": True, "tool": "lint", "payload": payload},
            "diagnostics.lint.no_sorry": lambda payload: {
                "ok": True,
                "tool": "no_sorry",
                "payload": payload,
            },
        }

    def register_mcp_tools(self, mcp, *, service, aliases_by_canonical, normalize_str_list, prune_none):
        _ = mcp
        _ = service
        _ = aliases_by_canonical
        _ = normalize_str_list
        _ = prune_none



def test_toolkit_http_client_dispatch() -> None:
    client = ToolkitHttpClient.from_http_config(
        HttpConfig(base_url="http://127.0.0.1:18080"),
        config=ToolkitConfig.from_dict(
            {"groups": {"enabled_groups": ["diagnostics"], "tool_naming_mode": "prefixed"}}
        ),
        plugins=(_FakePlugin(),),
    )
    assert client.dispatch_api("diagnostics.build", {})["tool"] == "build"
    assert client.dispatch_api("/diagnostics/lint", {})["tool"] == "lint"
    assert client.dispatch_api("diagnostics.lint.no_sorry", {})["tool"] == "no_sorry"



def test_toolkit_http_client_factory() -> None:
    cfg = HttpConfig(base_url="http://127.0.0.1:18080")
    client = ToolkitHttpClient.from_http_config(cfg)
    assert client.diagnostics.http_config.base_url == "http://127.0.0.1:18080"
