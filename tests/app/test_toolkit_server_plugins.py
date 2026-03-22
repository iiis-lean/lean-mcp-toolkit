from __future__ import annotations

from dataclasses import dataclass

import pytest

from lean_mcp_toolkit.app import ToolkitServer
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.groups.plugin_base import GroupToolSpec


@dataclass(slots=True, frozen=True)
class _FakePlugin:
    group_name: str = "fake"

    def backend_dependencies(self) -> tuple[str, ...]:
        return tuple()

    def create_local_service(self, config: ToolkitConfig, *, backends=None):
        _ = config
        _ = backends
        return object()

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return (
            GroupToolSpec(
                group_name="fake",
                canonical_name="fake.alpha",
                raw_name="alpha",
                api_path="/fake/alpha",
                description="alpha tool",
            ),
            GroupToolSpec(
                group_name="fake",
                canonical_name="fake.beta",
                raw_name="beta",
                api_path="/fake/beta",
                description="beta tool",
            ),
        )

    def tool_handlers(self, service) -> dict[str, callable]:
        _ = service
        return {
            "fake.alpha": lambda payload: {"tool": "fake.alpha", "payload": payload},
            "fake.beta": lambda payload: {"tool": "fake.beta", "payload": payload},
        }

    def register_mcp_tools(self, mcp, *, service, aliases_by_canonical, normalize_str_list, prune_none):
        _ = mcp
        _ = service
        _ = aliases_by_canonical
        _ = normalize_str_list
        _ = prune_none


def test_plugin_group_disabled_removes_all_tools() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "disabled_groups": ["fake"],
                "tool_naming_mode": "prefixed",
            }
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakePlugin(),))

    assert server.available_tool_aliases() == tuple()
    assert server.available_http_routes() == tuple()
    with pytest.raises(KeyError):
        server.dispatch_api("/fake/alpha", {})
    with pytest.raises(KeyError):
        server.dispatch_api("fake.alpha", {})


def test_plugin_include_exclude_filters_tools() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "include_tools": ["fake.alpha", "beta"],
                "exclude_tools": ["fake.beta"],
                "tool_naming_mode": "prefixed",
            }
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakePlugin(),))

    assert server.available_tool_aliases() == ("fake.alpha",)
    assert server.available_http_routes() == ("/fake/alpha",)
    assert server.dispatch_api("fake.alpha", {})["tool"] == "fake.alpha"
    assert server.dispatch_api("/fake/alpha", {})["tool"] == "fake.alpha"
    with pytest.raises(KeyError):
        server.dispatch_api("fake.beta", {})
    with pytest.raises(KeyError):
        server.dispatch_api("/fake/beta", {})


def test_plugin_tool_naming_mode_raw() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "tool_naming_mode": "raw",
            }
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakePlugin(),))

    assert server.available_tool_aliases() == ("alpha", "beta")
    assert server.dispatch_api("alpha", {})["tool"] == "fake.alpha"
    with pytest.raises(KeyError):
        server.dispatch_api("fake.alpha", {})
    assert server.dispatch_api("/fake/alpha", {})["tool"] == "fake.alpha"


def test_plugin_tool_naming_mode_both_and_unknown_group_ignored() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["unknown_group", "fake"],
                "tool_naming_mode": "both",
            }
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakePlugin(),))

    assert set(server.available_tool_aliases()) == {"fake.alpha", "fake.beta", "alpha", "beta"}
    assert server.dispatch_api("fake.beta", {})["tool"] == "fake.beta"
    assert server.dispatch_api("beta", {})["tool"] == "fake.beta"
